# ConectaResto-MVP

Aplicación académica de gestión de restaurantes desarrollada con **Python, Flask, MySQL 8 y HTML/CSS/JavaScript**. Permite gestionar mesas y productos, recibir pedidos mediante QR, autorizarlos, prepararlos y registrar pagos simulados.

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

Cuando aparezca `(.venv)` al comienzo de la terminal, el entorno estará activo. Las dependencias incluyen Flask, Flask-Migrate, PyMySQL, python-dotenv, pytest y segno.

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

- Sustituye `USUARIO` y `CONTRASENA` por las credenciales **locales** de MySQL.
- Si la contraseña de MySQL tiene caracteres especiales (por ejemplo, `@`, `#`, `/` o `:`), codifícalos para utilizarlos dentro de una URL.
- `PUBLIC_BASE_URL` apunta a la SPA independiente, por ejemplo `http://127.0.0.1:8000` para la demo local. Cambia el valor si tu configuración anterior apuntaba a Flask. Los QR nuevos abren `/?token=<token>#public`; los enlaces antiguos `/public/mesas/<token>/menu` redirigen a la SPA.
- **Nunca subas `.env`, contraseñas ni claves a GitHub.**

## 5. Aplicar las migraciones

Con `(.venv)` activo y MySQL iniciado:

```powershell
python -m flask --app run.py db upgrade
python -m flask --app run.py db current
```

La segunda instrucción debe indicar la revisión `014_add_image_filename_to_products (head)`.

Las tablas se crean mediante **Flask-Migrate**. No uses `db.create_all()` para sustituir este paso.

## 6. Crear datos y usuarios de demostración

Ejecuta **solo en una base local de prueba**:

```powershell
python -m flask --app run.py seed-demo
```

El comando muestra la base de datos de destino, solicita confirmación y pide una contraseña (con confirmación). **Esa contraseña se utiliza para los usuarios de demostración**:

| Usuario | Rol | Función |
| --- | --- | --- |
| `admin1` | ADMIN | Administrar mesas, catálogo y QR |
| `mesero1` | WAITER | Abrir servicios, autorizar y entregar pedidos |
| `cocinero1` | KITCHEN | Preparar pedidos |
| `cajero1` | CASHIER | Registrar pago simulado y cerrar servicios |

La contraseña **no está escrita en el repositorio**: es la que introduces al ejecutar `seed-demo`.

## 7. Iniciar la aplicación

```powershell
python -m flask --app run.py run --no-debugger --no-reload
```

Flask sirve la API en **http://127.0.0.1:5000**. Comprueba el arranque en **http://127.0.0.1:5000/health**.

En otra terminal, desde el repositorio [ConectaResto-MVP-Frontend](https://github.com/ConectaResto/ConectaResto-MVP-Frontend), ejecuta:

```powershell
python -m http.server 8000 --bind 127.0.0.1
```

Abre **http://127.0.0.1:8000/#login**.

Mantén abierta la terminal de Flask mientras pruebas la aplicación. Para detener el servidor, presiona `Ctrl+C`.

## 8. Recorrido rápido de demostración

1. **ADMIN:** entra con `admin1`, comprueba o crea una mesa, categoría y producto; muestra **Ver QR** de la mesa.

   Puedes guardar una imagen del QR y cargarla en el [lector QR online](https://www.codigos-qr.com/lector-qr-online/#result) para consultar el enlace que contiene. El lector es un servicio externo a ConectaResto.

2. **CLIENTE:** abre el enlace del QR en una ventana privada, sin iniciar sesión; agrega productos y confirma un pedido.
3. **WAITER:** entra con `mesero1`, localiza el pedido en Pendientes de autorización, pulsa **Autorizar y enviar a Cocina**.
4. **KITCHEN:** entra con `cocinero1`, pulsa **En cocina** y luego **Listo para servir**.
5. **WAITER:** pulsa **Entregar** cuando esté Listo; el pedido pasa al Historial de pedidos entregados.
6. **CASHIER:** entra con `cajero1`, registra el **pago simulado** y cierra el servicio.
7. **WAITER:** comprueba que la mesa vuelve a **Disponible**.

Al confirmar un pedido público, el backend reutiliza el servicio activo de la mesa. Si no existe y la mesa está Disponible, lo abre automáticamente y la pasa a Ocupada; el mesero no tiene que abrirlo previamente. También puede abrirlo manualmente desde su panel para tomar un pedido interno. Una mesa Cerrada rechaza pedidos; un fallo en la creación revierte la transacción.

Para usar sesiones de roles distintos, cierra sesión o utiliza perfiles de navegador separados. Las pestañas del mismo perfil suelen compartir sesión.

### Mejoras integradas de las vistas (D, E y F)

- **D:** estados legibles en español en administración, mesero, cocina y caja; sin cambiar valores internos ni transiciones.
- **E:** pendientes de autorización, pedidos en curso e historial de entregados, ordenados por ID descendente. Detalles muestra nombres y cantidades en las tres secciones; el historial no tiene acciones operativas.
- **F:** columna MESA con el número visible, resaltada en pendientes/en curso y sin resaltado en historial. Si falta la relación muestra «Mesa desconocida», sin sustituir el número por un ID interno.

## 9. Ejecutar las pruebas automatizadas

Con las dependencias instaladas:

```powershell
python -m pytest -q
```

Para aislar la suite de MySQL, establece `$env:TEST_DATABASE_URL = 'sqlite:///:memory:'` en la terminal de pruebas antes de ejecutarla. La suite general se probó con SQLite durante la auditoría; una prueba de collation requiere MySQL y puede omitirse con SQLite. **No apuntes los tests a una base con datos que quieras conservar**: algunos fixtures crean y eliminan tablas.

## Solución de problemas

| Problema | Qué comprobar |
| --- | --- |
| `ModuleNotFoundError` | Activa `.venv` y reinstala `requirements.txt`. |
| Error de conexión MySQL | Servicio MySQL activo, nombre de base, usuario, contraseña y `DATABASE_URL`. |
| Error por tabla o columna faltante | Ejecuta `db current` y verifica que las migraciones lleguen a `014_add_image_filename_to_products`. |
| El inicio de sesión falla | Comprueba que `seed-demo` terminó y usa la contraseña que elegiste allí. |
| El QR no abre en un teléfono | `127.0.0.1` es el propio dispositivo; para probar con teléfono hace falta una URL accesible desde la red y una configuración adecuada del servidor. |
| El puerto 5000 está ocupado | Detén la otra instancia de Flask antes de volver a iniciarlo. |

**Nota:** ConectaResto-MVP es un proyecto académico. El pago es simulado y los datos de demostración deben mantenerse separados de datos reales.

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
