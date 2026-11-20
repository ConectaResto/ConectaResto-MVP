---
name: conectaresto-ui
type: design
scope: proyecto
stack: ["HTML", "CSS", "JavaScript Vanilla", "Bootstrap 5 (CDN)"]
estado: borrador
autor: Kilo
dependencias: []
modifica_backend: false
modifica_base_datos: false
---

# Skill: conectaresto-ui

## Propósito

Guiar futuras mejoras visuales del MVP de ConectaResto mediante una estética clara, sencilla, moderna y minimalista, sin apariencia empresarial excesiva. Esta skill define reglas de diseño, criterios de componente y el proceso de integración de Bootstrap 5 mediante CDN. No modifica lógica de negocio, backend, modelos ni base de datos.

## Fuente de verdad y reglas vinculantes

Esta skill opera bajo las instrucciones permanentes del proyecto. En caso de conflicto, este documento prevalece. Reglas clave de la habilidad aplicables a esta skill:

- Stack obligatorio: HTML, CSS, JavaScript Vanilla (frontend). No se agregan React, Vue, Angular ni Tailwind.
- Reutilizar primero los componentes y estilos existentes (`app/static/css/style.css`, `app/static/css/public_menu.css`, plantillas en `app/templates/`). Evitar duplicados innecesarios.
- No modificar código fuente, documentación ni dependencias declaradas durante tareas exclusivamente visuales sin autorización explícita.
- No crear archivos `.env`, no conectar ni modificar MySQL, no ejecutar migraciones.
- No hacer commit, push ni merge sin autorización del coordinador.

## Estética objetivo

- **Clara y minimalista:** interfaz limpia, sin elementos decorativos superfluos.
- **Sencilla, bonita y moderna:** uso moderado de color, sombras suaves y bordes redondeados.
- **Espaciados uniformes:** sistema de espaciado coherente en toda la aplicación.
- **Botones y formularios consistentes:** mismos estilos para acciones idénticas en todos los roles.
- **Tablas legibles:** filas bien separadas, encabezados distinguibles, estados con colores sutiles.
- **Sin apariencia empresarial excesiva:** evitar gradientes complejos, sombras pesadas, iconografía recargada o paneles estilo dashboard corporativo.
- **Adaptable a computadores y celulares:** diseño responsivo que funcione en desktop y móvil sin romper el layout.

## Criterios de diseño

### Colores
Colores de marca definidos en `app/static/css/style.css`:
- Primario: `#2c3e50` (encabezados, botones principales).
- Peligro / salir: `#e74c3c` (botones de cierre de sesión, acciones destructivas).
- Fondo: `#f5f5f5` (fondo general de aplicación).
- Superficie: `#ffffff` (tarjetas, formularios, tablas).
- Texto principal: `#333`; texto secundario: `#666`; etiquetas: `#555`.

Cuando se autorice Bootstrap 5, se respetarán estos colores como base y se sobreescribirán las variables de Bootstrap (`--bs-primary`, `--bs-danger`, etc.) en lugar de reemplazarlas por completo.

### Tipografía
- Fuente del sistema: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif`.
- Jerarquía clara: `h1` para títulos de página, `h2` para secciones, `h3` para subtítulos de tarjetas.
- Tamaños de cuerpo legibles (mínimo 1rem en formularios y tablas).
- Interlineado cómodo (1.5 a 1.6).

### Espaciado
- Sistema basado en múltiplos de 8px (8, 16, 24, 32, 40, 48).
- Contenedor principal con `max-width: 1200px` y padding horizontal `20px`.
- Margen inferior uniforme entre secciones (`24px` o `28px`).
- Padding interno de tarjetas y paneles: `24px`.
- Espaciado entre elementos de formulario: `16px` entre campos.

### Botones
- Clase base `.btn` (relleno, borde redondeado 6px, padding `10px 18px`, fuente `0.95rem`).
- `.btn-primary`: fondo `#2c3e50`, texto blanco, hover `#1a252f`.
- `.btn` secundario: fondo transparente o gris claro, borde sutil.
- Botones deshabilitados: opacidad 0.6, cursor `not-allowed`.
- Ancho completo (`width: 100%`) en formularios móviles y tarjetas de acción.

### Formularios
- Campo `.field` con `margin-bottom: 16px`.
- Etiqueta de bloque, `font-size: 0.95rem`, color `#555`, `margin-bottom: 6px`.
- Input/select: ancho completo, padding `10px 12px`, borde `1px solid #ddd`, borde-radius 6px, fuente `1rem`.
- Focus: borde-color `#2c3e50`, sin outline agresivo.
- Checkbox y radio con alineación consistente.
- Mensajes de error con clase `.flash.error`.

### Tablas
- Ancho completo, `border-collapse: collapse`, fondo blanco, borde-radius 8px, sombra suave.
- Encabezado `th`: fondo `#f8f9fa`, texto `#2c3e50`, mayúsculas pequeñas, padding 12px.
- Celdas `td`: padding 12px, borde inferior `1px solid #eee`, fuente `0.95rem`.
- Filas:hover: fondo `#f8f9fa`.
- Última fila sin borde inferior.
- Estados con badges sutiles (`.badge`, padding `4px 10px`, borde-radius 12px, fuente `0.75rem`).

### Tarjetas y paneles
- `.card`: fondo blanco, borde-radius 8px, sombra `0 2px 8px rgba(0,0,0,0.1)`, padding 24px, flex columna.
- `.panel-header`: título `h1` (`1.75rem`, color `#2c3e50`), subtítulo color `#666`.
- `.cards-grid`: grid `repeat(auto-fill, minmax(260px, 1fr))`, gap 20px.

### Flash messages
- `.flash`: padding `10px 14px`, borde-radius 6px, fuente `0.95rem`.
- `.flash.error`: fondo claro rojo, texto rojo oscuro, borde rojo suave.

### Diseño adaptable (responsive)
- Navbar colapsable en móvil con botón de menú (hamburguesa).
- Grid de tarjetas pasa a una columna en pantallas pequeñas.
- Formularios y botones en ancho completo en móvil.
- Breakpoints alineados con Bootstrap 5 cuando se integre (576px, 768px, 992px, 1200px).
- Comprobar en navegador real en desktop y móvil (mínimo 375px de ancho) antes de considerar una pantalla terminada.

## Integración de Bootstrap 5

Bootstrap 5 se permite **únicamente mediante CDN**, nunca como dependencia de npm ni de `requirements.txt`. Se agrega en `app/templates/base.html`:

```html
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
```

y el bundle JS al cierre de `<body>`:

```html
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
```

Reglas de integración:
1. `style.css` se carga **después** de Bootstrap para servir como capa de marca y sobreescritura selectiva.
2. No se sustituye `style.css` por completo; Bootstrap provee la base (grid, utilidades, componentes) y `style.css` aporta la identidad visual de ConectaResto.
3. Se prefieren clases de utilidad de Bootstrap (`p-*`, `m-*`, `gap-*`, `d-*`) para espaciado y visibilidad.
4. Componentes de Bootstrap a usar: `container`, `row`/`col`, `card`, `btn`, `form-control`, `form-select`, `table`, `badge`, `alert`, `modal`, `offcanvas`, `toast`, `navbar`.
5. Clases en conflicto con `style.css` (`.btn`, `.card`, `.table`, `.container`, `.badge`) se resuelven cargando `style.css` después y ajustando selectores, no eliminando Bootstrap.

## Proceso de implementación por pantalla

1. **Infraestructura:** agregar CDN Bootstrap a `base.html`; crear capa de marca en `style.css`; verificar `login.html` y `unauthorized.html`.
2. **ADMIN (prioridad 1):** rediseño completo de `app/templates/admin.html` (mesas, categorías, productos, usuarios) con componentes reutilizados.
3. **Paneles de rol:** `login.html`, `waiter.html`, `waiter/pedidos.html`, `waiter/mesas.html`, `kitchen.html`, `kitchen/pedidos.html`, `cashier.html`.
4. **Index:** `app/templates/index.html`.
5. **Validación:** comprobar cada pantalla en navegador desktop y móvil; corregir conflictos visuales.

## Restricciones estrictas

- No modificar lógica de negocio, rutas, controladores, modelos, migraciones ni base de datos durante tareas exclusivamente visuales.
- No instalar Bootstrap todavía (solo documentar su integración futura mediante CDN).
- No modificar HTML, CSS ni JavaScript como parte de esta skill; la skill solo documenta el diseño.
- No crear archivos adicionales más allá de este `SKILL.md`.
- No modificar las reglas permanentes del proyecto.
- No hacer commit, push ni merge.
- No acceder a MySQL.

## Archivos involucrados (referencia, sin modificar aún)

- Reglas permanentes del proyecto.
- `app/templates/base.html` — layout base a integrar con Bootstrap CDN.
- `app/static/css/style.css` — capa de marca sobre Bootstrap.
- `app/static/css/public_menu.css` — menú público, se mantiene independiente.
- `app/templates/admin.html`, `login.html`, `unauthorized.html`, `index.html`, `waiter.html`, `waiter/pedidos.html`, `waiter/mesas.html`, `kitchen.html`, `kitchen/pedidos.html`, `cashier.html` — plantillas candidatas a rediseño visual futuro.

## Criterios de aceptación

- Estética clara, sencilla, moderna y minimalista, sin apariencia empresarial excesiva.
- Espaciado, tipografía, botones, formularios y tablas consistentes en todas las pantallas.
- Diseño verificable en navegador desktop y móvil.
- Bootstrap 5 integrable mediante CDN sin romper los estilos existentes.
- Cero cambios en backend, modelos o base de datos.
- Ningún archivo modificado además de este `SKILL.md`.
