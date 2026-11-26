# Decisiones técnicas duraderas — registro histórico

Consultar [DECISIONES.md](DECISIONES.md) para la consolidación vigente. Se conservan aquí los fundamentos y sustituciones.

## ADR-001 — GitHub como memoria compartida
**Fecha:** 2026-10-18. **Estado:** adoptada.

**Decisión:** los Issues describen tareas; los PR contienen diff, pruebas, revisiones y traspaso; los commits fijan la versión. Los chats no comparten automáticamente memoria.

## ADR-002 — Experiencia principal: ChatGPT Chat + Claude Chat
**Fecha:** 2026-10-18. **Estado:** adoptada.

**Decisión:** `AGENTS.md` conserva reglas comunes que se consultan bajo demanda. `CHATGPT.md` y `CLAUDE.md` documentan cómo iniciar el trabajo en cada chat. El usuario **no necesita Codex CLI**. No asumir que los archivos del repositorio se cargan solos en las conversaciones web.

## ADR-003 — Revisión cruzada controlada
**Fecha:** 2026-10-18. **Estado:** adoptada.

**Decisión:** ChatGPT propone/implementa con los permisos GitHub disponibles, Claude Chat revisa de forma independiente al aportarle el diff y contexto. CI confirma pruebas. **Sustitución expresa del 03-11-2026:** el propietario autorizó a los agentes a revisar, fusionar y publicar PR validados sin repetir aprobación individual; siguen vigentes el alcance y los controles de AGENTS. Véase [la decisión actual](DECISIONES.md). El intercambio entre los dos chats no es automático.

## ADR-004 — Skills portables, sin instalaciones implícitas
**Fecha:** 2026-10-18. **Estado:** adoptada.

**Decisión:** se conserva una skill opcional `coordinating-chatgpt-claude` para entornos capaces de descubrirla. No se requiere ni se ejecuta un instalador de Codex. Los plugins de ChatGPT y la integración GitHub de Claude necesitan acciones de conexión por separado.
