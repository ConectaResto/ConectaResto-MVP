from datetime import datetime, timezone

from app.extensions import db
from app.models.base import BaseModel


class Pago(BaseModel):
    __tablename__ = "pagos"

    servicio_id = db.Column(
        db.Integer, db.ForeignKey("servicios.id"), nullable=False, unique=True
    )
    registrado_por_id = db.Column(
        db.Integer, db.ForeignKey("usuarios.id"), nullable=False
    )
    importe = db.Column(db.Numeric(10, 2), nullable=False)
    fecha_registro = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        db.CheckConstraint("importe > 0", name="ck_pagos_importe_positivo"),
    )

    servicio = db.relationship("Servicio", backref=db.backref("pago", lazy=True, uselist=False))
    registrado_por = db.relationship("Usuario", backref=db.backref("pagos_registrados", lazy=True))

    def __repr__(self):
        return f"<Pago {self.id}: servicio={self.servicio_id}, importe={self.importe}>"