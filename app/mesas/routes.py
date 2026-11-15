from io import BytesIO

from flask import Blueprint, current_app, request, Response
from sqlalchemy.exc import IntegrityError

import segno

from app.auth.decorators import roles_required
from app.common.responses import error_response, success_response
from app.extensions import db
from app.models import Mesa


mesas_bp = Blueprint("mesas", __name__)


def serialize(mesa, *, include_public_token=True):
    data = {
        "id": mesa.id, "numero": mesa.numero,
        "estado": mesa.estado,
    }
    if include_public_token:
        data["public_token"] = mesa.public_token
    return data


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


@mesas_bp.get("/mesas")
@roles_required("WAITER")
def consultar_mesas():
    consulta = db.select(Mesa).order_by(Mesa.numero)
    for campo in ("id", "numero"):
        valor = request.args.get(campo)
        if valor is not None:
            try:
                valor = int(valor)
            except ValueError:
                return error_response(f"{campo} debe ser un entero positivo valido", 400)
            if not 0 < valor <= 2147483647:
                return error_response(f"{campo} debe ser un entero positivo valido", 400)
            consulta = consulta.where(getattr(Mesa, campo) == valor)
    estado = request.args.get("estado")
    if estado is not None:
        error = validate({"estado": estado})
        if error:
            return error_response(error, 400)
        consulta = consulta.where(Mesa.estado == estado)
    mesas = db.session.execute(consulta).scalars()
    return success_response([serialize(mesa, include_public_token=False) for mesa in mesas])


@mesas_bp.get("/admin/mesas")
@roles_required("ADMIN")
def list_tables():
    mesas = db.session.execute(db.select(Mesa).order_by(Mesa.numero)).scalars()
    return success_response([serialize(mesa) for mesa in mesas])


@mesas_bp.post("/admin/mesas")
@roles_required("ADMIN")
def create_table():
    data = request.get_json(silent=True)
    error = validate(data, creating=True)
    if error:
        return error_response(error, 400)
    mesa = Mesa(**data)
    db.session.add(mesa)
    return save(mesa, 201)


@mesas_bp.get("/admin/mesas/<int:mesa_id>")
@roles_required("ADMIN")
def get_table(mesa_id):
    mesa = db.get_or_404(Mesa, mesa_id)
    return success_response(serialize(mesa))


@mesas_bp.patch("/admin/mesas/<int:mesa_id>")
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


@mesas_bp.get("/admin/mesas/<int:mesa_id>/qr.svg")
@roles_required("ADMIN")
def qr_table(mesa_id):
    mesa = db.get_or_404(Mesa, mesa_id)
    base_url = current_app.config.get("PUBLIC_BASE_URL")
    if not base_url:
        return error_response("PUBLIC_BASE_URL no configurada", 500)
    menu_url = f"{base_url.rstrip('/')}/public/mesas/{mesa.public_token}/menu"
    qr = segno.make(menu_url)
    svg = BytesIO()
    qr.save(svg, kind="svg", scale=4, light="#fff")
    return Response(svg.getvalue(), mimetype="image/svg+xml")
