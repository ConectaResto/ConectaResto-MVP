from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import DetallePedido, Mesa, Pago, Pedido, Servicio
from app.pedidos.service import PedidoError, bloquear_servicio


def calcular_total_servicio(servicio_id, *, bloquear=False):
    consulta = (
        db.select(DetallePedido).join(Pedido)
        .where(Pedido.servicio_id == servicio_id)
        .execution_options(populate_existing=True)
    )
    if bloquear:
        consulta = consulta.with_for_update()
    detalles = db.session.execute(consulta).scalars()
    return sum((d.precio_unitario * d.cantidad for d in detalles), Decimal("0.00"))


def procesar_caja(servicio_id, accion, *, actor):
    """Registra pago o cierra el servicio con una sola confirmación atómica."""
    try:
        if not actor.is_active or actor.rol.name != "CASHIER":
            raise PedidoError("Prohibido", 403)
        if accion not in ("pago-simulado", "cerrar"):
            raise PedidoError("Accion invalida")
        servicio = bloquear_servicio(servicio_id)
        if servicio.estado != "ACTIVO":
            raise PedidoError("El servicio no esta activo", 409)
        pago = db.session.execute(
            db.select(Pago).where(Pago.servicio_id == servicio.id)
            .with_for_update().execution_options(populate_existing=True)
        ).scalar_one_or_none()
        if accion == "pago-simulado" and pago is not None:
            raise PedidoError("El servicio ya tiene un pago registrado", 409)
        # Lecturas con bloqueo obtienen los datos actuales también en REPEATABLE READ.
        pedidos = db.session.execute(
            db.select(Pedido).where(Pedido.servicio_id == servicio.id)
            .with_for_update().execution_options(populate_existing=True)
        ).scalars().all()
        if any(p.estado != "ENTREGADO" for p in pedidos):
            raise PedidoError("Todos los pedidos deben estar entregados", 409)
        total = calcular_total_servicio(servicio.id, bloquear=True)
        if accion == "pago-simulado":
            if not pedidos or total <= 0:
                raise PedidoError("El servicio debe tener pedidos y un total mayor a cero", 409)
            if total > Decimal("99999999.99"):
                raise PedidoError("El total excede la capacidad del importe de pago", 409)
            db.session.add(Pago(
                servicio_id=servicio.id, importe=total, registrado_por_id=actor.id,
            ))
        else:
            if pedidos and pago is None:
                raise PedidoError("El servicio requiere un pago completo", 409)
            if pago is not None and pago.importe != total:
                raise PedidoError("El pago no coincide con el total del servicio", 409)
            otro_activo = db.exists().where(
                Servicio.mesa_id == servicio.mesa_id,
                Servicio.estado == "ACTIVO", Servicio.id != servicio.id,
            )
            resultado = db.session.execute(
                db.update(Mesa).where(
                    Mesa.id == servicio.mesa_id, Mesa.estado == "OCUPADA", ~otro_activo,
                ).values(estado="DISPONIBLE")
            )
            if resultado.rowcount != 1:
                raise PedidoError("La mesa tiene un estado incompatible con el cierre", 409)
            servicio.estado = "CERRADO"
        db.session.commit()
        return servicio
    except IntegrityError as exc:
        db.session.rollback()
        raise PedidoError("Conflicto al registrar la operacion de caja", 409) from exc
    except Exception:
        db.session.rollback()
        raise


def abrir_servicio(mesa_id, *, actor):
    try:
        if not actor.is_active or actor.rol.name != "WAITER":
            raise PedidoError("Prohibido", 403)
        if type(mesa_id) is not int or not 0 < mesa_id <= 2147483647:
            raise PedidoError("mesa_id debe ser un entero positivo valido")
        # El UPDATE condicional serializa aperturas incluso sin SELECT FOR UPDATE.
        resultado = db.session.execute(
            db.update(Mesa).where(Mesa.id == mesa_id, Mesa.estado == "DISPONIBLE")
            .values(estado="OCUPADA")
        )
        if resultado.rowcount != 1:
            if db.session.get(Mesa, mesa_id) is None:
                raise PedidoError("Mesa no encontrada", 404)
            raise PedidoError("La mesa no esta disponible", 409)
        activo = db.session.execute(
            db.select(Servicio.id).where(Servicio.mesa_id == mesa_id, Servicio.estado == "ACTIVO")
        ).first()
        if activo is not None:
            raise PedidoError("La mesa ya tiene un servicio activo", 409)
        servicio = Servicio(mesa_id=mesa_id, abierto_por_id=actor.id, estado="ACTIVO")
        db.session.add(servicio)
        db.session.commit()
        return servicio
    except IntegrityError as exc:
        db.session.rollback()
        raise PedidoError("Conflicto al abrir el servicio", 409) from exc
    except Exception:
        db.session.rollback()
        raise
