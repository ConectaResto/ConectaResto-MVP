from app.extensions import db
from app.models.base import BaseModel


class Servicio(BaseModel):
    __tablename__ = "servicios"

    mesa_id = db.Column(db.Integer, db.ForeignKey("mesas.id"), nullable=False)
    abierto_por_id = db.Column(
        db.Integer, db.ForeignKey("usuarios.id"), nullable=True
    )
    estado = db.Column(
        db.String(20), nullable=False, default="ACTIVO"
    )

    mesa = db.relationship("Mesa", backref=db.backref("servicios", lazy=True))
    abierto_por = db.relationship("Usuario", backref=db.backref("servicios_abiertos", lazy=True))

    def __repr__(self):
        return f"<Servicio {self.id}: mesa={self.mesa_id}, estado={self.estado}>"