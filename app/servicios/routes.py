from flask import Blueprint, request

from app.auth.decorators import roles_required
from app.auth.service import current_user
from app.common.responses import success_response
from app.extensions import db
from app.models import Servicio
from app.pedidos.dto import PedidoDTO
from app.pedidos.routes import responder_error
from app.pedidos.service import PedidoError, crear_pedido
from app.servicios.dto import ServicioDTO
from app.servicios.repository import ServicioRepository
from app.servicios.service import abrir_servicio, procesar_caja


servicios_bp = Blueprint("servicios", __name__, url_prefix="/servicios")
servicios_bp.register_error_handler(PedidoError, responder_error)


@servicios_bp.post("")
@roles_required("WAITER")
def crear_servicio():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or set(data) != {"mesa_id"}:
        raise PedidoError("Se requiere solamente mesa_id")
    servicio = abrir_servicio(data["mesa_id"], actor=current_user())
    return success_response(ServicioDTO.serialize(servicio), status_code=201)


@servicios_bp.get("")
@roles_required("WAITER", "CASHIER")
def listar_servicios():
    estado = request.args.get("estado")
    if estado is not None:
        if estado not in ("ACTIVO", "CERRADO"):
            raise PedidoError("Estado invalido")
    servicios = ServicioRepository.list_by_estado(estado)
    return success_response([ServicioDTO.serialize(s) for s in servicios])


@servicios_bp.get("/<int:servicio_id>")
@roles_required("WAITER", "CASHIER")
def consultar_servicio(servicio_id):
    if not 0 < servicio_id <= 2147483647:
        raise PedidoError("Servicio no encontrado", 404)
    return success_response(ServicioDTO.serialize(db.get_or_404(Servicio, servicio_id)))


@servicios_bp.post("/<int:servicio_id>/pago-simulado", defaults={"accion": "pago-simulado"})
@servicios_bp.post("/<int:servicio_id>/cerrar", defaults={"accion": "cerrar"})
@roles_required("CASHIER")
def operar_caja(servicio_id, accion):
    if request.get_data() and request.get_json(silent=True) != {}:
        raise PedidoError("Esta accion no acepta campos")
    servicio = procesar_caja(servicio_id, accion, actor=current_user())
    return success_response(
        ServicioDTO.serialize(servicio), status_code=201 if accion == "pago-simulado" else 200,
    )


@servicios_bp.post("/<int:servicio_id>/pedidos")
@roles_required("WAITER")
def crear_pedido_interno(servicio_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or set(data) != {"items"}:
        raise PedidoError("Se requiere solamente items")
    pedido = crear_pedido(
        servicio_id, data["items"], origen="MESERO", creado_por_id=current_user().id,
    )
    return success_response(PedidoDTO.serialize(pedido), status_code=201)
