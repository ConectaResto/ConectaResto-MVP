# Orquestación de entrega — ConectaResto-MVP

**Fecha objetivo de entrega:** sábado 21 de noviembre de 2026, consigna oficial del profesor.
**Repositorio:** `https://github.com/ConectaResto/ConectaResto-MVP` (se mantiene; no se crea proyecto nuevo).
**Rama de trabajo:** `docs/orquestacion-entrega-21nov2026` (Agente D).
**Estado:** borrador maestro, pendiente autorización para publicar e integrar.

---

## 1. Objetivo

Entregar ConectaResto-MVP cumpliendo la consigna oficial del profesor, con el flujo principal completo conservado:

1. Cliente escanea QR.
2. Consulta menú y realiza pedido.
3. Mesero autoriza el pedido.
4. Cocina recibe y prepara.
5. Mesero entrega.
6. Caja registra pago simulado.
7. Se cierra el servicio y libera la mesa.

---

## 2. Decisiones definitivas

| Decisión | Alcance |
|----------|---------|
| Repositorio | Se mantiene el repositorio actual de ConectaResto-MVP. No se crea un proyecto nuevo ni se clonan repositorios separados por agente. |
| Integración | Los cuatro agentes trabajan en paralelo, pero los cambios se integran exclusivamente mediante revisión y Pull Request. |
| Rama principal | No se modifica directamente `main`. Cada agente trabaja en su propia rama de funcionalidad. |
| Operaciones Git | Commit, push y merge requieren autorización humana expresa del coordinador. |
| Funcionalidades | No se introducen funcionalidades nuevas fuera del alcance del MVP. |
| Modelos y migraciones | No se modifican modelos ni migraciones sin autorización. |
| Dependencias | No se añaden dependencias innecesarias. |
| Pruebas | No se eliminan pruebas existentes. |
| Componentes | Se reutilizan componentes actuales (modelos, rutas, servicios, fixtures, pruebas, utilidades). |
| Organización antigua | No se utiliza la antigua organización de equipos Kilo/Codex. |
| Reglas técnicas | Se mantienen las reglas técnicas y de seguridad vigentes de `AGENTS.md`. |
| Documentación | La documentación final debe coincidir con el código implementado. |
| Prioridad | La consigna oficial del profesor tiene prioridad sobre los ejemplos del manual ALOJAMIENTOS. |

---

## 3. Reglas generales de trabajo

1. Cuatro clones independientes: Agente-A, Agente-B, Agente-C y Agente-D.
2. Cada agente trabaja únicamente en su área autorizada.
3. No modificar directamente `main`.
4. PR obligatorios para cualquier integración.
5. Commit, push y merge requieren autorización humana.
6. No introducir funcionalidades nuevas.
7. No modificar modelos ni migraciones sin autorización.
8. No añadir dependencias innecesarias.
9. No eliminar pruebas existentes.
10. Reutilizar componentes actuales antes de crear otros.
11. No utilizar la antigua organización de equipos Kilo/Codex.
12. Mantener las reglas técnicas y de seguridad válidas de `AGENTS.md`.
13. La consigna oficial del profesor tiene prioridad sobre los ejemplos del manual ALOJAMIENTOS.
14. La documentación final debe coincidir con el código implementado.

---

## 4. Responsabilidades por agente

### Agente A — Frontend (Jira CRMVP-15, CRMVP-16)

- Crea una SPA sencilla con HTML5, CSS3, JavaScript vanilla y Bootstrap, en la carpeta `frontend/`.
- Utiliza navegación mediante hash, componentes reutilizables, estado y API REST.
- **No modifica el backend.** Debe conservar los contratos reales de Flask.
- Reutiliza plantillas y scripts estáticos existentes cuando apliquen (`app/static/js/`, `app/templates/`).

### Agente B — Backend (Jira CRMVP-17, CRMVP-18)

- Puede modificar exclusivamente:
  - `app/pedidos/repository.py`
  - `app/pedidos/dto.py`
  - `app/servicios/repository.py`
  - `app/servicios/dto.py`
  - Los archivos `service.py` y `routes.py` de los módulos `pedidos` y `servicios`, únicamente cuando sea necesario para conectar repositorios y DTO.
- Conserva rutas HTTP, formatos JSON, códigos de respuesta, permisos, transacciones y comportamiento.
- No puede modificar modelos, migraciones ni otros dominios sin autorización.
- No debe crear patrones genéricos innecesarios.
- **No hace una refactorización completa del backend.**

### Agente C — Documentación (Jira CRMVP-19, CRMVP-20)

- Crea el informe HTML final según la consigna oficial del profesor, cubriendo las fases 01 a 05.
- Revisa la documentación arquitectónica previa en `https://drive.google.com/drive/folders/1hJxBNN4lWGE3JznmLeWWi9kvPip2QIJt` (cinco subcarpetas, cada una con un documento Word).
- Recupera evidencias y crea solamente los diagramas que falten. No se ha confirmado que los catorce diagramas históricos estén disponibles como archivos independientes.

### Agente D — Auditoría e integración (Jira CRMVP-21, CRMVP-22, apoyo a CRMVP-23)

- Verifica los cambios de los demás agentes.
- Ayuda a servir la SPA desde Flask.
- Ejecuta pruebas autorizadas y comprueba el flujo completo con MySQL.
- **No desarrolla repositorios ni DTO.**
- Identifica riesgos, puntos de integración y posibles conflictos entre agentes.
- Prepara la lista de verificaciones para los cambios de los demás agentes.

---

## Jerarquía de instrucciones y prioridad de fuentes

Cuando varias fuentes definan alcance o reglas, aplicar el siguiente orden de prioridad:

1. Consigna oficial del profesor para requisitos académicos.
2. Decisiones expresas del coordinador para alcance y distribución del trabajo.
3. Documento maestro actual (`docs/ORQUESTACION_ENTREGA_21NOV2026.md`) para responsabilidades A/B/C/D.
4. `AGENTS.md` para reglas técnicas y de seguridad compatibles.

No aplicar asignaciones de equipos antiguos Kilo/Codex.

---

## 5. Documentación de referencia

| Documento | Contenido |
|-----------|-----------|
| `AGENTS.md` | Instrucciones permanentes para cualquier agente de IA (stack, arquitectura, seguridad, calidad, alcance, comunicación). |
| `PLAN_DE_TRABAJO_MVP.md` | Fuente de verdad: alcance, fases, roles, reglas de negocio, funcionalidades excluidas, decisiones pendientes. |
| `README.md` | Instalación, configuración `.env`, migraciones, seed-demo, recorrido de demostración, ejecución de pruebas. |
| `docs/COORDINACION_EQUIPOS_IA.md` | Reglas de coordinación, separación de responsabilidades y protección de la rama `main`. |
| `docs/ESTADO_CIERRE_MVP.md` | Estado del cierre del MVP tras Entrega F, riesgos, verificación ejecutada y comandos de repetición. |
| `docs/E3_MENU_PUBLICO.md` | Acceso público y menú QR (contrato, rutas, interfaz de cliente, validación histórica). |
| `docs/QR_PUBLICO.md` | QR público y menú por mesa (variable `PUBLIC_BASE_URL`, rutas, notas de implementación). |
| `app/pedidos/CONTRACT.md` | Contrato de API de servicios y pedidos (rutas, creación compartida, transiciones, verificación). |
| `app/catalog/CONTRACT.md` | Contrato de API de categorías y productos (endpoints, modelo, reglas de negocio). |
| Google Drive | Carpeta con documentación arquitectónica previa (cinco subcarpetas, cada una con un documento Word). No es la ubicación confirmada de la consigna oficial del profesor; el Agente C debe usar el texto original del encargo como referencia principal y consultar esta carpeta solo como fuente de evidencias y diagramas históricos. |

---

## 6. Flujo de integración

1. Cada agente clona el repositorio y crea su propia rama de funcionalidad a partir de `origin/main`.
2. Cada agente desarrolla únicamente en su área autorizada, reutilizando componentes existentes.
3. Cada agente ejecuta las pruebas correspondientes antes de solicitar integración.
4. Cada agente abre un Pull Request hacia `main` con evidencia de pruebas y cambios.
5. El coordinador revisa los informes y cambios, y autoriza el merge cuando correspondan.
6. Después de cada merge a `main`, los agentes se sincronizan antes de integrar sus siguientes cambios.
7. No se realizan commits, push, merges, rebases, resets ni eliminación de ramas sin autorización del coordinador.

---

## 7. Áreas autorizadas y archivos protegidos

### Área autorizada por agente

- **Agente A:** `frontend/` (SPA HTML/CSS/JS + Bootstrap). Puede reutilizar `app/static/` y `app/templates/` sin modificarlos.
- **Agente B:** `app/pedidos/` y `app/servicios/` (repositorios y DTO mínimos). No toca rutas, JSON, permisos, transacciones, modelos ni migraciones.
- **Agente C:** Informe HTML final y diagramas faltantes. Documentación en `docs/`.
- **Agente D:** Auditoría, integración, verificación de pruebas, flujo completo con MySQL, ayuda a servir la SPA desde Flask. No desarrolla código de negocio.

### Archivos protegidos (sin autorización expresa del coordinador)

- `app/models/*` (modelos de datos).
- `migrations/versions/*` (migraciones versionadas con Flask-Migrate).
- `app/__init__.py` (factory `create_app`, registro de blueprints).
- `app/config.py` (configuración y variables de entorno).
- `app/extensions.py` (instancia `db` y `migrate`).
- `requirements.txt` (dependencias).
- `tests/*` (pruebas existentes; no se eliminan ni se sustituyen).

---

## 8. Reglas técnicas y de seguridad (AGENTS.md)

- Stack obligatorio: Flask (Python), HTML/CSS/JavaScript Vanilla, MySQL 8, SQLAlchemy + Flask-Migrate, Pytest. No usar tecnologías fuera del stack sin justificación y autorización explícita.
- Respetar el diseño existente: factory `create_app()`, instancia `db` a nivel de módulo, migraciones con Flask-Migrate, patrón de pruebas con Pytest.
- No publicar credenciales, contraseñas, tokens ni archivos `.env` en el repositorio. Usar variables de entorno para configuración sensible (URI de MySQL, secret key, `PUBLIC_BASE_URL`).
- El archivo `.env` está en `.gitignore` y no se sube al repositorio.
- Ejecutar las pruebas relevantes después de cada implementación. El código debe pasar las pruebas automatizadas antes de considerarse completo.
- No declarar una tarea terminada si existen errores conocidos sin explicarlos claramente.

---

## 9. Decisiones pendientes (no asumir como aprobadas)

Según `PLAN_DE_TRABAJO_MVP.md` §9, los siguientes puntos requieren confirmación explícita del usuario antes de implementarse:

- Medio(s) de pago exactos aceptados en caja (efectivo, tarjeta, transferencia, otros).
- Si se requiere comprobante/factura impresa o digital por pago.
- Política de cancelación de pedidos y reembolsos.
- Tiempo de expiración de sesión de usuarios autenticados.
- URL base y dominio para generación de QR (localhost para pruebas, producción pendiente).
- Política de retención de datos y borrado de pedidos históricos.

Ningún agente debe inventar ni implementar estas decisiones. Si una tarea requiere una decisión pendiente, informarla y esperar autorización.

---

## 10. Funcionalidades excluidas del MVP

No introducir (según `PLAN_DE_TRABAJO_MVP.md` §6):

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

---

## 11. Criterios de aceptación para la entrega (21 nov 2026)

- Suite Pytest verde (salvo omisión documentada de collation MySQL, ejecutable por separado en MySQL 8).
- Migraciones aplicadas hasta `014_add_image_filename_to_products` sin errores.
- `GET /health` responde HTTP 200.
- Flujo completo verificado con MySQL: QR → pedido → cocina → caja → liberación de mesa.
- Contratos de API (`app/pedidos/CONTRACT.md`, `app/catalog/CONTRACT.md`) respetados por todos los módulos.
- SPA servida desde Flask, navegación por hash, consumo de API REST real.
- Informe HTML final (fases 01 a 05) coherente con el código implementado.
- Sin credenciales ni `.env` comprometidos en el repositorio.
- Documentación final coincidente con el código implementado.

---

## 12. Estado de Git (Agente D)

| Campo | Valor |
|-------|-------|
| Rama actual | `docs/orquestacion-entrega-21nov2026` |
| Rama base | `main` (sincronizada con `origin/main`) |
| Working tree | Un archivo nuevo sin seguimiento (`docs/ORQUESTACION_ENTREGA_21NOV2026.md`), pendiente de incorporación a Git. No se ha realizado commit, push ni merge. |
| Último commit en `main` | `4f77eac` (Merge PR #48, documentación post-Entrega F) |
| Archivo creado por este agente | `docs/ORQUESTACION_ENTREGA_21NOV2026.md` |
| Operaciones pendientes | Commit, push y merge requieren autorización humana |

---

## 13. Próximos pasos pendientes de autorización

1. Publicar la rama `docs/orquestacion-entrega-21nov2026` y abrir un PR hacia `main`.
2. Ejecutar pruebas autorizadas (`pytest -q`) tras la integración de los cambios de Agentes A, B y C.
3. Verificar el flujo completo con MySQL (QR, pedido, cocina, caja, liberación de mesa).
4. Apoyar la verificación final de archivos y repositorio (CRMVP-23).
5. Realizar commit/push/merge solo con autorización humana expresa del coordinador.

Espera autorización antes de publicar la rama, ejecutar pruebas o modificar el proyecto.
