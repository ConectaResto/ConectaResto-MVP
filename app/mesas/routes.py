from flask import Blueprint, request
from sqlalchemy.exc import IntegrityError

from app.auth.decorators import roles_required
from app.common.responses import error_response, success_response
from app.extensions import db
from app.models import Mesa


mesas_bp = Blueprint("mesas", __name__, url_prefix="/admin/mesas")


def serialize(mesa):
    return {
        "id": mesa.id, "numero": mesa.numero,
        "estado": mesa.estado, "public_token": mesa.public_token,
    }


def validate(data, creating=False):
    if not isinstance(data, dict) or not data or set(data) - {"numero", "estado"}:
        return "Solo se permiten numero y estado"
    if creating and "numero" not in data:
        return "Se requiere numero"
    if "numero" in data and (
        type(data["numero"]) is not int or not 0 < data["numero"] <= 2147483647
    ):
        return "numero debe ser un entero positivo de hasta 2147483647"
    if "estado" in data and (
        not isinstance(data["estado"], str) or data["estado"] not in Mesa.ESTADOS
    ):
        return "Estado invalido"
    return None


def save(mesa, status_code=200):
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error_response("Conflicto de unicidad de la mesa", 409)
    return success_response(serialize(mesa), status_code=status_code)


@mesas_bp.get("")
@roles_required("ADMIN")
def list_tables():
    mesas = db.session.execute(db.select(Mesa).order_by(Mesa.numero)).scalars()
    return success_response([serialize(mesa) for mesa in mesas])


@mesas_bp.post("")
@roles_required("ADMIN")
def create_table():
    data = request.get_json(silent=True)
    error = validate(data, creating=True)
    if error:
        return error_response(error, 400)
    mesa = Mesa(**data)
    db.session.add(mesa)
    return save(mesa, 201)


@mesas_bp.get("/<int:mesa_id>")
@roles_required("ADMIN")
def get_table(mesa_id):
    mesa = db.get_or_404(Mesa, mesa_id)
    return success_response(serialize(mesa))


@mesas_bp.patch("/<int:mesa_id>")
@roles_required("ADMIN")
def update_table(mesa_id):
    mesa = db.get_or_404(Mesa, mesa_id)
    data = request.get_json(silent=True)
    error = validate(data)
    if error:
        return error_response(error, 400)
    for key, value in data.items():
        setattr(mesa, key, value)
    return save(mesa)
