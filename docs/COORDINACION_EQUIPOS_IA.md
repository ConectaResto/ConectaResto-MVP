# Coordinación de Equipos de Desarrollo

ConectaResto-MVP es un proyecto de desarrollo de software para gestión de restaurantes. Este documento establece las reglas de coordinación, separación de responsabilidades y flujo de trabajo para el equipo de desarrollo.

## 1. Composición del equipo de desarrollo

| Identificador | Responsabilidad |
|---|---|
| Escritorio 1 | Base de datos, migraciones e integración |
| Escritorio 2 | Backend: servicios y pedidos |
| Portátil 1 | Frontend HTML/CSS/JavaScript |
| Portátil 2 | Backend: QR y menú público |

Cada miembro del equipo trabaja en su propia computadora y en una rama de funcionalidad independiente del mismo repositorio remoto.

## 2. Equipos históricos (documentación preservada)

### Equipo B (inactivo actualmente)

El Equipo B permanece documentado con sus reglas y responsabilidades originales en `docs/INSTRUCCIONES_CHATGPT_B.md`. Actualmente no tiene lotes activos asignados. Su primer lote propuesto (Administración de categorías y productos) permanece pendiente de autorización.

## 3. Roles y responsabilidades

### Coordinador general

- Coordinar el trabajo del equipo de desarrollo.
- Definir tareas pequeñas y verificables.
- Aprobar contratos compartidos.
- Revisar informes y cambios.
- Autorizar operaciones Git cuando corresponda.
- Organizar las integraciones y evitar conflictos.
- No declarar una tarea terminada únicamente porque el desarrollador lo afirma; distinguir pruebas reportadas de verificaciones realizadas.

### Escritorio 1

- Base de datos, migraciones e integración.

### Escritorio 2

- Backend: servicios y pedidos.

### Portátil 1

- Frontend HTML/CSS/JavaScript.

### Portátil 2

- Backend: QR y menú público.

## 4. Reglas generales de trabajo

1. Cada miembro del equipo tendrá un directorio Git independiente y una rama de funcionalidad propia.
2. Todos utilizarán `origin/main` como referencia para iniciar nuevas tareas.
3. No modificar directamente `main`.
4. No ejecutar commits, push, merges, rebases, resets ni eliminar ramas sin autorización del coordinador.
5. Cada miembro tendrá una responsabilidad y un conjunto de archivos asignados.
6. Antes de modificar archivos compartidos, deberá solicitar autorización.
7. Reutilizar componentes existentes antes de crear otros. Si hace falta un componente compartido nuevo, consultar antes de crearlo.
8. Los contratos de API, modelos y relaciones entre módulos deberán acordarse antes de desarrollar funcionalidades dependientes.
9. Ejecutar las pruebas correspondientes antes de solicitar integración.
10. Los miembros del equipo pueden desarrollar tareas independientes en paralelo, pero no integrar cambios sin revisión.
11. Después de cada merge a `main`, los miembros deberán sincronizarse antes de integrar sus siguientes cambios.
12. Mantener los nombres oficiales de los miembros del equipo en los informes.
13. Nunca exponer credenciales ni modificar la base de datos sin autorización.
14. Conservar las reglas y responsabilidades vigentes del Equipo B.

## 5. Reglas de interacción entre equipos

- No se modifica directamente la rama `main`.
- La integración se realiza mediante Pull Requests con aprobación conjunta del coordinador.
- Cada miembro trabaja únicamente en sus módulos autorizados.
- Los cambios de arquitectura, contratos compartidos, dependencias y reglas de negocio requieren consulta previa antes de implementarse.
- Los informes se entregan por lote funcional terminado, no por cada tarea pequeña.
- Ante bloqueos parciales, se informa y se continúa con trabajo independiente autorizado.
- Prohibido realizar commits, push, merges o acciones Git destructivas sin autorización humana expresa.

## 6. Fuentes de verdad

- `PLAN_DE_TRABAJO_MVP.md`: alcance, fases, roles, reglas de negocio, funcionalidades excluidas y decisiones pendientes.
- `AGENTS.md`: instrucciones permanentes para cualquier miembro del equipo de desarrollo.
- `docs/COORDINACION_EQUIPOS_IA.md`: este documento, reglas de coordinación entre equipos.
- `docs/INSTRUCCIONES_CHATGPT_B.md`: instrucciones específicas para el Equipo B (documentación preservada).

---