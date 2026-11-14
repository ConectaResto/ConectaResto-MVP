# Servicios y pedidos E2

Los blueprints `servicios_bp` y `pedidos_bp` se registran en `create_app()`.
Las escrituras utilizan la protección CSRF global y el encabezado
`X-CSRF-Token`, obtenido mediante `GET /auth/csrf`.

| Método y ruta | Entrada | Rol |
|---|---|---|
| POST /servicios | `{"mesa_id": 1}` | WAITER |
| GET /servicios | Filtro opcional `estado=ACTIVO` o `CERRADO` | WAITER |
| GET /servicios/<id> | Servicio con todos sus pedidos | WAITER |
| POST /servicios/<id>/pedidos | `{"items": [{"producto_id": 7, "cantidad": 2}]}` | WAITER |
| GET /pedidos | Filtro opcional `estado` | WAITER, KITCHEN |
| GET /pedidos/<id> | Pedido y detalles con precios históricos | WAITER, KITCHEN |
| POST /pedidos/<id>/autorizar | Cuerpo vacío o `{}` | WAITER |
| POST /pedidos/<id>/enviar-cocina | Cuerpo vacío o `{}` | WAITER |
| PATCH /pedidos/<id>/preparacion | `{"estado": "EN_COCINA"}` o `LISTO_PARA_SERVIR` | KITCHEN |
| POST /pedidos/<id>/entregar | Cuerpo vacío o `{}` | WAITER |

Cocina consulta exclusivamente pedidos con preparación distinta de `NO_ENVIADO`.
Cualquier WAITER puede autorizar y operar pedidos. ADMIN tiene los permisos
administrativos existentes. Los permisos de estas rutas son explícitos por rol.

## Creación compartida

`app.pedidos.service.crear_pedido(servicio_id, items, *, origen, creado_por_id=None)`
devuelve un `Pedido` persistido. Valida servicio activo, lista no vacía,
identificadores y cantidades enteros positivos dentro del rango de Integer,
excluyendo booleanos. Cada item contiene exclusivamente `producto_id` y
`cantidad`. Reutiliza `get_product()` para exigir producto activo, disponible
y categoría activa. Copia `Product.price` a `DetallePedido.precio_unitario`.

Para `MESERO`, `creado_por_id` identifica un WAITER activo. Para `PUBLICO`,
el adaptador de Portátil Codex 2 debe resolver el servicio mediante el token
de mesa e invocar la función sin usuario creador. El contrato compartido
está disponible para esa integración.

La función es dueña del commit y rollback de la sesión. El adaptador debe
invocarla sin escrituras pendientes ajenas a la operación. Pedido y detalles
se guardan atómicamente. Los errores de dominio usan `PedidoError` con
`status_code`. Los errores de persistencia se revierten y se propagan.

Los importes se calculan con Decimal y se serializan como cadenas con dos
decimales. El total se obtiene de los detalles. La autorización y el envío
conservan los precios y productos registrados aunque cambie el catálogo.

## Transiciones

| Acción | Estado del pedido | Estado de preparación |
|---|---|---|
| Crear | PENDIENTE | NO_ENVIADO |
| Autorizar | PENDIENTE | NO_ENVIADO |
| Enviar autorizado con detalles | EN_PREPARACION | RECIBIDO |
| Cocina comienza | EN_PREPARACION | EN_COCINA |
| Cocina termina | LISTO | LISTO_PARA_SERVIR |
| Mesero entrega | ENTREGADO | LISTO_PARA_SERVIR |

Autorizar registra usuario y fecha, incluso para pedidos creados por el
propio mesero. Las acciones repetidas o fuera de secuencia devuelven 409.
Las transiciones bloquean la fila del pedido en MySQL y se confirman
atómicamente. Todas requieren servicio activo.

La apertura cambia condicionalmente la mesa de DISPONIBLE a OCUPADA y crea
el servicio en una transacción. También comprueba servicios activos previos.
La migración 008 aporta la restricción única por mesa para servicios activos.
Las instalaciones MySQL deben tener aplicadas las migraciones de Kilo 1.
`db.create_all()` por sí solo no crea esa restricción definida en migración.

Las respuestas reutilizan `success_response` y `error_response`. Creaciones
devuelven 201, consultas y transiciones 200. Se utilizan 400 para validación
y CSRF, 401 para sesión ausente, 403 para rol incorrecto, 404 para recursos
inexistentes o productos no disponibles y 409 para conflictos de estado.

## Verificación

`pytest -q tests/test_servicios.py tests/test_pedidos.py` cubre apertura,
agrupación, permisos, CSRF, cantidades, productos, precios históricos,
transiciones y rollback después de fallos de persistencia.
La validación de concurrencia y de la restricción generada de la migración
008 requiere un entorno MySQL de pruebas autorizado.
