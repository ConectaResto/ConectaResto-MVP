from decimal import Decimal

from app.extensions import db
from app.pedidos.models import DetallePedido, Pedido
from app.servicios.models import Servicio


class ServicioRepository:
    """Consultas de acceso a datos para servicios."""

    @staticmethod
    def list_by_estado(estado=None):
        consulta = db.select(Servicio).order_by(Servicio.id)
        if estado is not None:
            consulta = consulta.where(Servicio.estado == estado)
        return db.session.execute(consulta).scalars().all()

    @staticmethod
    def calcular_total(servicio_id, *, bloquear=False):
        consulta = (
            db.select(DetallePedido).join(Pedido)
            .where(Pedido.servicio_id == servicio_id)
            .execution_options(populate_existing=True)
        )
        if bloquear:
            consulta = consulta.with_for_update()
        detalles = db.session.execute(consulta).scalars()
        return sum((d.precio_unitario * d.cantidad for d in detalles), Decimal("0.00"))
