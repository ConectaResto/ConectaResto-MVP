# QR público y menú por mesa

Responsable: **Portátil Codex 2** (backend QR y menú público).

## Variable de entorno

`PUBLIC_BASE_URL`: URL base pública para construir los enlaces de los QR de mesa.
Es obligatoria: no tiene valor predeterminado (no se asume `localhost`) y no se
deriva del `Host` de la petición. Ejemplo: `https://resto.tudominio.com`.

## Rutas

| Método y ruta | Acceso | Resultado |
|---|---|---|
| `GET /admin/mesas/<mesa_id>/qr.svg` | Solo `ADMIN` | Imagen SVG del QR que apunta a `{PUBLIC_BASE_URL}/public/mesas/<public_token>/menu`. Reutiliza `Mesa.public_token`. Devuelve `500` si `PUBLIC_BASE_URL` no está configurada y `404` si la mesa no existe. |
| `GET /public/mesas/<token>/menu` | Público, sin login | Plantilla HTML mínima del menú de la mesa (Kilo 2 la completa). Valida el token (64 caracteres hexadecimales minúsculos); `404` si es inválido o inexistente. No expone el token ni datos internos. |

## Notas de implementación

- El QR se genera localmente con `segno` (dependencia añadida a `requirements.txt`); no se usan servicios externos.
- No se habilita el depurador de Flask para acceso LAN.
- No se modifica el modelo `Mesa`, las migraciones, la lógica de pedidos ni el frontend integrado.
- Pruebas: `tests/test_qr_publico.py` (permisos, token inválido, configuración de URL y contenido del QR).
