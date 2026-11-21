from datetime import datetime, timezone

from app.catalog.service import get_product
from app.extensions import db
from app.mesas.models import Mesa
from app.pedidos.models import DetallePedido, Pedido
from app.servicios.models import Pago, Servicio
from app.users.models import Usuario
from app.pedidos.repository import PedidoRepository


class PedidoError(ValueError):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


def bloquear_servicio(servicio_id):
    """Serializa pedidos y caja en MySQL y SQLite dentro de la transacción actual."""
    if type(servicio_id) is not int or not 0 < servicio_id <= 2147483647:
        raise PedidoError("Servicio no encontrado", 404)
    mesa_id = db.session.execute(
        db.select(Servicio.mesa_id).where(Servicio.id == servicio_id)
    ).scalar_one_or_none()
    if mesa_id is None:
        raise PedidoError("Servicio no encontrado", 404)
    # SQLite ignora FOR UPDATE. Esta escritura obtiene su bloqueo antes de leer.
    # MySQL mantiene el bloqueo de la fila hasta commit o rollback.
    # Mesa antes de servicio conserva el orden del adaptador público y la apertura.
    db.session.execute(
        db.update(Mesa).where(Mesa.id == mesa_id)
        .values(estado=Mesa.estado, updated_at=Mesa.updated_at)
        .execution_options(synchronize_session=False)
    )
    db.session.execute(
        db.update(Servicio).where(Servicio.id == servicio_id)
        .values(estado=Servicio.estado, updated_at=Servicio.updated_at)
        .execution_options(synchronize_session=False)
    )
    servicio = db.session.execute(
        db.select(Servicio).where(Servicio.id == servicio_id)
        .with_for_update().execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if servicio is None:
        raise PedidoError("Servicio no encontrado", 404)
    return servicio


def crear_pedido(servicio_id, items, *, origen, creado_por_id=None):
    """Crea y confirma un pedido completo con precios del catálogo.

    El adaptador público resuelve el servicio y pasa origen PUBLICO sin usuario.
    Esta función valida el dominio y es dueña del commit y rollback.
    """
    try:
        if type(servicio_id) is not int or not 0 < servicio_id <= 2147483647:
            raise PedidoError("servicio_id debe ser un entero positivo valido")
        if origen not in ("MESERO", "PUBLICO"):
            raise PedidoError("Origen invalido")
        if origen == "MESERO":
            usuario = None
            if type(creado_por_id) is int and 0 < creado_por_id <= 2147483647:
                usuario = db.session.get(Usuario, creado_por_id)
            if usuario is None or not usuario.is_active or usuario.rol.name != "WAITER":
                raise PedidoError("Se requiere un mesero activo", 403)
        elif creado_por_id is not None:
            raise PedidoError("Un pedido publico no tiene usuario creador")
        if not isinstance(items, list) or not items:
            raise PedidoError("items debe contener al menos un producto")
        servicio = bloquear_servicio(servicio_id)
        if servicio.estado != "ACTIVO":
            raise PedidoError("El servicio no esta activo", 409)
        pago = db.session.execute(
            db.select(Pago.id).where(Pago.servicio_id == servicio.id).with_for_update()
        ).first()
        if pago is not None:
            raise PedidoError("El servicio ya tiene un pago registrado", 409)
        detalles = []
        for item in items:
            if not isinstance(item, dict) or set(item) != {"producto_id", "cantidad"}:
                raise PedidoError("Cada item requiere solamente producto_id y cantidad")
            producto_id, cantidad = item["producto_id"], item["cantidad"]
            if type(producto_id) is not int or not 0 < producto_id <= 2147483647:
                raise PedidoError("producto_id debe ser un entero positivo valido")
            if type(cantidad) is not int or not 0 < cantidad <= 2147483647:
                raise PedidoError("cantidad debe ser un entero positivo valido")
            producto = get_product(producto_id)
            if producto is None:
                raise PedidoError("Producto no encontrado o no disponible", 404)
            detalles.append(DetallePedido(
                producto_id=producto.id, cantidad=cantidad,
                precio_unitario=producto.price,
            ))
        pedido = Pedido(
            servicio_id=servicio.id, origen=origen, creado_por_id=creado_por_id,
            estado="PENDIENTE", estado_preparacion="NO_ENVIADO",
        )
        pedido.detalles = detalles
        db.session.add(pedido)
        db.session.commit()
        return pedido
    except Exception:
        db.session.rollback()
        raise


def actualizar_pedido(pedido_id, accion, *, actor, estado_preparacion=None):
    """Aplica una transición con bloqueo de fila y confirmación atómica."""
    try:
        rol = "KITCHEN" if accion == "preparacion" else "WAITER"
        if not actor.is_active or actor.rol.name != rol:
            raise PedidoError("Prohibido", 403)
        pedido = PedidoRepository.get_by_id_for_update(pedido_id)
        if pedido is None:
            raise PedidoError("Pedido no encontrado", 404)
        if pedido.servicio.estado != "ACTIVO":
            raise PedidoError("El servicio no esta activo", 409)
        if accion == "autorizar":
            if (pedido.estado != "PENDIENTE" or pedido.estado_preparacion != "NO_ENVIADO"
                    or pedido.autorizado_por_id is not None):
                raise PedidoError("El pedido no puede autorizarse en su estado actual", 409)
            pedido.autorizado_por_id = actor.id
            pedido.autorizado_at = datetime.now(timezone.utc)
        elif accion == "enviar-cocina":
            if (pedido.estado != "PENDIENTE" or pedido.estado_preparacion != "NO_ENVIADO"
                    or pedido.autorizado_por_id is None or not pedido.detalles):
                raise PedidoError("El pedido debe estar pendiente, autorizado y tener productos", 409)
            pedido.estado = "EN_PREPARACION"
            pedido.estado_preparacion = "RECIBIDO"
        elif accion == "preparacion":
            if estado_preparacion not in ("EN_COCINA", "LISTO_PARA_SERVIR"):
                raise PedidoError("Estado de preparacion invalido")
            anterior = "RECIBIDO" if estado_preparacion == "EN_COCINA" else "EN_COCINA"
            if pedido.estado != "EN_PREPARACION" or pedido.estado_preparacion != anterior:
                raise PedidoError("Transicion de preparacion invalida", 409)
            pedido.estado_preparacion = estado_preparacion
            if estado_preparacion == "LISTO_PARA_SERVIR":
                pedido.estado = "LISTO"
        elif accion == "entregar":
            if pedido.estado != "LISTO" or pedido.estado_preparacion != "LISTO_PARA_SERVIR":
                raise PedidoError("Solo puede entregarse un pedido listo", 409)
            pedido.estado = "ENTREGADO"
        else:
            raise PedidoError("Accion invalida")
        db.session.commit()
        return pedido
    except Exception:
        db.session.rollback()
        raise
