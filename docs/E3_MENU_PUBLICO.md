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

## Ruta implementada, pendiente de registro

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

**Pendiente para Escritorio Kilo 1:** registrar el blueprint en `create_app()`,
después del registro de modelos y antes de devolver la aplicación:

```python
from app.mesas.public_routes import public_mesas_bp
app.register_blueprint(public_mesas_bp)
```

Por instrucción de ChatGPT A, `app/__init__.py` no se modifica en esta entrega.
Hasta integrar ese registro, la factory normal no expone esta ruta (404).
`tests/test_public_mesas.py` registra el blueprint únicamente en su fixture
local y verifica la ruta con la autenticación, CSRF y catálogo existentes.

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

Desde este clon, con el intérprete del entorno existente:

```powershell
..\.venv\Scripts\python.exe -m pytest -q tests/test_public_menu.py
..\.venv\Scripts\python.exe -m pytest -q tests/test_public_mesas.py
..\.venv\Scripts\python.exe -m pytest -q
```

Estas pruebas usan la configuración de pruebas existente. No acreditan la
lectura física de un QR ni una integración con pedidos.

Se conservan los 24 casos de `test_public_menu.py` y se añaden 17 casos de
resolución pública, tokens inválidos, mesa cerrada, enlaces al catálogo
filtrado y restricciones de acceso y escritura.
