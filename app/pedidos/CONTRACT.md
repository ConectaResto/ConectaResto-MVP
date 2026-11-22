# Servicios y pedidos E2

Los blueprints `servicios_bp` y `pedidos_bp` se registran en `create_app()`.
Las escrituras utilizan la protección CSRF global y el encabezado
`X-CSRF-Token`, obtenido mediante `GET /auth/csrf`.

| Método y ruta | Entrada | Rol |
|---|---|---|
| POST /servicios | `{"mesa_id": 1}` | WAITER |
| GET /servicios | Filtro opcional `estado=ACTIVO` o `CERRADO` | WAITER, CASHIER |
| GET /servicios/<id> | Servicio con todos sus pedidos | WAITER, CASHIER |
| POST /servicios/<id>/pedidos | `{"items": [{"producto_id": 7, "cantidad": 2}]}` | WAITER |
| GET /pedidos | Filtro opcional `estado` | WAITER, KITCHEN |
| GET /pedidos/<id> | Pedido y detalles con precios históricos | WAITER, KITCHEN |
| POST /pedidos/<id>/autorizar | Cuerpo vacío o `{}` | WAITER |
| POST /pedidos/<id>/enviar-cocina | Cuerpo vacío o `{}` | WAITER |
| POST /pedidos/<id>/autorizar-y-enviar-cocina | Cuerpo vacío o `{}` | WAITER |
| PATCH /pedidos/<id>/preparacion | `{"estado": "EN_COCINA"}` o `LISTO_PARA_SERVIR` | KITCHEN |
| POST /pedidos/<id>/entregar | Cuerpo vacío o `{}` | WAITER |

## Consultas operativas

`GET /mesas` permite a WAITER consultar `id`, `numero` y `estado`, ordenados
por número visible. Los filtros opcionales `id`, `numero` y `estado` se
combinan mediante AND. Los dos primeros son enteros positivos hasta
2147483647. Los estados admitidos son DISPONIBLE, OCUPADA y CERRADA.
Sin filtro `estado`, se excluyen las mesas CERRADA, también al filtrar por
`id` o `numero`. El filtro explícito `estado=CERRADA` sigue disponible.
Un filtro inválido devuelve 400. Una búsqueda sin coincidencias devuelve
200 con `data: []`. Esta consulta utiliza la sesión existente y devuelve
exclusivamente esos tres campos de mesa.

`GET /admin/mesas` requiere ADMIN y excluye las mesas CERRADA. El cierre
lógico usa `PATCH /admin/mesas/<id>` con `{"estado": "CERRADA"}` y conserva
el registro y su historial. Con un servicio ACTIVO, cambiar el estado
a CERRADA o DISPONIBLE devuelve 409.
Una mesa CERRADA no puede pasar directamente a OCUPADA: el PATCH devuelve
409 sin modificar ninguno de los campos enviados. Puede regresar a DISPONIBLE
mediante el PATCH autorizado para ADMIN, siempre que no tenga un servicio ACTIVO.

`GET /servicios?estado=ACTIVO` permite a CASHIER descubrir servicios sin
conocer sus IDs. Reutiliza la misma respuesta del listado de WAITER,
incluidos `pedidos`, `total` decimal como cadena y `pago` (objeto o null).
Sin filtro se listan todos los servicios. También se admite estado CERRADO.
El frontend puede distinguir servicios activos con pago registrado para
cerrarlos, servicios sin pago con pedidos entregados y total positivo para
cobrarlos, y servicios vacíos para cerrarlos sin pago. Las operaciones de
caja vuelven a validar el estado al ejecutarse.

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
el adaptador debe resolver el servicio mediante el token
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
| Autorizar y enviar a cocina con detalles | EN_PREPARACION | RECIBIDO |
| Cocina comienza | EN_PREPARACION | EN_COCINA |
| Cocina termina | LISTO | LISTO_PARA_SERVIR |
| Mesero entrega | ENTREGADO | LISTO_PARA_SERVIR |

Autorizar registra usuario y fecha, incluso para pedidos creados por el
propio mesero. Las acciones repetidas o fuera de secuencia devuelven 409.
Las transiciones bloquean la fila del pedido en MySQL y se confirman
atómicamente. Todas requieren servicio activo.

La acción combinada usa el CSRF global y requiere un WAITER activo, un
pedido `PENDIENTE` y `NO_ENVIADO` con detalles, y un servicio activo sin pago.
Si el pedido aún no está autorizado, registra el usuario de la sesión y la
fecha. Si ya fue autorizado, conserva `autorizado_por_id` y `autorizado_at`,
aunque lo envíe otro mesero. La autorización y el envío se confirman juntos
en una sola transacción. Devuelve 200 con el pedido y sus detalles históricos.

Para esta acción se devuelve 400 ante un cuerpo inválido o CSRF inválido,
401 sin sesión con CSRF válido, 403 para roles distintos de WAITER, 404 si el
pedido no existe y 409 si el servicio está cerrado o pagado, el pedido carece
de detalles o ya no está pendiente sin enviar. Los endpoints individuales
`/autorizar` y `/enviar-cocina` siguen disponibles con sus reglas previas.

La apertura cambia condicionalmente la mesa de DISPONIBLE a OCUPADA y crea
el servicio en una transacción. También comprueba servicios activos previos.
La migración 008 aporta la restricción única por mesa para servicios activos.
Las instalaciones MySQL deben tener aplicadas las migraciones de la versión 008.
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
