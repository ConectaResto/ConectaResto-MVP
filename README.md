# ConectaResto-MVP

API REST académica para la gestión de restaurantes, desarrollada con **Python, Flask, SQLAlchemy y MySQL 8**. El código se organiza por dominio. Las rutas reciben las solicitudes HTTP, los servicios aplican las reglas de negocio y los modelos gestionan la persistencia con SQLAlchemy. Los módulos de pedidos y servicios incluyen repositorios para las consultas.

Flask conserva la API JSON, las reglas de negocio, la persistencia, las fotografías de productos y la generación de códigos QR. La interfaz HTML, CSS y JavaScript vive en una SPA independiente que consume esta API. [Repositorio oficial del frontend](https://github.com/ConectaResto/ConectaResto-MVP-Frontend).

> **Alcance:** demostración local. No incluye pagos reales ni despliegue comercial.

## Requisitos

- Windows 11 con PowerShell (los ejemplos usan Windows).
- Python y `pip` instalados. Comprueba `py --version`.
- MySQL 8 iniciado y acceso a MySQL Workbench o a un cliente SQL.
- Git para clonar el proyecto.
- Navegador web.

## 1. Clonar el repositorio

Abre PowerShell en la carpeta donde quieras guardar el proyecto:

```powershell
git clone https://github.com/ConectaResto/ConectaResto-MVP.git
cd ConectaResto-MVP
git branch --show-current
```

La rama para ejecutar la versión integrada es `main`.

## 2. Crear el entorno virtual e instalar dependencias

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Si PowerShell bloquea la activación, ejecuta lo siguiente **solo en esa ventana** y vuelve a activar el entorno:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Cuando aparezca `(.venv)` al comienzo de la terminal, el entorno estará activo. Las dependencias incluyen Flask, Flask-SQLAlchemy, Flask-Migrate, PyMySQL, python-dotenv, pytest y segno.

## 3. Preparar una base MySQL vacía

Con MySQL 8 en funcionamiento, crea una **base nueva** desde MySQL Workbench:

```sql
CREATE DATABASE conectaresto_mvp
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;
```

Si ese nombre ya existe, **no borres ni sobrescribas la base**: elige otro nombre para la prueba. Usa una cuenta MySQL con permisos sobre la base creada.

## 4. Configurar `.env`

En la raíz del repositorio:

```powershell
Copy-Item .env.example .env
notepad .env
```

Adapta los valores de ejemplo a tu instalación:

```dotenv
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=reemplazar-por-una-clave-larga-y-privada
PUBLIC_BASE_URL=http://127.0.0.1:8000
DATABASE_URL=mysql+pymysql://USUARIO:CONTRASENA@127.0.0.1:3306/conectaresto_mvp
```

- `DATABASE_URL` es la URL de conexión de SQLAlchemy a MySQL. Sustituye `USUARIO`, `CONTRASENA` y el nombre de la base por los de tu instalación. Codifica los caracteres reservados de la contraseña (por ejemplo, `@`, `#`, `/` o `:`) para utilizarlos en la URL.
- `SECRET_KEY` firma las cookies de sesión de Flask. Usa una clave larga, privada y propia de la instalación.
- `PUBLIC_BASE_URL` debe apuntar a la SPA independiente. Para la demo local usa `http://127.0.0.1:8000`.
- **Nunca subas `.env`, contraseñas ni claves a GitHub.**

## 5. Aplicar las migraciones

Con `(.venv)` activo y MySQL iniciado:

```powershell
python -m flask --app run.py db upgrade
python -m flask --app run.py db current
```

La segunda instrucción debe indicar la revisión `015_add_cancelado_to_pedidos (head)`.

Las tablas se crean mediante **Flask-Migrate**. No uses `db.create_all()` para sustituir este paso.

## 6. Crear datos y usuarios de demostración

Ejecuta **solo en una base local de prueba**:

```powershell
python -m flask --app run.py seed-demo
```

El comando pide una contraseña y su confirmación, muestra la base de datos de destino y solicita confirmación antes de cargar los datos. **Esa contraseña se utiliza para los usuarios de demostración.**

| Usuario | Rol | Función |
| --- | --- | --- |
| `admin1` | ADMIN | Administrar mesas, catálogo, usuarios y QR |
| `mesero1` | WAITER | Abrir servicios, autorizar y enviar pedidos a Cocina y registrar la entrega |
| `cocinero1` | KITCHEN | Preparar pedidos |
| `cajero1` | CASHIER | Registrar pago simulado y cerrar servicios |

La contraseña **no está escrita en el repositorio**: es la que introduces al ejecutar `seed-demo`.

## 7. Iniciar la API y la SPA

```powershell
python -m flask --app run.py run --host 127.0.0.1 --port 5000 --no-debugger --no-reload
```

Flask sirve la API en `http://127.0.0.1:5000`. Para comprobar el arranque, abre `http://127.0.0.1:5000/health`. `GET /health` devuelve HTTP `200` y JSON con `status: "ok"`.

Desde la raíz del frontend oficial, abre otra terminal y ejecuta el siguiente comando. [README del frontend](https://github.com/ConectaResto/ConectaResto-MVP-Frontend/blob/main/README.md).

```powershell
python -m http.server 8000 --bind 127.0.0.1
```

Abre `http://127.0.0.1:8000/#login`. En desarrollo, Flask permite solicitudes con credenciales desde el origen exacto `http://127.0.0.1:8000`. Usa esa URL en el navegador.

Mantén ambos servidores en ejecución durante la prueba. Para detenerlos, presiona `Ctrl+C` en cada terminal.

## 8. Recorrido rápido de demostración

1. **ADMIN:** entra con `admin1`, comprueba o crea una mesa, categoría y producto; muestra **Ver QR** de la mesa.

   Puedes guardar una imagen del QR y cargarla en el [lector QR online](https://www.codigos-qr.com/lector-qr-online/) para consultar el enlace que contiene. El lector es un servicio externo a ConectaResto.

2. **CLIENTE:** abre el enlace del QR en una ventana privada, sin iniciar sesión; agrega productos y confirma un pedido.
3. **WAITER:** entra con `mesero1`, localiza el pedido en Pendientes de autorización, pulsa **Autorizar y enviar a Cocina**.
4. **KITCHEN:** entra con `cocinero1`, pulsa **En cocina** y luego **Listo para servir**.
5. **WAITER:** pulsa **Entregar** cuando el pedido esté listo. El pedido pasa a **Historial de entregados y cancelados**.
6. **CASHIER:** entra con `cajero1`, registra el **pago simulado** y cierra el servicio.
7. **WAITER:** comprueba que la mesa vuelve a **Disponible**.

Al confirmar un pedido público, el backend reutiliza el servicio activo de la mesa. Si no existe y la mesa está Disponible, lo abre automáticamente y la pasa a Ocupada; el mesero no tiene que abrirlo previamente. También puede abrirlo manualmente desde su panel para tomar un pedido interno. Una mesa Cerrada rechaza pedidos; un fallo en la creación revierte la transacción.

Para usar sesiones de roles distintos, cierra sesión o utiliza perfiles de navegador separados. Las pestañas del mismo perfil suelen compartir sesión.

Mesero distingue pendientes de autorización, pedidos en curso e historial de entregados y cancelados. **Ver detalles** permite consultar productos y cantidades en las tres secciones. La tabla muestra el número visible de mesa o «Mesa sin identificar» si falta la relación.

## 9. Ejecutar las pruebas automatizadas

Con las dependencias instaladas, ejecuta la suite en una terminal de pruebas con SQLite en memoria:

```powershell
$env:TEST_DATABASE_URL = 'sqlite:///:memory:'
python -m pytest -q
```

Una prueba de cotejamiento (`utf8mb4_0900_ai_ci`) requiere MySQL 8 y se omite con SQLite. Usa únicamente bases desechables para las pruebas porque algunos fixtures crean y eliminan tablas.

## Solución de problemas

| Problema | Qué comprobar |
| --- | --- |
| `ModuleNotFoundError` | Activa `.venv` y reinstala `requirements.txt`. |
| Error de conexión MySQL | Servicio MySQL activo, nombre de base, usuario, contraseña y `DATABASE_URL`. |
| Error por tabla o columna faltante | Ejecuta `db current` y verifica que las migraciones lleguen a `015_add_cancelado_to_pedidos`. |
| El inicio de sesión falla | Comprueba que `seed-demo` terminó y usa la contraseña que elegiste allí. |
| El QR no abre en un teléfono | La demo usa `127.0.0.1` para ambos servidores. Abre el enlace del QR en el mismo equipo que ejecuta la demo. |
| El puerto 5000 está ocupado | Detén la otra instancia de Flask antes de volver a iniciarlo. |

## Reactivación administrativa

ADMIN puede usar **Reactivar** en usuarios, categorías y productos inactivos.
Se reutilizan `PATCH /users/<id>`, `PATCH /categories/<id>` y
`PATCH /products/<id>` con `{"is_active": true}`. Solo se admite el booleano
JSON `true`; para desactivar se conserva DELETE y sus protecciones.
La reactivación de usuarios conserva contraseña y rol.

Los listados `/categories?include_inactive=true` y
`/admin/products?include_inactive=true` requieren ADMIN. Las consultas públicas
siguen ocultando inactivos. Reactivar una categoría no reactiva sus productos;
un producto requiere una categoría activa y conserva su disponibilidad.
**Activo** y **Disponible** son estados independientes.

## API y recursos

| Módulo | Endpoints principales |
| --- | --- |
| Autenticación | `GET /auth/csrf`, `POST /auth/login`, `GET /auth/me`, `POST /auth/logout` |
| Mesas y usuarios | `GET /mesas` para Mesero. Administración usa `GET /admin/mesas`, `POST /admin/mesas`, `GET /admin/mesas/<id>/qr.svg` y `GET /users`. |
| Catálogo | `GET /categories` y `GET /products` para el catálogo público. `GET /admin/products` para Administración. |
| Servicios | `GET /servicios` y `GET /servicios/<id>` para Mesero y Caja. `POST /servicios` y `POST /servicios/<id>/pedidos` para Mesero. |
| Pedidos públicos | `GET /public/mesas/<token>` consulta la mesa. `POST /public/mesas/<token>/pedidos` registra el pedido con CSRF y sin iniciar sesión. |
| Mesero | `GET /pedidos` y `GET /pedidos/<id>` consultan pedidos. `POST /pedidos/<id>/autorizar-y-enviar-cocina`, `POST /pedidos/<id>/entregar` y `POST /pedidos/<id>/cancelar` aplican las transiciones permitidas. |
| Cocina | `GET /pedidos` y `GET /pedidos/<id>` consultan pedidos de Cocina. `PATCH /pedidos/<id>/preparacion` actualiza su preparación. |
| Caja | `POST /servicios/<id>/pago-simulado` y `POST /servicios/<id>/cerrar` registran el pago simulado y el cierre. |

- **QR.** Flask genera el SVG al solicitarlo. El enlace abre `/?token=<token>#public` en la SPA. En la demo, la generación usa el origen local permitido cuando la solicitud viene de ese origen y `PUBLIC_BASE_URL` en los demás casos. El enlace anterior `GET /public/mesas/<token>/menu` redirige con HTTP `302` a `PUBLIC_BASE_URL` para un token válido y devuelve `404` para uno inválido.
- **Fotografías.** Flask sirve las imágenes reales de productos activos y disponibles en `GET /products/<id>/image`, desde `instance/uploads/products/`. El SVG predeterminado se sirve desde `img/default-product.svg` en el repositorio frontend.

## Estructura del backend

| Ruta | Responsabilidad |
| --- | --- |
| `run.py`, `app/__init__.py`, `app/config.py` | Punto de entrada, registro de módulos y configuración de Flask. |
| `app/auth/`, `app/users/` | Sesiones, CSRF, roles, usuarios y comandos de carga inicial. |
| `app/catalog/`, `app/mesas/` | Catálogo, fotografías, mesas y acceso al menú por QR. |
| `app/servicios/`, `app/pedidos/` | Servicios de mesa, pedidos, preparación, pago simulado y cierre. |
| `app/common/`, `app/models/`, `app/health/` | Respuestas y errores comunes, registro y base de modelos y comprobación de arranque. |
| `migrations/`, `tests/` | Migraciones de Alembic y pruebas automatizadas. |
