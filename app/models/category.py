from app.extensions import db
from app.models.base import BaseModel


class Category(BaseModel):
    __tablename__ = "categories"

    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(500), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def find_by_name_case_insensitive(cls, name, exclude_id=None):
        query = cls.query.filter(db.func.lower(cls.name) == db.func.lower(name))
        if exclude_id is not None:
            query = query.filter(cls.id != exclude_id)
        return query.first()

    def __repr__(self):
        return f"<Category {self.id}: {self.name}>"
