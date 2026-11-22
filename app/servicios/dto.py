from app.pedidos.dto import PedidoDTO
from app.pedidos.models import Pedido
from app.servicios.repository import ServicioRepository


class ServicioDTO:
    """Serializador de respuesta para servicios."""

    @staticmethod
    def serialize(servicio):
        pago = servicio.pago
        return {
            "id": servicio.id, "mesa_id": servicio.mesa_id,
            "mesa_numero": servicio.mesa.numero,
            "abierto_por_id": servicio.abierto_por_id, "estado": servicio.estado,
            "pedidos": [PedidoDTO.serialize(p) for p in servicio.pedidos],
            "total": format(ServicioRepository.calcular_total(
                servicio.id, estados=Pedido.ESTADOS_NO_CANCELADOS,
            ), ".2f"),
            "pago": {
                "id": pago.id, "servicio_id": pago.servicio_id,
                "importe": format(pago.importe, ".2f"),
                "registrado_por_id": pago.registrado_por_id,
                "fecha_registro": pago.fecha_registro.isoformat(),
            } if pago is not None else None,
        }
