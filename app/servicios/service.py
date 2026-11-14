from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Mesa, Servicio
from app.pedidos.service import PedidoError


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
