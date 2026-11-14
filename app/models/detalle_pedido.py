from decimal import Decimal

from app.extensions import db
from app.models.base import BaseModel


class DetallePedido(BaseModel):
    __tablename__ = "detalles_pedido"

    pedido_id = db.Column(
        db.Integer, db.ForeignKey("pedidos.id"), nullable=False
    )
    producto_id = db.Column(
        db.Integer, db.ForeignKey("products.id"), nullable=False
    )
    cantidad = db.Column(db.Integer, nullable=False, default=1)
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=False)

    pedido = db.relationship("Pedido", backref=db.backref("detalles", lazy=True))
    producto = db.relationship("Product", backref=db.backref("detalles_pedido", lazy=True))

    def __repr__(self):
        return f"<DetallePedido {self.id}: pedido={self.pedido_id}, producto={self.producto_id}, cantidad={self.cantidad}>"