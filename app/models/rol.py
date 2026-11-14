from app.extensions import db
from app.models.base import BaseModel


class Rol(BaseModel):
    __tablename__ = "roles"

    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<Rol {self.name}>"