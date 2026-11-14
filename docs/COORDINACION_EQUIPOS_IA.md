# Coordinación de Equipos de Desarrollo Asistidos por IA

ConectaResto-MVP se desarrolla con dos equipos asistidos por IA que operan sobre el mismo repositorio remoto. Este documento establece las reglas de coordinación, separación de responsabilidades y flujo de trabajo para ambos equipos.

## 1. Composición de los equipos

| Equipo | Miembros |
|--------|----------|
| **Equipo A** | Desarrollador A + ChatGPT A + Kilo + Codex |
| **Equipo B** | Desarrollador B + ChatGPT B + Kilo |

## 2. Roles y responsabilidades

### Equipo A
- **Desarrollador A y ChatGPT A**: coordinan el reparto general de trabajo y las aprobaciones conjuntas.
- **Kilo y Codex**: agentes de programación y auditoría asignados al Equipo A según se necesite.

### Equipo B
- **Desarrollador B y ChatGPT B**: coordinan la ejecución técnica de los lotes asignados al Equipo B.
- **Kilo**: agente de programación y auditoría del Equipo B.

Cada equipo trabaja en su propio computador y en ramas independientes del mismo repositorio remoto.

## 3. Reglas generales de trabajo

- No se modifica directamente la rama `main`.
- La integración se realiza mediante Pull Requests y aprobación conjunta de ambos equipos.
- Cada equipo trabaja únicamente en sus módulos autorizados.
- Los cambios de arquitectura, contratos compartidos, dependencias y reglas de negocio requieren consulta previa antes de implementarse.
- Los informes se entregan por lote funcional terminado, no por cada tarea pequeña.
- Ante bloqueos parciales, se informa y se continúa con trabajo independiente autorizado.
- Prohibido realizar commits, push, merges o acciones Git destructivas sin autorización humana expresa.

## 4. Fuentes de verdad

- `PLAN_DE_TRABAJO_MVP.md`: alcance, fases, roles, reglas de negocio, funcionalidades excluidas y decisiones pendientes.
- `AGENTS.md`: instrucciones permanentes para cualquier agente de IA.
- `docs/COORDINACION_EQUIPOS_IA.md`: este documento, reglas de coordinación entre equipos.
- `docs/INSTRUCCIONES_CHATGPT_B.md`: instrucciones específicas para ChatGPT B.

## 5. Primera propuesta de lote para el Equipo B

**Lote propuesto (pendiente de autorización):** Administración de categorías y productos.

Este lote no está aprobado para implementación hasta que el Equipo A (Desarrollador A + ChatGPT A) lo autorice explícitamente.

---