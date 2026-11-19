from decimal import Decimal


class PedidoDTO:
    """Serializador de respuesta para pedidos."""

    @staticmethod
    def serialize(pedido):
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
