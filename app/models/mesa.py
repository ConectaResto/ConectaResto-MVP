import secrets

from app.extensions import db
from app.models.base import BaseModel


class Mesa(BaseModel):
    __tablename__ = "mesas"
    __table_args__ = (
        db.CheckConstraint("numero > 0", name="ck_mesas_numero_positivo"),
        db.CheckConstraint(
            "estado IN ('DISPONIBLE', 'OCUPADA', 'CERRADA')",
            name="ck_mesas_estado",
        ),
    )

    ESTADOS = frozenset({"DISPONIBLE", "OCUPADA", "CERRADA"})

    numero = db.Column(db.Integer, unique=True, nullable=False)
    estado = db.Column(db.String(10), default="DISPONIBLE", nullable=False)
    public_token = db.Column(
        db.String(64), unique=True, nullable=False,
        default=lambda: secrets.token_hex(32),
    )
