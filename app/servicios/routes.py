from flask import Blueprint, request

from app.auth.decorators import roles_required
from app.auth.service import current_user
from app.common.responses import success_response
from app.extensions import db
from app.models import Servicio
from app.pedidos.routes import responder_error, serializar_pedido
from app.pedidos.service import PedidoError, crear_pedido
from app.servicios.service import abrir_servicio, calcular_total_servicio, procesar_caja


servicios_bp = Blueprint("servicios", __name__, url_prefix="/servicios")
servicios_bp.register_error_handler(PedidoError, responder_error)


def serializar_servicio(servicio):
    pago = servicio.pago
    return {
        "id": servicio.id, "mesa_id": servicio.mesa_id,
        "abierto_por_id": servicio.abierto_por_id, "estado": servicio.estado,
        "pedidos": [serializar_pedido(p) for p in servicio.pedidos],
        "total": format(calcular_total_servicio(servicio.id), ".2f"),
        "pago": {
            "id": pago.id, "servicio_id": pago.servicio_id,
            "importe": format(pago.importe, ".2f"),
            "registrado_por_id": pago.registrado_por_id,
            "fecha_registro": pago.fecha_registro.isoformat(),
        } if pago is not None else None,
    }


@servicios_bp.post("")
@roles_required("WAITER")
def crear_servicio():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or set(data) != {"mesa_id"}:
        raise PedidoError("Se requiere solamente mesa_id")
    servicio = abrir_servicio(data["mesa_id"], actor=current_user())
    return success_response(serializar_servicio(servicio), status_code=201)


@servicios_bp.get("")
@roles_required("WAITER")
def listar_servicios():
    consulta = db.select(Servicio).order_by(Servicio.id)
    estado = request.args.get("estado")
    if estado is not None:
        if estado not in ("ACTIVO", "CERRADO"):
            raise PedidoError("Estado invalido")
        consulta = consulta.where(Servicio.estado == estado)
    return success_response([serializar_servicio(s) for s in db.session.execute(consulta).scalars()])


@servicios_bp.get("/<int:servicio_id>")
@roles_required("WAITER", "CASHIER")
def consultar_servicio(servicio_id):
    if not 0 < servicio_id <= 2147483647:
        raise PedidoError("Servicio no encontrado", 404)
    return success_response(serializar_servicio(db.get_or_404(Servicio, servicio_id)))


@servicios_bp.post("/<int:servicio_id>/pago-simulado", defaults={"accion": "pago-simulado"})
@servicios_bp.post("/<int:servicio_id>/cerrar", defaults={"accion": "cerrar"})
@roles_required("CASHIER")
def operar_caja(servicio_id, accion):
    if request.get_data() and request.get_json(silent=True) != {}:
        raise PedidoError("Esta accion no acepta campos")
    servicio = procesar_caja(servicio_id, accion, actor=current_user())
    return success_response(
        serializar_servicio(servicio), status_code=201 if accion == "pago-simulado" else 200,
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
    return success_response(serializar_pedido(pedido), status_code=201)
