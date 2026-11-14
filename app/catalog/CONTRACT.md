# Contrato de API — Administración de Categorías y Productos (B-01)

Este documento describe el contrato de API del módulo de categorías y productos.
Vive dentro del módulo `app/catalog` y no debe editarse en documentos generales
ni de coordinación.

## Estado del registro de rutas

Los blueprints `categories_bp` y `products_bp` (`app/catalog/routes.py`) están
registrados en `app/__init__.py`. Los endpoints administrativos (POST, PATCH,
DELETE) estan protegidos con `roles_required("ADMIN")` del modulo A-02.
Los endpoints GET son publicos y no requieren autenticacion.

La proteccion CSRF global (`protect_csrf` de `app/auth/csrf.py`) se aplica a
todas las peticiones mutantes mediante `before_request` en la factory.

## Endpoints

### GET /categories
Lista categorias activas (consulta publica).
Respuesta: `{"success": true, "data": [{...}, ...]}`

### POST /categories
Crea una categoria nueva (siempre activa). Requiere rol ADMIN.
Entrada: `{"name": "string", "description": "string|null"}`
Respuesta 201: `{"success": true, "data": {...}, "message": "Categoria creada"}`
Errores: 401 sin autenticacion, 403 sin rol ADMIN, 409 si el nombre ya existe
(insensible a mayusculas/minusculas).

### GET /categories/<int:id>
Obtiene una categoria activa por id.
Respuesta: `{"success": true, "data": {...}}`
Errores: 404 si no existe o esta inactiva.

### PATCH /categories/<int:id>
Actualiza nombre y/o descripcion de una categoria activa. Requiere rol ADMIN.
Entrada: `{"name": "string|null", "description": "string|null"}`
Respuesta: `{"success": true, "data": {...}}`
Errores: 401 sin autenticacion, 403 sin rol ADMIN, 404 si no existe o esta
inactiva, 409 si el nombre ya existe.

### DELETE /categories/<int:id>
Desactivacion logica: establece `is_active = false`. Requiere rol ADMIN.
Bloqueado (409) si la categoria tiene al menos un producto con `is_active=True`.
Respuesta: `{"success": true, "message": "Categoria desactivada"}`
Errores: 401 sin autenticacion, 403 sin rol ADMIN, 404 si no existe o ya
esta inactiva, 409 si tiene productos activos asociados.

### GET /products
Lista productos activos, disponibles y asociados a categorias activas
(consulta publica). Filtro opcional `?categoria_id=<id>`.
Respuesta: `{"success": true, "data": [{...}, ...]}`

### POST /products
Crea un nuevo producto activo y disponible. Requiere rol ADMIN.
Entrada: `{"name": "string", "description": "string|null", "price": "string",
"categoria_id": "int", "is_available": "boolean|null"}`
Respuesta 201: `{"success": true, "data": {...}, "message": "Producto creado"}`
Errores: 401 sin autenticacion, 403 sin rol ADMIN, 404 si la categoria no
existe o esta inactiva, 409 si el nombre ya existe en la categoria o el precio
es invalido.

### GET /products/<int:id>
Obtiene un producto activo, disponible y con categoria activa por id.
Respuesta: `{"success": true, "data": {...}}`
Errores: 404 si no existe, no esta disponible o su categoria esta inactiva.

### PATCH /products/<int:id>
Actualiza campos de un producto. Requiere rol ADMIN.
Campos actualizables: name, description, price, categoria_id, is_active,
is_available. Un producto inactivo (is_active=False) puede actualizarse
mediante PATCH para cambiar is_available de False a True.
Entrada: `{"name": "string|null", "description": "string|null", "price":
"string|null", "categoria_id": "int|null", "is_active": "boolean|null",
"is_available": "boolean|null"}`
Respuesta: `{"success": true, "data": {...}}`
Errores: 401 sin autenticacion, 403 sin rol ADMIN, 404 si no existe, 409 si
el nombre ya existe en la categoria o el precio es invalido.

### DELETE /products/<int:id>
Desactivacion logica: establece `is_active = false`. Requiere rol ADMIN.
No es una desactivacion temporal; usa is_available para eso.
Respuesta: `{"success": true, "message": "Producto desactivado"}`
Errores: 401 sin autenticacion, 403 sin rol ADMIN, 404 si no existe o ya
esta inactivo.

## Modelo

Tabla: `categories`
Columnas: `id` (PK, int), `name` (string, no nulo, unico sin distinguir
mayusculas/minusculas ni acentos con collation utf8mb4_0900_ai_ci),
`description` (string, nullable), `is_active` (boolean, default true),
`created_at`, `updated_at`.

Tabla: `products`
Columnas: `id` (PK, int), `name` (string, no nulo), `description` (string,
nullable), `price` (numeric 10,2, no nulo), `categoria_id` (int, no nulo,
FK a categories.id), `is_active` (boolean, default true),
`is_available` (boolean, default true), `created_at`, `updated_at`.

## Reglas de negocio

- Las categorias nuevas se crean activas (`is_active = true`).
- Los productos nuevos se crean activos y disponibles (`is_active = true`,
  `is_available = true`).
- `name` de categoria es unico sin distinguir mayusculas/minusculas ni acentos.
- `name` de producto es unico dentro de su categoria, sin distinguir
  mayusculas/minusculas.
- `DELETE` es desactivacion logica (no borrado fisico) tanto para
  categorias como para productos.
- Las consultas públicas solo muestran categorias activas, y productos
  activos (`is_active=True`), disponibles (`is_available=True`) y asociados
  a categorias activas.
- No se puede desactivar una categoria que tenga al menos un producto con
  `is_active=True`.
- `is_active` representa desactivacion logica; `is_available` representa
  disponibilidad temporal. `PATCH` puede cambiar `is_available` pero no
  reactiva `is_active` (eso solo se hace con `DELETE` revertido o actualizacion
  administrativa directa).
- Los precios se manejan internamente como `Decimal` y se serializan como
  cadena JSON (ej. `"25.50"`) para preservar precision.
- `NaN`, `Infinity` y `-Infinity` no son precios validos.
- No se implementa autenticacion propia; se reutilizan los componentes de A-02
  (`login_required`, `roles_required`).

## Formato de respuesta

Todos los endpoints usan `success_response` y `error_response` de
`app/common/responses.py` con el formato:
- Exito: `{"success": true, "data": ..., "message": ...}`
- Error: `{"success": false, "error": ..., "errors": ...}`
