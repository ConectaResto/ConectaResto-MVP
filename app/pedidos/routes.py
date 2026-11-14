from decimal import Decimal

from flask import Blueprint, request

from app.auth.decorators import roles_required
from app.auth.service import current_user
from app.common.responses import error_response, success_response
from app.extensions import db
from app.models import Pedido
from app.pedidos.service import PedidoError, actualizar_pedido


pedidos_bp = Blueprint("pedidos", __name__, url_prefix="/pedidos")


def responder_error(error):
    return error_response(str(error), error.status_code)


pedidos_bp.register_error_handler(PedidoError, responder_error)


def serializar_pedido(pedido):
    detalles = [{
        "id": detalle.id, "producto_id": detalle.producto_id,
        "cantidad": detalle.cantidad,
        "precio_unitario": format(detalle.precio_unitario, ".2f"),
        "subtotal": format(detalle.precio_unitario * detalle.cantidad, ".2f"),
    } for detalle in pedido.detalles]
    return {
        "id": pedido.id, "servicio_id": pedido.servicio_id,
        "origen": pedido.origen, "creado_por_id": pedido.creado_por_id,
        "autorizado_por_id": pedido.autorizado_por_id,
        "autorizado_at": pedido.autorizado_at.isoformat() if pedido.autorizado_at else None,
        "estado": pedido.estado, "estado_preparacion": pedido.estado_preparacion,
        "items": detalles,
        "total": format(sum((d.precio_unitario * d.cantidad for d in pedido.detalles), Decimal("0.00")), ".2f"),
    }


@pedidos_bp.get("")
@roles_required("WAITER", "KITCHEN")
def listar_pedidos():
    consulta = db.select(Pedido).order_by(Pedido.id)
    if current_user().rol.name == "KITCHEN":
        consulta = consulta.where(Pedido.estado_preparacion != "NO_ENVIADO")
    estado = request.args.get("estado")
    if estado is not None:
        if estado not in ("PENDIENTE", "EN_PREPARACION", "LISTO", "ENTREGADO"):
            raise PedidoError("Estado invalido")
        consulta = consulta.where(Pedido.estado == estado)
    return success_response([serializar_pedido(p) for p in db.session.execute(consulta).scalars()])


@pedidos_bp.get("/<int:pedido_id>")
@roles_required("WAITER", "KITCHEN")
def consultar_pedido(pedido_id):
    if not 0 < pedido_id <= 2147483647:
        raise PedidoError("Pedido no encontrado", 404)
    pedido = db.get_or_404(Pedido, pedido_id)
    if current_user().rol.name == "KITCHEN" and pedido.estado_preparacion == "NO_ENVIADO":
        raise PedidoError("Pedido no encontrado", 404)
    return success_response(serializar_pedido(pedido))


@pedidos_bp.post("/<int:pedido_id>/autorizar", defaults={"accion": "autorizar"})
@pedidos_bp.post("/<int:pedido_id>/enviar-cocina", defaults={"accion": "enviar-cocina"})
@pedidos_bp.post("/<int:pedido_id>/entregar", defaults={"accion": "entregar"})
@roles_required("WAITER")
def ejecutar_accion(pedido_id, accion):
    if request.get_data() and request.get_json(silent=True) != {}:
        raise PedidoError("Esta accion no acepta campos")
    pedido = actualizar_pedido(pedido_id, accion, actor=current_user())
    return success_response(serializar_pedido(pedido))


@pedidos_bp.patch("/<int:pedido_id>/preparacion")
@roles_required("KITCHEN")
def preparar_pedido(pedido_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or set(data) != {"estado"}:
        raise PedidoError("Se requiere solamente estado")
    pedido = actualizar_pedido(
        pedido_id, "preparacion", actor=current_user(), estado_preparacion=data["estado"],
    )
    return success_response(serializar_pedido(pedido))
