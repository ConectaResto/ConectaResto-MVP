# AGENTS.md — ConectaResto-MVP

Instrucciones permanentes para cualquier agente de IA que trabaje en este proyecto.

## 1. Contexto

ConectaResto-MVP es un proyecto nuevo e independiente del antiguo backend NestJS. No se debe consultar, reutilizar ni importar código del backend NestJS anterior. Toda la implementación parte de cero bajo el stack y el plan definidos a continuación.

## 2. Stack obligatorio

| Componente | Tecnología |
|---|---|
| Backend | Flask (Python) |
| Lenguaje backend | Python |
| Frontend | HTML, CSS, JavaScript Vanilla |
| Base de datos | MySQL |
| ORM / migraciones | SQLAlchemy, Flask-Migrate |
| Pruebas | Pytest |

No se debe usar tecnologías fuera de este stack sin justificación y autorización explícita del usuario.

## 3. Fuente de verdad

Antes de comenzar cualquier tarea, leer `PLAN_DE_TRABAJO_MVP.md`. Es el documento de referencia que define el alcance, las fases, los roles, las reglas de negocio, las funcionalidades excluidas y las decisiones pendientes.

## 4. Inspección y reutilización

Revisar la estructura actual del proyecto y reutilizar primero los componentes existentes (modelos, rutas, fixtures, pruebas, utilidades). Evitar crear duplicados innecesarios. No inventar archivos o módulos que ya existan con otro nombre.

## 5. Autonomía

Para tareas autorizadas, el agente debe inspeccionar, planificar, implementar, ejecutar pruebas, corregir errores y presentar resultados sin detenerse a pedir confirmación en cada paso rutinario. Solo se debe solicitar intervención del usuario cuando exista un bloqueo real, una decisión de negocio pendiente o una restricción que exceda el alcance autorizado.

## 6. Dependencias

Utilizar primero las dependencias ya definidas en `requirements.txt`. Si una dependencia adicional resulta necesaria, explicar por qué y solicitar autorización al usuario antes de incorporarla. No instalar dependencias por cuenta propia.

## 7. Arquitectura

Respetar el diseño existente (factory `create_app()`, instancia `db` a nivel de módulo, migraciones con Flask-Migrate, patrón de pruebas con Pytest). Evitar duplicaciones, complejidad innecesaria y soluciones fuera del alcance del MVP.

## 8. Calidad

Ejecutar las pruebas relevantes después de cada implementación. No declarar una tarea terminada si existen errores conocidos sin explicarlos claramente. El código debe pasar las pruebas automatizadas antes de considerarse completo.

## 9. Seguridad

No publicar credenciales, contraseñas, tokens ni archivos `.env` en el repositorio. Usar variables de entorno para configuración sensible (URI de MySQL, secret key, etc.).

## 10. Decisiones pendientes

No inventar ni implementar decisiones de negocio que `PLAN_DE_TRABAJO_MVP.md` identifique como pendientes (sección "Decisiones pendientes"). Ejemplos: medios de pago exactos, comprobante de pago, política de cancelación, expiración de sesión, URL de QR, retención de datos. Si una tarea requiere una decisión pendiente, informarlo y esperar autorización.

## 11. GitHub y control de versiones

No ejecutar `commit`, `push`, `merge` ni publicar cambios sin autorización explícita del usuario. No crear el repositorio remoto sin instrucciones expresa del usuario.

## 12. Alcance

No introducir funcionalidades ajenas al MVP sin aprobación del usuario. Las funcionalidades excluidas del MVP (sección 6 del plan) no deben implementarse: multisucursal, reservas, delivery, inventario detallado, facturación electrónica, pasarelas de pago reales, notificaciones push/email, reportes avanzados, roles adicionales.

## 13. Comunicación al finalizar

Al terminar cada tarea, informar:
- Archivos modificados, creados o eliminados.
- Funcionalidades implementadas.
- Pruebas ejecutadas y resultados.
- Problemas encontrados y cómo se resolvieron.
- Pendientes o bloqueos para el siguiente paso.

## 14. Documentación

Mantener `PLAN_DE_TRABAJO_MVP.md` y cualquier otra documentación coherente con el código real. Si el código cambia de forma que afecta al plan, actualizar la documentación correspondiente antes de considerar la tarea terminada.

## 15. Equipos de desarrollo asistidos por IA

El proyecto se desarrolla con cuatro agentes asistidos por IA bajo la coordinación de ChatGPT A sobre el mismo repositorio remoto:

| Identificador | Responsabilidad |
|---|---|
| **Escritorio Kilo 1** | Base de datos, migraciones e integración |
| **Escritorio Codex 1** | Backend: servicios y pedidos |
| **Portátil Kilo 2** | Frontend HTML/CSS/JavaScript |
| **Portátil Codex 2** | Backend: QR y menú público |

Cada agente trabaja en su propio computador y en ramas independientes. No se modifica directamente `main`. La integración se realiza mediante Pull Requests con aprobación conjunta del coordinador.

Antes de iniciar cualquier tarea, consultar `docs/COORDINACION_EQUIPOS_IA.md` para conocer las reglas de coordinación, separación de responsabilidades y protección de la rama `main`. Los cambios de arquitectura, contratos compartidos, dependencias y reglas de negocio requieren consulta previa entre equipos.

La documentación histórica del Equipo B se conserva en `docs/INSTRUCCIONES_CHATGPT_B.md` y no ha sido modificada.

---