from flask import Blueprint, request

from app.auth.decorators import roles_required
from app.auth.service import current_user
from app.common.responses import error_response, success_response
from app.extensions import db
from app.pedidos.models import Pedido
from app.pedidos.dto import PedidoDTO
from app.pedidos.repository import PedidoRepository
from app.pedidos.service import PedidoError, actualizar_pedido


pedidos_bp = Blueprint("pedidos", __name__, url_prefix="/pedidos")


def responder_error(error):
    return error_response(str(error), error.status_code)


pedidos_bp.register_error_handler(PedidoError, responder_error)


@pedidos_bp.get("")
@roles_required("WAITER", "KITCHEN")
def listar_pedidos():
    estado = request.args.get("estado")
    if estado is not None and estado not in Pedido.ESTADOS:
        raise PedidoError("Estado invalido")
    pedidos = PedidoRepository.list_by_rol_and_estado(
        current_user().rol.name, estado
    )
    return success_response([PedidoDTO.serialize(p) for p in pedidos])


@pedidos_bp.get("/<int:pedido_id>")
@roles_required("WAITER", "KITCHEN")
def consultar_pedido(pedido_id):
    if not 0 < pedido_id <= 2147483647:
        raise PedidoError("Pedido no encontrado", 404)
    pedido = db.get_or_404(Pedido, pedido_id)
    if current_user().rol.name == "KITCHEN" and (
        pedido.estado_preparacion == "NO_ENVIADO" or pedido.estado == "CANCELADO"
    ):
        raise PedidoError("Pedido no encontrado", 404)
    return success_response(PedidoDTO.serialize(pedido))


@pedidos_bp.post("/<int:pedido_id>/autorizar", defaults={"accion": "autorizar"})
@pedidos_bp.post("/<int:pedido_id>/enviar-cocina", defaults={"accion": "enviar-cocina"})
@pedidos_bp.post(
    "/<int:pedido_id>/autorizar-y-enviar-cocina",
    defaults={"accion": "autorizar-y-enviar-cocina"},
)
@pedidos_bp.post("/<int:pedido_id>/entregar", defaults={"accion": "entregar"})
@pedidos_bp.post("/<int:pedido_id>/cancelar", defaults={"accion": "cancelar"})
@roles_required("WAITER")
def ejecutar_accion(pedido_id, accion):
    if request.get_data() and request.get_json(silent=True) != {}:
        raise PedidoError("Esta accion no acepta campos")
    pedido = actualizar_pedido(pedido_id, accion, actor=current_user())
    return success_response(PedidoDTO.serialize(pedido))


@pedidos_bp.patch("/<int:pedido_id>/preparacion")
@roles_required("KITCHEN")
def preparar_pedido(pedido_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or set(data) != {"estado"}:
        raise PedidoError("Se requiere solamente estado")
    pedido = actualizar_pedido(
        pedido_id, "preparacion", actor=current_user(), estado_preparacion=data["estado"],
    )
    return success_response(PedidoDTO.serialize(pedido))
