# QR público y menú por mesa

Responsable: **Portátil Codex 2** (backend QR y menú público).

## Variable de entorno

`PUBLIC_BASE_URL`: URL base pública para construir los enlaces de los QR de mesa.
Es obligatoria: no tiene valor predeterminado (no se asume `localhost`) y no se
deriva del `Host` de la petición. Ejemplo: `https://resto.tudominio.com`.

## Rutas

Comportamiento contrastado con main `91f416c`, posterior a Entrega F.

| Método y ruta | Acceso | Resultado |
|---|---|---|
| `GET /admin/mesas/<mesa_id>/qr.svg` | Solo `ADMIN` | Imagen SVG del QR que apunta a `{PUBLIC_BASE_URL}/public/mesas/<public_token>/menu`. Reutiliza `Mesa.public_token`. Devuelve `500` si `PUBLIC_BASE_URL` no está configurada y `404` si la mesa no existe. |
| `GET /public/mesas/<token>` | Público, sin login | JSON con número visible y enlaces al catálogo; no abre servicios. |
| `POST /public/mesas/<token>/pedidos` | Público con CSRF | Recibe `items` con `producto_id` y `cantidad`; devuelve 201 con ID y estado del pedido. Reutiliza servicio activo o abre uno para una mesa Disponible. |
| `GET /public/mesas/<token>/menu` | Público, sin login | Menú por categorías, productos, carrito y confirmación de pedidos. Valida el token (64 caracteres hexadecimales minúsculos); `404` si es inválido o inexistente. No imprime el token ni datos internos en el HTML. |

## Notas de implementación

- El QR se genera localmente con `segno` (dependencia añadida a `requirements.txt`); no se usan servicios externos.
- No se habilita el depurador de Flask para acceso LAN.
- La entrega inicial de QR reutilizó el modelo `Mesa` sin modificarlo. La apertura automática actual se describe abajo; no debe confundirse con el alcance histórico de aquella entrega.
- Pruebas: `tests/test_qr_publico.py` (permisos, token inválido, configuración de URL y contenido del QR).

## Interfaz pública del cliente

La entrega original de Portátil Codex 2 completó `app/templates/public/menu.html` con `public_menu.js` y `public_menu.css`, sin modificar entonces mesero/cocina. La coordinación vigente se conserva en `COORDINACION_EQUIPOS_IA.md`.

El QR existente abre directamente la interfaz móvil. Esta consulta el
catálogo público y obtiene CSRF mediante `/auth/csrf` cuando el cliente
confirma el envío. El formulario usa `action="pedidos"`, relativo al menú,
para llegar al POST existente sin imprimir el token en el documento.

La página inicial no crea sesión ni solicita login. Las cookies anónimas de
CSRF se obtienen al enviar. Mesas cerradas conservan lectura del menú; el
POST rechaza mesas cerradas y los demás errores del dominio. Reutiliza el servicio ACTIVO si existe; si no, el backend abre uno para una mesa DISPONIBLE, sin usuario abridor, y crea el pedido en la misma transacción. Una mesa OCUPADA sin servicio activo se rechaza con 409. Un fallo revierte la apertura. Los GET no crean servicios.

El mesero autoriza el pedido PENDIENTE/NO_ENVIADO y después lo envía a cocina. Consultar Detalles o leer el menú no autoriza ni modifica el pedido. El token público permanece estable entre servicios. Token inválido: 404; cuerpo/CSRF inválido: 400. No hay consulta pública de pedidos ajenos.

`tests/test_public_menu_ui.py` valida el HTML y los recursos; además usa un
navegador Chromium ya instalado y Node con WebSocket nativo para comprobar
el JavaScript real contra Flask/SQLite. No instala paquetes. Esa prueba se
omite si faltan esas herramientas; el resto se ejecuta con pytest normalmente.
`PUBLIC_MENU_TEST_BROWSER` permite indicar la ruta de un Chromium instalado.
En un entorno restringido es necesario permitir sockets de loopback para
esa prueba. Los perfiles y capturas usan un temporal aislado de pytest.
