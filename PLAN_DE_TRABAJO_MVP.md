# PLAN_DE_TRABAJO_MVP — ConectaResto

**Objetivo:** Definir la hoja de ruta oficial del Minimum Viable Product (MVP) de ConectaResto, un sistema de punto de venta y gestión de restaurantes para un único establecimiento.

---

## 0. Stack tecnológico aprobado

| Componente | Tecnología |
|---|---|
| Backend | Flask (Python) |
| Lenguaje backend | Python |
| Frontend | HTML, CSS, JavaScript Vanilla |
| Base de datos | MySQL |
| ORM / migraciones | SQLAlchemy, Flask-Migrate |
| Pruebas | Pytest |

---

## 1. Alcance del MVP

- **Restaurante único:** una sola instancia del sistema, no multiempresa ni multisucursal.
- **Roles:** `ADMIN`, `WAITER`, `KITCHEN`, `CASHIER`.
- **Cliente público:** acceso sin autenticación para consultar el menú y generar pedidos mediante QR.
- **Separación de conceptos:** pedidos, preparación (estado de cocina) y pagos son entidades/estados independientes.
- **Canales de uso:**
  - Panel de administración (ADMIN).
  - Panel del mesero (WAITER).
  - Panel de cocina (KITCHEN).
  - Panel de caja (CASHIER).
  - Menú público para clientes (sin autenticación).

---

## 2. Hoja de trabajo — 12 fases

### Fase 0 — Preparación del proyecto

- Crear estructura de carpetas del proyecto Python/Flask.
- Configurar `requirements.txt` con Flask, SQLAlchemy, Flask-Migrate, Pytest y MySQL driver.
- Configurar `pytest.ini` y `testpaths`.
- Inicializar control de versiones Git (local, sin repositorio remoto todavía).
- Crear `AGENTS.md` con reglas de trabajo y convenciones del repositorio.
- Definir variables de entorno para configuración (URI de MySQL, secret key, entorno).

### Fase 1 — Diseño funcional y reglas de negocio

- Definir catálogo de entidades: Producto, Categoría, Mesa, Pedido, Línea de pedido, Pago, Usuario, Rol.
- Definir estados de pedido (ej. pendiente, en preparación, listo, entregado, cancelado).
- Definir estados de preparación de cocina (ej. recibido, en cocina, listo para servir).
- Definir estados de pago (ej. pendiente, pagado, reembolsado).
- Definir reglas de negocio: creación de pedido, asignación a mesa, cambio de estado por rol, cierre de caja, validación de stock (si aplica).
- Documentar flujos: cliente ordena por QR → mesero toma pedido → cocina prepara → caja cobra.

### Fase 2 — Fundación técnica

- Configurar aplicación Flask con factory `create_app()`.
- Conectar SQLAlchemy a MySQL y configurar Flask-Migrate.
- Crear modelo base y primeras migraciones.
- Implementar health check `/health`.
- Configurar CORS si es necesario para el frontend.
- Configurar logging básico y manejo global de errores (400, 401, 403, 404, 500).
- Pruebas unitarias básicas de la aplicación y la base de datos.

### Fase 3 — Usuarios, autenticación y permisos

- Modelo `Usuario` y `Rol` (ADMIN, WAITER, KITCHEN, CASHIER).
- Registro y autenticación de usuarios (login/token o sesión).
- Middleware de autorización por rol en endpoints.
- Endpoints de gestión de usuarios (solo ADMIN puede crear/editar/desactivar otros usuarios).
- Protección de rutas sensibles según el rol del usuario autenticado.
- Pruebas de autenticación y autorización por rol.

### Fase 4 — Administración

- CRUD de productos (nombre, descripción, precio, categoría, disponibilidad).
- CRUD de categorías.
- Gestión de mesas (crear, editar, cambiar estado: disponible/ocupada/cerrada).
- Gestión de usuarios y roles (ADMIN).
- Dashboard resumen para ADMIN (ventas, pedidos, productos más vendidos).
- Pruebas del módulo de administración.

### Fase 5 — QR y menú público

- Generación de código QR por mesa (enlace al menú público).
- Menú público sin autenticación: listar productos disponibles por categoría.
- Cliente público puede crear un pedido asociado a una mesa mediante QR.
- Validación de disponibilidad de producto al ordenar.
- Pruebas del menú público y generación de QR.

### Fase 6 — Servicios y pedidos

- Creación de pedidos (mesero o cliente público).
- Líneas de pedido: producto, cantidad, precio unitario, subtotal.
- Estados del flujo de pedido: pendiente → en preparación → listo → entregado → cancelado.
- Asignación de pedido a mesa.
- Cálculo automático de totales.
- Consulta y listado de pedidos activos y históricos.
- Pruebas de creación, consulta y cambio de estado de pedidos.

### Fase 7 — Panel del mesero (WAITER)

- Vista de mesas con estado y pedidos asociados.
- Tomar pedido para una mesa desde el panel.
- Enviar pedido a cocina (cambiar estado a "en preparación").
- Marcar pedido como entregado al cliente.
- Cerrar mesa cuando el cliente se retira.
- Pruebas del panel del mesero.

### Fase 8 — Panel de cocina (KITCHEN)

- Vista de pedidos pendientes de preparación.
- Cambiar estado de preparación: recibido → en cocina → listo para servir.
- Notificación visual de nuevos pedidos (si aplica).
- Marcar ítems/listo de preparación.
- Pruebas del panel de cocina.

### Fase 9 — Panel de caja (CASHIER)

- Vista de pedidos listos para cobrar.
- Registrar pago de un pedido (efectivo, tarjeta, otros medios acordados).
- Generar comprobante de pago (si aplica).
- Cierre de caja diario (totalizaciones por medio de pago).
- Pruebas del panel de caja y cierre de caja.

### Fase 10 — Frontend e integración

- Implementar interfaces HTML/CSS/JS Vanilla para todos los paneles (ADMIN, WAITER, KITCHEN, CASHIER, público).
- Conectar frontend con los endpoints del backend Flask.
- Manejo de autenticación y sesión en el cliente.
- Navegación entre paneles según el rol del usuario.
- Diseño responsivo básico para uso en tablet/móvil (mesero, cocina, caja).
- Pruebas de integración frontend-backend.

### Fase 11 — Pruebas integrales y correcciones

- Pruebas de extremo a extremo (E2E) por flujo completo: ordenar → preparar → cobrar.
- Pruebas de integración entre módulos (usuarios, pedidos, cocina, caja).
- Pruebas de validación de reglas de negocio y estados.
- Pruebas de carga ligera y casos borde (pedido sin productos, precio cero, mesa inexistente, rol sin permiso).
- Corrección de defectos encontrados.
- Pruebas de regresión antes de la entrega.

### Fase 12 — Documentación y entrega

- Documentar endpoints de la API (método, ruta, parámetros, respuestas, códigos HTTP).
- Documentar modelos de base de datos y relaciones.
- Manual de usuario para cada rol (ADMIN, WAITER, KITCHEN, CASHIER, cliente público).
- Instrucciones de instalación, configuración de variables de entorno y despliegue local.
- Instrucciones para ejecutar pruebas (`pytest`).
- Entrega oficial del MVP al usuario para validación y aceptación.

---

## 3. Roles y permisos

| Rol | Puede | No puede |
|---|---|---|
| `ADMIN` | Todo: usuarios, productos, categorías, mesas, pedidos, caja, reportes | — |
| `WAITER` | Crear/editar pedidos, asignar mesas, cambiar estado de pedido, cerrar mesa | Gestionar usuarios, productos, caja |
| `KITCHEN` | Ver pedidos en preparación, cambiar estado de preparación | Crear pedidos, cobrar, gestionar usuarios |
| `CASHIER` | Ver pedidos listos para cobrar, registrar pagos, cierre de caja | Crear pedidos, gestionar usuarios/productos |
| Cliente público (sin auth) | Ver menú público, crear pedido por QR | Acceder a paneles internos, autenticarse |

---

## 4. Estados y separación de conceptos

- **Pedido:** entidad principal que agrupa líneas de producto, mesa, mesero, fecha y estado general.
- **Preparación:** estado independiente del flujo de cocina (recibido, en cocina, listo para servir, servido).
- **Pago:** entidad independiente vinculada al pedido (monto, medio de pago, estado pendiente/pagado, fecha).
- Un pedido puede existir sin pago (por cobrar) y un pago solo existe si hay un pedido.

---

## 5. Reglas de negocio y funcionalidades acordadas

- Un producto debe estar marcado como disponible para poder agregarse a un pedido.
- El precio de una línea de pedido se captura al momento de crear el pedido (precio unitario del producto en ese instante).
- Un pedido solo puede pasar a "en preparación" si tiene al menos una línea de producto.
- Solo el rol `KITCHEN` puede cambiar el estado de preparación.
- Solo el rol `CASHIER` puede registrar pagos y hacer cierre de caja.
- Solo el rol `ADMIN` puede crear, editar y desactivar usuarios y productos.
- Un cliente público no necesita autenticación para ver el menú ni crear un pedido por QR.
- El cierre de caja registra totales agrupados por medio de pago en un período diario.

---

## 6. Funcionalidades excluidas del MVP (pendientes para versiones futuras)

- Multirestaurante / multisucursal.
- Reservas de mesa.
- Delivery y envío a domicilio.
- Inventario y control de stock detallado.
- Programación de turnos de empleados.
- Facturación electrónica oficial.
- Integración con pasarelas de pago reales (tarjetas, billeteras).
- Notificaciones push o email al cliente.
- Panel de análisis avanzado / reportes exportables.
- Roles adicionales o permisos granulares por usuario individual.

> Cualquier funcionalidad no listada en la sección "Alcance del MVP" se considera excluida y debe aprobarse por separado antes de implementarse.

---

## 7. Criterios generales de validación por fase

Cada fase se considera completada solo cuando:

1. Toda la funcionalidad planificada de la fase está implementada.
2. Existen pruebas automatizadas (Pytest) que cubren los casos de uso principales y los casos borde.
3. Las pruebas de la fase pasan sin errores (`pytest` verde).
4. Se revisó el código y se aprobó la calidad (estilo, nombres, manejo de errores).
5. El usuario (o el responsable de producto) dio su visto bueno a la fase antes de iniciar la siguiente.

---

## 8. Reglas de trabajo y revisión antes de avanzar

- No se inicia la fase N+1 sin la aprobación explícita de la fase N.
- Cada funcionalidad nueva debe contar con al menos una prueba automatizada antes de considerarse terminada.
- Los cambios en la base de datos se gestionan mediante Flask-Migrate (migraciones versionadas).
- No se cometen credenciales, tokens ni secretos en el repositorio.
- Se utiliza `create_app()` y el patrón de factory para facilitar pruebas con configuración aislada.
- Cualquier decisión funcional pendiente de aprobación se documenta como tal y no se asume como aceptada.
- El frontend se integra solo después de que los endpoints del backend estén probados y aprobados.

---

## 9. Decisiones pendientes (no asumir como aprobadas)

Los siguientes puntos requieren confirmación explícita del usuario antes de implementarse:

- Medio(s) de pago exactos aceptados en caja (efectivo, tarjeta, transferencia, otros).
- Si se requiere comprobante/factura impresa o digital por pago.
- Política de cancelación de pedidos y reembolsos.
- Tiempo de expiración de sesión de usuarios autenticados.
- URL base y dominio para generación de QR (localhost para pruebas, producción pendiente).
- Política de retención de datos y borrado de pedidos históricos.

---

**Archivo:** `PLAN_DE_TRABAJO_MVP.md`  
**Ruta exacta:** `C:\Users\1234\Desktop\softwareDeveloper\python\conectaRestoAppMVP\PLAN_DE_TRABAJO_MVP.md`