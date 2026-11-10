# Research retention implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement task-by-task.

**Goal:** Conservar investigación académica con ventana propia sin aumentar el archivo ni desplazar completamente otras noticias.
**Architecture:** Ampliar el colector existente con recencia por catálogo y selección protegida dentro de los límites. El frontend consume los mismos JSON/particiones.
**Tech Stack:** Python/Node, Playwright con fixtures.
**Spec:** docs/superpowers/specs/2026-11-10-research-retention.md

## Global constraints
Research730días/reserva200, otras categorías45días por defecto, total5000/candidatos7500/partes300; fechas y créditos originales; catálogo actual; sin dependencias nuevas, sin cambios en deploy.yml.

## Review focus
Categorías antiguas de caché; fuente académica retirada; reserva antes del corte de candidatos; duplicados entre fuentes; fallo de red que conserva trabajos válidos.

## Task1: Política y publicación
Files: scripts/collect.py; tests/test_research_retention.py.
- [ ] RED: colector completo con RSS simulado mantiene trabajos anteriores a45días; elimina mayores730, conserva cutoff45 para noticias y fecha exacta, rechaza categorías de caché sin fuente válida.
- [ ] RED: más7500 noticias no expulsan investigación; más5000 mantiene límite/reserva y orden; pocos trabajos no dejan huecos; mismo límite tras agrupar/refrescar y cuotas con otra carpeta.
- [ ] GREEN: constants RESEARCH_CATEGORY/RESEARCH_DAYS/RESEARCH_RESERVE, selector `select_retained(ordered,limit)`, recencia por categoría recalculada. Selección protegida antes de group_related_articles y después. `research_articles` en resultado de ingesta.
- [ ] Verificar toda suite Python y contratos Node existentes.

## Task2: Flujo de carpeta y cierre
Files: browser_tests/research_retention.py; .github/workflows/responsive.yml; docs/research-retention-2026-11-10.md.
- [ ] Fixture5000 entradas, últimos300 utilizables y archivo con artículos académicos antiguos; carpeta muestra cantidad/fecha real y título abre fuente original; filtro de fecha explícito se respeta y se puede quitar.
- [ ] Revisión independiente de diff y pruebas; corregir hallazgos importantes con regresión.
- [ ] Commit/PR, esperar CI, fusionar SHA verificado y comprobar build con research_articles>0 + generación pública correcta.
