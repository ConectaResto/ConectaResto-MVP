from app.extensions import db
from app.models.base import BaseModel


class Pedido(BaseModel):
    __tablename__ = "pedidos"
    __table_args__ = (
        db.CheckConstraint(
            "estado IN ('PENDIENTE', 'EN_PREPARACION', 'LISTO', 'ENTREGADO')",
            name="ck_pedidos_estado",
        ),
        db.CheckConstraint(
            "origen IN ('MESERO', 'PUBLICO')",
            name="ck_pedidos_origen",
        ),
        db.CheckConstraint(
            "estado_preparacion IN ('NO_ENVIADO', 'RECIBIDO', 'EN_COCINA', 'LISTO_PARA_SERVIR')",
            name="ck_pedidos_estado_preparacion",
        ),
    )

    servicio_id = db.Column(
        db.Integer, db.ForeignKey("servicios.id"), nullable=False
    )
    origen = db.Column(db.String(20), nullable=False)
    creado_por_id = db.Column(
        db.Integer, db.ForeignKey("usuarios.id"), nullable=True
    )
    autorizado_por_id = db.Column(
        db.Integer, db.ForeignKey("usuarios.id"), nullable=True
    )
    autorizado_at = db.Column(db.DateTime, nullable=True)
    estado = db.Column(db.String(20), nullable=False, default="PENDIENTE")
    estado_preparacion = db.Column(
        db.String(30), nullable=False, default="NO_ENVIADO"
    )

    servicio = db.relationship("Servicio", backref=db.backref("pedidos", lazy=True))
    creado_por = db.relationship(
        "Usuario", foreign_keys=[creado_por_id], backref=db.backref("pedidos_creados", lazy=True)
    )
    autorizado_por = db.relationship(
        "Usuario", foreign_keys=[autorizado_por_id], backref=db.backref("pedidos_autorizados", lazy=True)
    )

    def __repr__(self):
        return f"<Pedido {self.id}: servicio={self.servicio_id}, estado={self.estado}>"