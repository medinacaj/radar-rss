# Reglas compartidas para agentes — Radar RSS

Este archivo recoge reglas compartidas para trabajar desde ChatGPT Chat y Claude Chat a través de GitHub. **Los chats no lo cargan automáticamente:** pedir expresamente leerlo o seleccionarlo mediante la integración GitHub. Leer primero este archivo y la tarea actual; ampliar contexto bajo demanda.

## Principios
- GitHub Issues, commits y Pull Requests son la fuente de verdad. No asumir memoria de otras conversaciones.
- Una tarea = una rama = un PR. Nunca escribir directo en `main`.
- Autorización expresa del usuario (2026-11-03): los agentes pueden revisar, fusionar y publicar los PR de Radar RSS sin solicitar aprobación humana en cada ocasión. Verificar el diff, resolver conflictos y ejecutar las pruebas pertinentes antes de fusionar; informar de bloqueos reales. Esta autorización sustituye el requisito anterior de revisión humana previa.
- Antes de editar, delimitar criterios de aceptación y archivos afectados. Leer diffs antes que archivos enteros.
- Preferir cambios pequeños y reversibles; no reformatear archivos ajenos al alcance ni hacer refactors oportunistas.
- No añadir secretos, datos privados, dependencias o servicios externos sin justificación/aprobación.
- No ejecutar acciones destructivas, despliegues ni modificaciones de producción fuera de una tarea aprobada.
- No afirmar que algo se probó, se revisó o se publicó si no hay evidencia real.

## Proyecto
Python 3.12 para ingesta y pruebas; frontend JavaScript estático; GitHub Pages.
- `scripts/collect.py`: obtención y normalización RSS. Evitar consultas de red en tests.
- `scripts/insights.py`: agrupación y tendencias.
- `sources/feeds.opml`: configuración de medios.
- `web/`: interfaz y datos estáticos.
- `.github/workflows/deploy.yml`: ingestión periódica y publicación; no modificar sin tarea explícita.

## Pruebas locales pertinentes
```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
node --check web/app.js
node --check web/library.js
node --check web/sidebar-layout.js
node --check web/news-effects.js
node --check web/features.js
node --check web/sw.js
node tests/test_sidebar_behavior.cjs
node tests/test_news_effects.cjs
```
Ejecutar solo las pruebas relevantes, o toda la batería antes de cerrar si el cambio es transversal. Nunca depender de respuestas reales de terceros durante tests.

## Transferencia implementador → revisor
Dejar en el PR (preferiblemente menos de 200 palabras): referencia al issue, archivos, resumen del diff, pruebas ejecutadas y resultados, riesgos y preguntas abiertas. Identificar SHA del commit. No pegar conversaciones completas.

## Revisión independiente
El agente revisor inspecciona primero el diff y los tests; luego abre dependencias concretas si hace falta. Reporta solo hallazgos accionables con severidad, `archivo:línea`, causa y corrección sugerida. No modificar código durante una auditoría; devolver observaciones al implementador. Si no hay hallazgos, decirlo sin prometer ausencia de errores.

## Información ampliada
- `docs/architecture.md`: mapa técnico.
- `docs/agent-workflow.md`: flujo entre ChatGPT y Claude en interfaces de chat, prompts y economía de tokens.
- `CHATGPT.md` y `CLAUDE.md`: cómo cargar el contexto en cada conversación.
- `docs/project-status.md`: ubicación de tareas y estados vivos.
- `docs/decisions.md`: decisiones duraderas.

## Criterios jurídico-tecnológicos transversales
Al diseñar, corregir, auditar o publicar, leer `docs/ASESOR_LEGAL_TECNOLOGICO.md`. Aplicar sus siete capas cuando sean relevantes (legal, técnica, seguridad, datos, evidencia, responsabilidad y negocio), documentar jurisdicción, licencias y datos, y separar hechos de hipótesis. No afirmar cumplimiento legal ni autorizaciones sin evidencia. Estas pautas complementan, sin sustituir, las pruebas técnicas y el criterio profesional habilitado.
