# E3 — Acceso público y menú QR

Responsable: **Portátil Codex 2** (backend QR y menú público).

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

Una mesa CERRADA o sin servicio activo no acepta pedidos. No se infiere de
esa restricción una prohibición de lectura del menú. No se expone información
interna ni pedidos ajenos. La creación pública reutiliza el contrato
compartido de Escritorio Codex 1, sin modificar su implementación.

## Ruta implementada y registrada

`app/mesas/public_routes.py` define `public_mesas_bp` y una única ruta:
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
| 409 | Mesa CERRADA o sin servicio ACTIVO (inexistente o cerrado) |

No se crean servicios automáticamente. El token permanece estable y se
resuelve el servicio activo actual en cada petición. No se habilita consulta
pública de pedidos o servicios ni se revelan identificadores de usuarios.
Los GET internos conservan sus permisos. La semántica CSRF y los bloqueos
de base de datos existentes se mantienen; concurrencia MySQL no se acredita
con SQLite.

No hay generador QR en requirements.txt ni bibliotecas `qrcode` o `segno`
instaladas en el entorno existente. Por decisión recibida, el QR gráfico
permanece pendiente, sin dependencias nuevas.
La URL base/dominio sigue pendiente según el plan; no se deriva del Host
recibido ni se envían tokens a generadores externos. Un enlace relativo no
equivale a una imagen QR escaneable.

No se modifica ningún modelo, migración, frontend ni servicio de pedidos.
No se instalan dependencias nuevas.

## Validación

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
