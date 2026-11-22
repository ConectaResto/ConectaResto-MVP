"""Public table lookup, menu and order creation through the shared order service."""

import re

from flask import Blueprint, current_app, redirect, request, url_for

from app.common.responses import error_response, success_response
from app.extensions import db
from app.mesas.models import Mesa
from app.servicios.models import Servicio
from app.pedidos.routes import responder_error
from app.pedidos.service import PedidoError, crear_pedido
from app.servicios.service import _crear_servicio_para_mesa


public_mesas_bp = Blueprint(
    "public_mesas", __name__, url_prefix="/public/mesas",
)


def _find_public_table(token, *, lock=False):
    if re.fullmatch(r"[0-9a-f]{64}", token) is None:
        return None
    query = db.select(Mesa).where(Mesa.public_token == token)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    return db.session.execute(query).scalar_one_or_none()


@public_mesas_bp.get("/<token>")
def get_public_table(token):
    mesa = _find_public_table(token)
    if mesa is None:
        return error_response("Mesa no encontrada", 404)
    # Closing a table restricts future orders, not public menu reading.
    return success_response({
        "numero": mesa.numero,
        "menu": {
            "categories": url_for("categories.list_all"),
            "products": url_for("products.list_all_products"),
        },
    })


@public_mesas_bp.get("/<token>/menu")
def public_menu(token):
    mesa = _find_public_table(token)
    if mesa is None:
        return error_response("Mesa no encontrada", 404)
    base_url = current_app.config.get("PUBLIC_BASE_URL")
    if not base_url:
        return error_response("PUBLIC_BASE_URL no configurada", 500)
    return redirect(f"{base_url.rstrip('/')}/?token={mesa.public_token}#public", code=302)


@public_mesas_bp.post("/<token>/pedidos")
def create_public_order(token):
    try:
        mesa = _find_public_table(token, lock=True)
        if mesa is None:
            raise PedidoError("Mesa no encontrada", 404)
        if mesa.estado == "CERRADA":
            raise PedidoError("La mesa esta cerrada", 409)
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or set(data) != {"items"}:
            raise PedidoError("Se requiere solamente items")
        servicio_id = db.session.execute(
            db.select(Servicio.id).where(
                Servicio.mesa_id == mesa.id, Servicio.estado == "ACTIVO",
            )
        ).scalar_one_or_none()
        if servicio_id is None:
            # Apertura automática: crear servicio si la mesa está disponible.
            servicio = _crear_servicio_para_mesa(mesa.id, abierto_por_id=None)
            servicio_id = servicio.id
        pedido = crear_pedido(servicio_id, data["items"], origen="PUBLICO")
        return success_response({"id": pedido.id, "estado": pedido.estado}, status_code=201)
    except PedidoError as error:
        db.session.rollback()
        return responder_error(error)
    except Exception:
        db.session.rollback()
        raise
