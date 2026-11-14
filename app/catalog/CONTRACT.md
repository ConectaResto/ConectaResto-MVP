# Contrato de API — Administración de Categorías (B-01.1)

Este documento describe el contrato de API del módulo de categorías. Vive
dentro del módulo `app/catalog` y no debe editarse en documentos generales
ni de coordinación.

## Estado del registro de rutas

El blueprint `categories_bp` (`app/catalog/routes.py`) está **sin registrar**
en `app/__init__.py`. No se expondrán endpoints administrativos sin protección
hasta que el mecanismo de autorización de A-02 esté integrado.

## Endpoints

### GET /categories
Lista categorías activas (consulta pública).
Respuesta: `{"success": true, "data": [{...}, ...]}`

### POST /categories
Crea una categoría nueva (siempre activa).
Entrada: `{"name": "string", "description": "string|null"}`
Respuesta 201: `{"success": true, "data": {...}, "message": "Categoría creada"}`
Errores: 409 si el nombre ya existe (insensible a mayúsculas/minúsculas).

### GET /categories/<int:id>
Obtiene una categoría activa por id.
Respuesta: `{"success": true, "data": {...}}`
Errores: 404 si no existe o está inactiva.

### PATCH /categories/<int:id>
Actualiza nombre y/o descripción de una categoría activa.
Entrada: `{"name": "string|null", "description": "string|null"}`
Respuesta: `{"success": true, "data": {...}}`
Errores: 404 si no existe o está inactiva; 409 si el nombre ya existe.

### DELETE /categories/<int:id>
Desactivación lógica: establece `is_active = false`.
Respuesta: `{"success": true, "message": "Categoría desactivada"}`
Errores: 404 si no existe o ya está inactiva.

## Modelo

Tabla: `categories`
Columnas: `id` (PK, int), `name` (string, no nulo), `description` (string,
nullable), `is_active` (boolean, default true), `created_at`, `updated_at`.

## Reglas de negocio

- Las categorías nuevas se crean activas (`is_active = true`).
- `name` es único sin distinguir mayúsculas/minúsculas.
- `DELETE` es desactivación lógica (no borrado físico).
- Las consultas públicas solo muestran categorías activas.
- No se implementa autenticación ni protección de rutas en este lote.
- La regla "no desactivar una categoría con productos activos" se completará
  en B-01.2 cuando exista el modelo de Producto.

## Formato de respuesta

Todos los endpoints usan `success_response` y `error_response` de
`app/common/responses.py` con el formato:
- Éxito: `{"success": true, "data": ..., "message": ...}`
- Error: `{"success": false, "error": ..., "errors": ...}`
