from app.extensions import db
from app.pedidos.models import Pedido


class PedidoRepository:
    """Consultas de acceso a datos para pedidos."""

    @staticmethod
    def get_by_id_for_update(pedido_id):
        return db.session.execute(
            db.select(Pedido).where(Pedido.id == pedido_id)
            .with_for_update().execution_options(populate_existing=True)
        ).scalar_one_or_none()

    @staticmethod
    def list_by_rol_and_estado(rol_name, estado=None):
        consulta = db.select(Pedido).order_by(Pedido.id)
        if rol_name == "KITCHEN":
            consulta = consulta.where(
                Pedido.estado_preparacion != "NO_ENVIADO", Pedido.estado != "CANCELADO",
            )
        if estado is not None:
            consulta = consulta.where(Pedido.estado == estado)
        return db.session.execute(consulta).scalars().all()
