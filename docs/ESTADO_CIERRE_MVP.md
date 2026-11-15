# Estado del cierre del MVP

## Bloque 1 — Esquema MySQL 8

Rama local `audit/mvp-entrega`, basada en `origin/main` en `d7035a7`. El árbol de trabajo contiene cambios sin commit. Las correcciones previas de QR, CASHIER y KITCHEN siguen en los mismos archivos y se conservaron íntegramente.

| Archivos | Estado |
|---|---|
| `migrations/versions/012_add_detalle_timestamps.py` | Nueva migración del bloque 1 |
| `docs/ESTADO_CIERRE_MVP.md` | Nuevo registro de continuidad |
| `app/mesas/routes.py`, `tests/test_qr_publico.py`, `app/static/js/cashier.js`, `app/templates/kitchen/pedidos.html` | Cambios previos de la auditoría |

### Diagnóstico y corrección

La migración `010` creó `detalles_pedido` sin `created_at` ni `updated_at`. `DetallePedido` hereda ambos campos de `BaseModel`. En una base MySQL migrada hasta `011`, `POST /servicios` devolvía HTTP 500 con el error MySQL 1054 al calcular el total para la respuesta, incluso con cero líneas de pedido.

`abrir_servicio()` confirma juntas la inserción del servicio y la transición de la mesa a `OCUPADA`. Después, `serializar_servicio()` consulta los detalles para calcular el total. La consulta fallaba sobre el esquema antiguo con la transacción de apertura ya confirmada. La mesa ocupada y su servicio activo permanecieron coherentes. Reintentar la apertura devolvió HTTP 409.

`012_add_detalle_timestamps` añade ambas columnas como `DATETIME`, rellena las líneas existentes con `pedidos.created_at` en ambos campos y aplica `NOT NULL`. La fecha del pedido es la referencia histórica disponible para las líneas, que se crean junto con él. El ORM sigue proporcionando los valores de las líneas nuevas y actualizando `updated_at`. El upgrade conserva los identificadores, importes, cantidades y relaciones. Las revisiones `001` a `011` se conservaron.

### Verificación ejecutada

MySQL Community **8.0.46**, en una instancia de auditoría dedicada en loopback y con bases de prueba independientes. Los esquemas usados para verificar el flujo se crearon con Flask-Migrate.

- `cr_block1_verify_fresh`. `flask --app run.py db upgrade` aplicó las revisiones `001` a `012` y `flask --app run.py db current` confirmó `012_add_detalle_timestamps (head)`. Por HTTP se comprobó apertura 201, duplicado 409, pedido interno 201, total correcto, preparación, entrega, pago y cierre. La mesa volvió a `DISPONIBLE`. SQL confirmó las fechas en la nueva línea.
- `cr_block1_verify_legacy`. Se aplicó `flask --app run.py db upgrade 011_create_pagos`, se reprodujo el 500 y se insertaron dos líneas de prueba vinculadas a pedidos con fechas distintas. Tras ejecutar `flask --app run.py db upgrade`, se conservaron ambos registros, IDs, relaciones, cantidades y precios. Las dos fechas de cada línea coincidieron con la creación de su pedido. El servicio que ya estaba activo recibió un nuevo pedido público con HTTP 201.
- La inspección con SQLAlchemy confirmó `DATETIME NOT NULL` sin valores por defecto del servidor para las dos columnas nuevas y verificó el índice único `uq_servicios_una_activa_por_mesa`.
- En el esquema `012`, con fallos inyectados antes y después de confirmar la apertura, se verificaron dos resultados. Antes del commit, el rollback dejó la mesa `DISPONIBLE` y cero servicios activos. Después del commit, un fallo forzado de serialización devolvió 500 con un solo servicio `ACTIVO` y la mesa `OCUPADA`. La consulta posterior devolvió 200, el reintento 409 y el cierre normal liberó la mesa.
- `pytest -q tests/test_categories.py::test_create_category_duplicate_name_accent_case_insensitive` pasó en `cr_block1_collation`, un esquema separado, porque esa prueba gestiona sus propias tablas.
- La suite completa `pytest -q -p audit_browser_plugin -rs --basetemp ../pytest-block1` dio **582 aprobadas y 1 omitida** con SQLite. La omitida fue la de collation, aprobada por separado en MySQL. El lanzador local añadió `--no-sandbox` a Chrome para habilitar CDP en este entorno. Pytest emitió una advertencia de escritura de caché.
- `pytest -q -p no:cacheprovider --basetemp ../pytest-block1-related tests/test_migrations.py tests/test_servicios.py tests/test_pedidos.py tests/test_caja.py` dio **165 aprobadas**. La primera ejecución de este subconjunto dio 159 aprobadas y seis errores de preparación por permisos en el temporal predeterminado de Windows. Los seis casos pasaron al usar un temporal en el área de trabajo.
- `git diff --check` pasó y la comparación del diff anterior al bloque confirmó que los cuatro cambios previos se conservaron byte por byte.

### Cómo repetir la comprobación

1. En una instancia MySQL 8 de pruebas, prepara una base vacía con `utf8mb4_0900_ai_ci`. Configura `DATABASE_URL` hacia esa base y `FLASK_ENV=development`. Usa un entorno con las dependencias que declara el repositorio.
2. Ejecuta `python -m flask --app run.py db upgrade`, `python -m flask --app run.py db current` y `python -m flask --app run.py seed-demo`. El comando de siembra solicita la contraseña de demostración.
3. Comprueba el esquema con `SHOW COLUMNS FROM detalles_pedido;`. Las dos fechas deben figurar como `datetime` con `Null = NO`.
4. Inicia Flask con `python -m flask --app run.py run --no-debugger`. Como WAITER, abre una mesa disponible, crea un pedido con un producto disponible y comprueba el total. El flujo usa `POST /servicios` y `POST /servicios/<id>/pedidos`. Para verificar la liberación de mesa, pasa el pedido por cocina, entrégalo y completa el pago y cierre en caja.
5. Para probar un upgrade con datos, usa una segunda base aislada hasta `011_create_pagos`. Inserta datos de prueba por SQL en `servicios`, `pedidos` y `detalles_pedido` con sus referencias válidas y registra la salida antes del upgrade. Tras subir a `012`, compara los IDs, relaciones, cantidades y precios de esas líneas y comprueba que sus fechas coinciden con `pedidos.created_at`.
6. Ejecuta `git diff --check` y `python -m pytest -q` con `TEST_DATABASE_URL=sqlite:///:memory:` para la suite general. Si el entorno de Windows restringe el temporal predeterminado de Pytest, pasa `--basetemp` con un directorio nuevo dentro del área de trabajo. La prueba específica de collation se puede repetir apuntando `TEST_DATABASE_URL` a otra base MySQL vacía y desechable. Los fixtures de Pytest crean y eliminan tablas en la base que reciben.

### Riesgos y siguiente bloque

- El caso original del esquema quedó resuelto. La ruta aún puede responder 500 ante otro fallo de serialización posterior al commit, como mostró la prueba de fallo inyectado. Ante una respuesta ambigua, consultar si el servicio quedó activo antes de reintentar. Cambiar la secuencia de la respuesta y la transacción requiere autorización para lógica de backend.
- En `products.is_available`, el esquema migrado admite `NULL` y el ORM declara `nullable=False`. La diferencia proviene del renombrado de la revisión `004` y no impidió los flujos comprobados. La columna generada `servicios.estado_activo` es intencional y sostiene la restricción de un solo servicio activo por mesa. Los booleanos se representan como `TINYINT` en MySQL.
- MySQL aplica DDL sin una transacción que abarque toda la migración. Si se interrumpe el upgrade, inspeccionar `flask db current` y las columnas antes de reintentar. Un downgrade de `012` quitaría las dos fechas. No se ejecutó.
- Siguiente bloque recomendado. Resolver la reactivación de productos desde ADMIN con una consulta administrativa autorizada. Revisar si hay valores `NULL` de disponibilidad en una copia de prueba antes de proponer una migración posterior.

## Bloque 2 — Disponibilidad de productos en ADMIN

El panel cargaba productos mediante `GET /products`, la misma consulta que usa el menú QR. En `app/catalog/service.py`, `list_products()` filtra los productos activos de categorías activas por `is_available = true`. Por eso la fila desaparecía al guardar la disponibilidad en falso, aunque el `PATCH` existente permitía reactivarla si se conocía el ID.

El panel carga ahora `GET /admin/products`, protegido con `roles_required("ADMIN")`. La ruta reutiliza `list_products(include_unavailable=True)` y conserva los filtros de producto y categoría activos. El formulario continúa usando `POST /products` y `PATCH /products/<id>`. El menú QR conserva su consulta pública y su filtro de disponibilidad.

| Archivo modificado en el bloque 2 | Cambio |
|---|---|
| `app/catalog/routes.py` y `app/catalog/service.py` | Consulta administrativa con los dos estados de disponibilidad |
| `app/static/js/admin.js` y `app/templates/admin.html` | Listado administrativo y texto de disponibilidad |
| `app/catalog/CONTRACT.md` | Documentación de la consulta y sus permisos |
| `tests/test_admin_frontend.py` | Regresión del ciclo de disponibilidad, permisos y conexión con JavaScript |
| `docs/ESTADO_CIERRE_MVP.md` | Registro de continuidad |

### Verificación ejecutada

- Chrome con MySQL **8.0.46** y el esquema aislado `cr_block2_admin_browser` migrado mediante `flask --app run.py db upgrade` hasta `012`. Desde ADMIN se creó un producto disponible, se marcó como no disponible y se volvió a habilitar sobre la misma fila. Se recargó ADMIN en ambos estados y se abrió el menú QR sin sesión para confirmar que lo ocultaba y volvía a mostrar. WAITER recibió 403 en la consulta administrativa y al intentar modificar la disponibilidad con CSRF válido.
- `pytest -q -p no:cacheprovider --basetemp ../pytest-block2-admin tests/test_admin_frontend.py tests/test_public_menu.py` dio **41 aprobadas**. Incluye las comprobaciones HTTP de acceso anónimo, WAITER, KITCHEN y CASHIER y las interacciones de ADMIN ejecutadas en Node.
- La suite completa `pytest -q -p audit_browser_plugin -p no:cacheprovider -rs --basetemp ../pytest-block2-full` dio **587 aprobadas y 1 omitida** con SQLite. Se usó el lanzador local de Chrome con `--no-sandbox` para CDP. La única omisión fue la prueba de collation ejecutada por separado en MySQL.
- `pytest -q -p no:cacheprovider tests/test_categories.py::test_create_category_duplicate_name_accent_case_insensitive` pasó en la base MySQL aislada `cr_block2_collation`.
- `node --check app/static/js/admin.js` y `git diff --check` pasaron.

### Git y pendientes para la entrega

La rama sigue en `audit/mvp-entrega` sobre `d7035a7`, con cambios locales sin commit. Se preservaron los cambios previos de QR, CASHIER y KITCHEN y la migración `012`. Los modelos, las migraciones y las dependencias quedan fuera del diff de este bloque.

El proyecto queda preparado para repetir la demostración integral en un esquema MySQL de prueba migrado hasta `012`, con QR, pedido, preparación, entrega, pago y liberación de mesa. Queda por realizar esa verificación final y comprobar el escaneo del QR con un teléfono si forma parte de la demostración.

- Sigue registrado el posible fallo de respuesta posterior al commit en `POST /servicios`, reproducido mediante un fallo inyectado de serialización en el bloque 1.
- Sigue registrado que MySQL permite `NULL` en `products.is_available` y el ORM declara `nullable=False`. El ciclo de disponibilidad comprobado persistió los valores booleanos esperados.

## Bloque 3 — Verificación integral definitiva

**Veredicto: LISTO para cerrar el desarrollo del MVP académico y preparar la entrega.** El recorrido de mesa, pedido QR, cocina y caja pasó en Chrome con Flask y MySQL Community **8.0.46**.

### Entorno y resultado por módulo

Se creó la base aislada `cr_block3_verified` vacía y se aplicó `python -m flask --app run.py db upgrade`. Flask-Migrate confirmó `012_add_detalle_timestamps (head)`. Se ejecutaron `seed-demo` y el arranque de Flask desde la CLI. `GET /health` devolvió HTTP 200. SQL confirmó `DATETIME NOT NULL` para ambas fechas de `detalles_pedido` y el índice único `uq_servicios_una_activa_por_mesa`.

| Módulo | Resultado observado en Chrome |
|---|---|
| ADMIN | Inicio de sesión, alta de la mesa 123, categoría, producto y usuario. El QR SVG se renderizó y su patrón se decodificó para obtener la URL de esa mesa. La fila del producto siguió visible al quitarle disponibilidad y permitió reactivarlo. |
| Cliente público | El producto desapareció del menú al quitarle disponibilidad y reapareció al reactivarlo. Desde la URL decodificada, sin sesión, se envió un pedido de dos unidades y se obtuvo confirmación con estado `PENDIENTE`. |
| WAITER | Abrió el servicio de la mesa 123, recibió y autorizó el pedido, lo envió a cocina y al final lo marcó `ENTREGADO`. Pudo reabrir la mesa después del primer cierre. |
| KITCHEN | Mostró el nombre del producto y la cantidad 2. Se pasó de `RECIBIDO` a `EN_COCINA` y luego a `LISTO_PARA_SERVIR`. |
| CASHIER | Mostró el total 24.70, registró ese importe como pago simulado, conservó el estado al recargar y cerró el servicio. El segundo servicio, vacío, se cerró sin pago. WAITER confirmó la mesa `DISPONIBLE`. |

SQL confirmó el servicio 1 `CERRADO`, con el pedido 1 de origen `PUBLICO` y estado `ENTREGADO`, dos unidades a 12.35, ambas fechas pobladas y pago de 24.70. El servicio 2 quedó `CERRADO` sin pedido ni pago. La mesa 123 quedó `DISPONIBLE`. La decodificación se hizo sobre la imagen mostrada en Chrome. El escaneo con un teléfono físico quedó sin comprobar.

### Contratos y pruebas

| Pantalla | Rutas contrastadas con Flask y los contratos del módulo |
|---|---|
| ADMIN | `/admin/mesas` y `/admin/mesas/<id>/qr.svg`, `/categories`, `GET /admin/products`, `POST /products`, `PATCH /products/<id>`, `/users` |
| Cliente | `GET /public/mesas/<token>/menu`, `GET /categories`, `GET /products`, `GET /auth/csrf`, `POST /public/mesas/<token>/pedidos` |
| WAITER y KITCHEN | `GET /mesas`, `POST /servicios`, `GET /servicios?estado=ACTIVO`, `GET /pedidos`, acciones `autorizar`, `enviar-cocina` y `entregar`, y `PATCH /pedidos/<id>/preparacion` |
| CASHIER | `GET /servicios?estado=ACTIVO`, `GET /servicios/<id>`, `POST /servicios/<id>/pago-simulado` y `POST /servicios/<id>/cerrar` |

- `pytest -q -p audit_browser_plugin -p no:cacheprovider -rs --basetemp ../pytest-block3-full`, con SQLite, dio **587 aprobadas y 1 omitida**. El lanzador local añadió `--no-sandbox` a Chrome para las pruebas CDP en este entorno.
- La prueba omitida de collation, `tests/test_categories.py::test_create_category_duplicate_name_accent_case_insensitive`, se ejecutó por separado en MySQL con **1 aprobada**. Se usó una segunda base aislada y vacía para sus fixtures.
- `pytest -q -p no:cacheprovider --basetemp ../pytest-block3-migrations tests/test_migrations.py tests/test_seed_demo.py tests/test_qr_publico.py tests/test_admin_frontend.py` dio **59 aprobadas**.
- `node --check` pasó en cuatro archivos JavaScript y cuatro bloques de las plantillas. `git diff --check` pasó.

### Demostración con MySQL

Prepara una base MySQL 8 vacía con `utf8mb4_0900_ai_ci` y las dependencias de `requirements.txt`. Configura localmente `DATABASE_URL` hacia esa base, una `SECRET_KEY` para la sesión, `FLASK_ENV=development` y `PUBLIC_BASE_URL=http://127.0.0.1:5000` para la demostración en el mismo equipo. En el repositorio, ejecuta:

```sh
python -m flask --app run.py db upgrade
python -m flask --app run.py db current
python -m flask --app run.py seed-demo
python -m flask --app run.py run --no-debugger --no-reload
```

En `seed-demo`, elige una contraseña de demostración y confirma el nombre de la base. El comando prepara `admin1` (ADMIN), `mesero1` (WAITER), `cocinero1` (KITCHEN), `cajero1` (CASHIER), mesas y catálogo de prueba. Abre `/login` para los roles internos.

1. En ADMIN, muestra **Ver QR** para una mesa disponible. Si la demostración es en el mismo equipo, puedes abrir la URL del QR en una ventana privada. Como alternativa local, obtén el `public_token` de la mesa desde `/admin/mesas` con sesión ADMIN y abre `/public/mesas/<token>/menu` en dicha ventana.
2. Con WAITER, abre el servicio de esa mesa. En la ventana pública elige productos y confirma. Vuelve a WAITER, recarga pedidos, autoriza y envía a cocina.
3. Con KITCHEN, abre la lista, marca **En cocina** y luego **Listo para servir**. Vuelve a WAITER, recarga y marca **Entregar**.
4. En CASHIER, selecciona el servicio, verifica el importe, registra el pago simulado y cierra. Regresa a WAITER y verifica `DISPONIBLE`. Para demostrar el caso vacío, vuelve a abrir la mesa y cierra ese servicio desde caja sin registrar pago.

### Problemas y estado de Git

- **Bloqueantes:** ninguno en el recorrido académico comprobado.
- **No bloqueantes:** un fallo de serialización posterior al commit en `POST /servicios` puede devolver 500 aunque la apertura haya quedado registrada. Si ocurre, consulta los servicios activos antes de reintentar. MySQL permite `NULL` en `products.is_available`; los cambios realizados desde ADMIN guardaron valores booleanos. Caja muestra `mesa_id` y se puede identificar el cobro por el número de servicio. El escaneo físico puede comprobarse en el equipo de la demostración si se usará un teléfono.
- **Fuera del alcance:** pagos reales, inventario y despliegue comercial.

Rama `audit/mvp-entrega` en `d7035a7`. El bloque 3 solo añadió este registro. El diff previo y la migración `012` conservaron su contenido. Archivos pendientes de integrar:

- Catálogo y ADMIN: `app/catalog/CONTRACT.md`, `app/catalog/routes.py`, `app/catalog/service.py`, `app/static/js/admin.js`, `app/templates/admin.html` y `tests/test_admin_frontend.py`.
- QR, caja y cocina: `app/mesas/routes.py`, `app/static/js/cashier.js`, `app/templates/kitchen/pedidos.html` y `tests/test_qr_publico.py`.
- Esquema y continuidad: `migrations/versions/012_add_detalle_timestamps.py` y `docs/ESTADO_CIERRE_MVP.md`.

Con autorización, revisar los doce archivos, hacer commit en `audit/mvp-entrega`, publicar esa rama y abrir un PR hacia `main` con las evidencias de MySQL y Chrome. El merge queda sujeto a la revisión del PR.
