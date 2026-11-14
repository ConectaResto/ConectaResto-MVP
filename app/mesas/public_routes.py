"""Public table lookup. Blueprint registration is pending integration."""

import re

from flask import Blueprint, url_for

from app.common.responses import error_response, success_response
from app.extensions import db
from app.models import Mesa


public_mesas_bp = Blueprint("public_mesas", __name__, url_prefix="/public/mesas")


@public_mesas_bp.get("/<token>")
def get_public_table(token):
    if re.fullmatch(r"[0-9a-f]{64}", token) is None:
        return error_response("Mesa no encontrada", 404)
    mesa = db.session.execute(
        db.select(Mesa).where(Mesa.public_token == token)
    ).scalar_one_or_none()
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
