# E3 — Acceso público y menú QR

Responsable: Backend QR y menú público.

## Lectura del documento y estado actual

Referencia actual: main `91f416c`, posterior al PR #47. Las rondas, commits y cifras de pruebas siguientes son registros históricos, no una nueva ejecución ni el total actual. Se conserva su trazabilidad.

Actualmente el POST público reutiliza el servicio ACTIVO o lo abre para una mesa DISPONIBLE; no exige apertura previa del mesero. El código está en `app/mesas/public_routes.py` y `_crear_servicio_para_mesa()` de `app/servicios/service.py`. Las pruebas `test_public_order_first_creates_service_and_ocupa_mesa`, `test_public_order_second_reuses_service` y `test_public_order_invalid_product_leaves_mesa_disponible` de `tests/test_public_orders.py` cubren apertura, reutilización y rollback. La última suite previa a publicar F dio 692 aprobadas y 1 omitida; no acredita un nuevo recorrido manual integral.

## Parte independiente verificada

Se reutilizan los endpoints de `app/catalog/routes.py`, sin duplicarlos:

| Método y ruta | Acceso y resultado |
|---|---|
| `GET /categories` | Sin autenticación; categorías activas, incluidas las vacías |
| `GET /categories/<int:id>` | Categoría activa; 404 si no existe o está inactiva |
| `GET /products` | Productos activos, disponibles y con categoría activa |
| `GET /products?categoria_id=<id>` | Mismos filtros públicos, restringidos a la categoría |
| `GET /products/<int:id>` | Producto público válido; 404 en cualquier otro caso |

Se conserva el formato `success_response` / `error_response` existente y
el precio como cadena decimal. Los parámetros enviados por el cliente no
habilitan la consulta de recursos inactivos. El menú es consultable sin mesa;
eso ya forma parte del contrato del catálogo.

`tests/test_public_menu.py` cubre el recorrido HTTP sin autenticación,
recursos ocultos por cada condición, filtros por categoría, precios y
restricciones de acceso. Una mesa existente o inexistente permanece
inaccesible mediante las rutas administrativas para clientes anónimos;
su token no se expone. Las escrituras administrativas siguen requiriendo
autenticación y CSRF; la creación pública requiere CSRF sin login.

## Decisiones aprobadas en ronda 2

`Mesa.public_token` ya existe: token aleatorio hexadecimal de 64 caracteres,
único y generado por el servidor. Se ha aprobado reutilizarlo, estable entre
servicios, para identificar la mesa y consultar el menú sin iniciar sesión.
Se verifica que cerrar y reabrir la mesa no altera el token almacenado.

En la ronda 2 original, una mesa CERRADA o sin servicio activo no aceptaba pedidos. En main actual se conserva el rechazo de CERRADA y se admite apertura automática para DISPONIBLE. No se infiere de
esa restricción una prohibición de lectura del menú. No se expone información
interna ni pedidos ajenos. La creación pública reutiliza el contrato
compartido del módulo de servicios y pedidos, sin modificar su implementación.

## Ruta implementada y registrada

`app/mesas/public_routes.py` definió inicialmente `public_mesas_bp` con la ruta JSON:
`GET /public/mesas/<token>`, sin login. Resuelve el `Mesa.public_token`
existente (64 caracteres hexadecimales minúsculos). Respuesta 200:

```json
{"success": true, "data": {"numero": 7, "menu": {"categories": "/categories", "products": "/products"}}}
```

No expone id interno, estado, token, servicios ni pedidos. Los enlaces se
construyen con `url_for` sobre las rutas existentes, sin duplicar el catálogo.
Token mal formado o inexistente: 404, con la misma respuesta
`{"success": false, "error": "Mesa no encontrada"}`.

CERRADA conserva respuesta 200 de solo lectura, igual que DISPONIBLE y
OCUPADA: la restricción aprobada corresponde a crear pedidos. La consulta no abre servicios, no cambia el
estado, no rota el token ni autentica al cliente. No admite escrituras.

El blueprint está registrado en `create_app()`, junto al módulo de mesas:

```python
from app.mesas.public_routes import public_mesas_bp
app.register_blueprint(public_mesas_bp)
```

La actualización del PR #7 autoriza este registro mínimo en `app/__init__.py`.
`tests/test_public_mesas.py` verifica el registro de la factory real; no
registra rutas artificialmente en su fixture. Conserva autenticación,
CSRF y catálogo existentes.

## Compatibilidad con pedidos (revisión de origin/main, PR #9)

Se revisaron `app/pedidos/service.py` y `app/pedidos/CONTRACT.md` en
`origin/main` (`5cc9edf`). El contrato compartido permite invocar
`crear_pedido(servicio_id, items, origen="PUBLICO")` sin usuario creador.
La función valida el servicio activo, cantidades y productos del catálogo,
captura precios y controla commit/rollback. Es reutilizable sin duplicar
esas reglas. `origin/main` (`5cc9edf`) está integrado localmente mediante
el merge `d94271d`; se conservaron los módulos de servicios y pedidos.
También se integró el PR #8 de frontend (`origin/main` en `439232d`)
mediante el merge `9836f9d`, sin conflictos ni cambios al frontend integrado.
El bloqueo por `python-dotenv` se resolvió
creando, con autorización, un `.venv` propio del clon con Python 3.13.18 e
instalando `requirements.txt`, sin modificar el entorno del directorio padre.

## Ronda B — creación pública de pedidos

`POST /public/mesas/<token>/pedidos` no requiere login. Primero se obtiene
un token CSRF mediante `GET /auth/csrf`, conservando la cookie de sesión,
y se envía en `X-CSRF-Token`. No se introduce ninguna exención CSRF.

Entrada JSON exclusiva:

```json
{"items": [{"producto_id": 7, "cantidad": 2}]}
```

El adaptador valida el token, bloquea la mesa para comprobar que no esté
CERRADA y resuelve su servicio ACTIVO. No acepta `servicio_id`, usuario,
origen ni precios enviados por el cliente. Delega a
`crear_pedido(servicio_id, items, origen="PUBLICO")` sin usuario creador,
sin duplicar validación de items, productos, precios ni persistencia.
El GET no crea pedidos. El servicio compartido confirma la transacción;
los rechazos previos liberan los bloqueos mediante rollback. Los errores
de dominio reutilizan `PedidoError` y `responder_error` existentes.

Respuesta 201 mínima, exclusivamente del pedido recién creado:

```json
{"success": true, "data": {"id": 1, "estado": "PENDIENTE"}}
```

| Estado HTTP | Motivo |
|---|---|
| 400 | CSRF ausente/inválido, JSON o items inválidos |
| 404 | Token mal formado/inexistente o producto no público válido |
| 409 | Mesa CERRADA; sin servicio activo y no disponible para abrirlo; servicio con pago u otro conflicto de dominio |

En la ronda B original no se creaban servicios automáticamente. En main actual, si no hay servicio ACTIVO, el POST llama a `_crear_servicio_para_mesa()` y exige una mesa DISPONIBLE. Se abre con `abierto_por_id=None`, pasa la mesa a OCUPADA y se confirma junto al pedido; un error revierte ambos. Si hay servicio ACTIVO se reutiliza, aunque existan servicios cerrados anteriores. El token permanece estable. No se habilita consulta
pública de pedidos o servicios ni se revelan identificadores de usuarios.
Los GET internos conservan sus permisos. La semántica CSRF y los bloqueos
de base de datos existentes se mantienen; concurrencia MySQL no se acredita
con SQLite.

El QR gráfico se genera localmente con `segno` (en `requirements.txt`),
sin servicios externos. La URL base se configura con `PUBLIC_BASE_URL`
(obligatoria, sin predeterminado `localhost`; no se deriva del `Host` ni se
envían tokens a generadores externos). Véase `docs/QR_PUBLICO.md`,
`app/mesas/routes.py`, `app/mesas/public_routes.py` y
`tests/test_qr_publico.py`.

La ronda B original no modificó modelos, migraciones ni el servicio compartido; la apertura automática posterior usa el helper de servicios y la revisión `013_allow_null_abierto_por_id` permite el abridor nulo. La interfaz del cliente se describe al final de este documento.
No se instalan dependencias nuevas.

## Validación histórica y comandos de repetición

Desde este clon, con su propio entorno y SQLite aislado:

```powershell
$env:TEST_DATABASE_URL = 'sqlite:///:memory:'
$env:DATABASE_URL = 'sqlite:///:memory:'
$env:PYTHON_DOTENV_DISABLED = '1'
.\.venv\Scripts\python.exe -m pytest -q tests/test_public_menu.py tests/test_public_mesas.py tests/test_public_orders.py
$e3TestTemp = Join-Path (Get-Location).Path ('.pytest_cache/e3-isolated-' + [guid]::NewGuid().ToString('N'))
.\.venv\Scripts\python.exe -m pytest -q --basetemp $e3TestTemp
```

No se crean archivos `.env` ni se conecta a MySQL. Estas pruebas no acreditan
la lectura física de un QR.
El temporal nuevo dentro de `.pytest_cache` evita el error de permisos del
directorio temporal global de Pytest en Windows, sin cambiar las pruebas.
Referencia de E3 anterior: 41 casos E3 pasan; suite completa,
375 pasan y 1 se omite (collation específica de MySQL), tras integrar el PR #8.

Se conservan los 24 casos de `test_public_menu.py` y se añaden 17 casos de
resolución pública, tokens inválidos, mesa cerrada, enlaces al catálogo
filtrado y restricciones de acceso y escritura.
La ronda B añade pruebas de creación anónima, origen y precios del servicio
compartido, aislamiento entre mesas y servicios, reapertura con token estable,
rechazos por estado, token, productos, cuerpo y CSRF, y rollback sin pedidos
parciales. Se utilizan los blueprints reales registrados en la factory.
Resultado de ronda B: 68 casos públicos pasan (41 E3 y 27 pedidos públicos);
suite completa: 402 pasan y 1 se omite por collation específica de MySQL.

Las rutas actuales del blueprint son GET `/public/mesas/<token>`, GET `/public/mesas/<token>/menu` y POST `/public/mesas/<token>/pedidos`. Solo el POST puede abrir un servicio y crear un pedido; exige CSRF. Los permisos internos no cambian.

## Interfaz de cliente por QR

La página `/public/mesas/<token>/menu` muestra mesa, categorías, nombres,
descripciones y precios del catálogo disponible. El carrito permite agregar,
quitar y editar cantidades enteras positivas hasta el límite Integer del
backend. Se conserva solo en memoria de la página, sin persistirlo entre
servicios o recargas. Los importes se calculan exactamente en centavos con
BigInt y se muestran con dos decimales, sin asignar una moneda.

El total es estimado: el backend valida productos y precios al recibir el
pedido. No se realizan pagos desde esta página. La revisión de cantidades y
total es obligatoria antes del botón «Confirmar y enviar». Durante el envío
se bloquean las modificaciones y los botones para evitar doble clic. Solo
una respuesta válida 201 limpia el carrito y muestra ID y estado del pedido;
la respuesta no contiene un total confirmado ni seguimiento público.

Se obtiene CSRF mediante el GET existente y se conserva su cookie, sin login.
No se añade ningún endpoint. Los errores HTTP conservan el carrito y muestran
el rechazo del dominio, incluida mesa cerrada o no disponible para abrir un servicio.
Si falla la red tras iniciar el POST o el servidor responde 5xx, el resultado
puede ser incierto: se indica consultar al mesero antes de volver a enviar.
Nunca se reintenta automáticamente un POST ni se promete idempotencia del
backend. Un error de carga del catálogo ofrece un reintento manual solo de GET.

Nombre, descripción, categorías y mensajes se insertan con `textContent`;
no se interpreta HTML del catálogo. El diseño independiente se adapta a
celular y escritorio sin cargar los controles de autenticación de paneles.
Las pruebas del QR conservan los permisos, el 404 de token y la ausencia de
sesión inicial; las expectativas de enlaces JSON se actualizan a atributos
de configuración del menú interactivo. `tests/test_public_menu_ui.py` añade
pruebas HTTP y un recorrido en navegador real, sin dependencias instaladas.

Validación de la interfaz: 91 pruebas específicas públicas/QR pasan; suite
completa: 541 pasan y 1 se omite por collation MySQL. Después del ajuste de
nombres largos, las 6 pruebas de interfaz se verifican nuevamente. El
recorrido en Edge sin ventana usa 390 px y 1280 px, sin desbordamiento,
confirma un único POST ante doble clic, persistencia del pedido anónimo,
carrito conservado ante 400/404/409/500 y errores de red, y texto de catálogo
tratado como texto. No sustituye la prueba física del QR en un celular real.
