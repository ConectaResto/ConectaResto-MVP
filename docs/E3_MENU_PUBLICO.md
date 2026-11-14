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
su token no se expone. Las escrituras siguen requiriendo autenticación y CSRF.

## Decisiones aprobadas en ronda 2

`Mesa.public_token` ya existe: token aleatorio hexadecimal de 64 caracteres,
único y generado por el servidor. Se ha aprobado reutilizarlo, estable entre
servicios, para identificar la mesa y consultar el menú sin iniciar sesión.
Se verifica que cerrar y reabrir la mesa no altera el token almacenado.

Una mesa CERRADA o sin servicio activo no acepta pedidos. No se infiere de
esa restricción una prohibición de lectura del menú. No se expone información
interna ni pedidos ajenos. La creación pública de pedidos espera el contrato
definitivo de Escritorio Codex 1.

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
OCUPADA: la restricción aprobada corresponde a crear pedidos, funcionalidad
que no existe en esta entrega. La consulta no abre servicios, no cambia el
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
La revisión del adaptador sigue siendo estática: no hay endpoint público
de creación de pedidos en E3. El bloqueo por `python-dotenv` se resolvió
creando, con autorización, un `.venv` propio del clon con Python 3.13.18 e
instalando `requirements.txt`, sin modificar el entorno del directorio padre.

Una futura tarea deberá resolver el servicio activo desde la mesa por token,
rechazar pedidos para mesa CERRADA o sin servicio activo y delegar la
creación a esa función, sin escrituras ajenas pendientes. Esta entrega no
añade endpoints públicos de pedidos ni invoca `crear_pedido()` desde el GET.

No hay generador QR en requirements.txt ni bibliotecas `qrcode` o `segno`
instaladas en el entorno existente. Por decisión recibida, el QR gráfico
permanece pendiente, sin dependencias nuevas.
La URL base/dominio sigue pendiente según el plan; no se deriva del Host
recibido ni se envían tokens a generadores externos. Un enlace relativo no
equivale a una imagen QR escaneable.

No se modifica ningún modelo, migración ni frontend. No se crean pedidos
ni contratos de pedidos: cualquier futura dependencia debe acordarse con
**Escritorio Codex 1** antes de implementarse.

## Validación

Desde este clon, con su propio entorno y SQLite aislado:

```powershell
$env:TEST_DATABASE_URL = 'sqlite:///:memory:'
$env:DATABASE_URL = 'sqlite:///:memory:'
$env:PYTHON_DOTENV_DISABLED = '1'
.\.venv\Scripts\python.exe -m pytest -q tests/test_public_menu.py tests/test_public_mesas.py
$e3TestTemp = Join-Path (Get-Location).Path ('.pytest_cache/e3-isolated-' + [guid]::NewGuid().ToString('N'))
.\.venv\Scripts\python.exe -m pytest -q --basetemp $e3TestTemp
```

No se crean archivos `.env` ni se conecta a MySQL. Estas pruebas no acreditan
la lectura física de un QR ni un adaptador público de creación de pedidos.
El temporal nuevo dentro de `.pytest_cache` evita el error de permisos del
directorio temporal global de Pytest en Windows, sin cambiar las pruebas.
Resultado con el entorno propio: 41 casos E3 pasan; suite completa,
375 pasan y 1 se omite (collation específica de MySQL), tras integrar el PR #8.

Se conservan los 24 casos de `test_public_menu.py` y se añaden 17 casos de
resolución pública, tokens inválidos, mesa cerrada, enlaces al catálogo
filtrado y restricciones de acceso y escritura.
