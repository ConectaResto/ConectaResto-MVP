from decimal import Decimal

from app.extensions import db
from app.models.base import BaseModel


class Product(BaseModel):
    __tablename__ = "products"

    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    categoria_id = db.Column(
        db.Integer, db.ForeignKey("categories.id"), nullable=False
    )
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_available = db.Column(db.Boolean, default=True, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "price": str(self.price) if self.price is not None else None,
            "categoria_id": self.categoria_id,
            "is_active": self.is_active,
            "is_available": self.is_available,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Product {self.id}: {self.name}>"
