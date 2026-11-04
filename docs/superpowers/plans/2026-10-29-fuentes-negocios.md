# Fuentes de negocios — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans para implementar esta tarea en la sesión actual.

**Goal:** Incorporar fuentes verificadas de la lista de 100 portales y otras similares, sin perder fuentes o preferencias actuales.

**Architecture:** OPML como origen; regenerar únicamente el catálogo estático mediante `parse_opml`. Guardar observaciones fechadas de RSS y una matriz de las 100 solicitudes. Reutilizar las categorías dinámicas y deduplicación existentes.

**Tech Stack:** Python, requests/feedparser y la aplicación JavaScript existente; ninguna dependencia nueva.

**Spec:** `docs/superpowers/specs/2026-10-29-fuentes-negocios-design.md`.

## Global Constraints

- Preservar las 311 suscripciones y ocho carpetas originales exactamente; no mover duplicados existentes.
- Añadir carpetas 09/10/11 según la especificación; TI empresarial conserva carpeta 02.
- Noticias: entrada observada de los últimos 90 días; revistas periódicas: máximo 730 días, con idioma documentado.
- No RSS inventados, búsquedas vacías presentadas como medios, scraping completo ni evasión de restricciones de red.
- No cambiar workflows, dependencias, preferencias, formatos, retención ni estilo.

## Review Focus

- Nombres ambiguos y portales reubicados: identificar editor, dominio y edición correctos.
- Feeds nativos inaccesibles: distinguir no comprobado, inválido y sin entradas recientes.
- Duplicados y ediciones: conservar suscripciones anteriores y no duplicar endpoints equivalentes.
- Revistas trimestrales/bilingües: no confundir cadencia o idioma con noticias diarias en español.
- Catálogo ampliado: nuevas carpetas visibles sin truncar fuentes, romper contadores o perder preferencias.

### Task 1: Investigación y observaciones

**Files:** Scratch `/workspace/scratch/startup-feeds/`; crear `sources/business-sources-verification.json`, `docs/fuentes-startups-negocios-2026-10-29.md`.

**Interfaces:** Cada solicitud usa `number`, `requested_name`, `website`, `status`, `reason`, `feed`; cada alta verificada conserva URL, proveedor, idioma, recencia, fecha, versión RSS y SHA256 de la respuesta.

- [x] Identificar las 100 solicitudes, duplicados y fuentes similares; guardar evidencia de consultas.
- [x] Activar y comprobar acceso nativo mediante el flujo del entorno; continuar investigación independiente mientras esté pendiente. Acceso vigente con 155 dominios; cuatro destinos de redirecciones quedan documentados en un segundo borrador.
- [x] Verificar RSS/Atom y entradas recientes; seleccionar nativos primero y RADAR por dominio solo con resultados válidos.
- [x] Redactar resultado individual para los 100 casos y documentar pendientes reales.

### Task 2: Catálogo y publicación

**Files:** `sources/feeds.opml`, `web/data/sources.json`, comprobaciones históricas de `tests/test_new_catalog.py`, `tests/test_spanish_ai_catalog.py`, `tests/test_world_catalog.py`; pruebas pertinentes de preservación/categorías.

**Interfaces:** `parse_opml` conserva ID SHA256 de cada URL; catálogo y OPML deben coincidir. Las pruebas históricas delimitan su conjunto anterior para admitir altas futuras sin debilitar su comprobación de preservación.

- [x] Registrar la instantánea anterior y comprobar que las pruebas de preservación detectarían pérdida, renombrado o cambios de URL.
- [x] Incorporar solo altas con evidencia; regenerar catálogo sin ejecutar recolección de red en pruebas.
- [x] Adaptar comprobaciones históricas al conjunto anterior y verificar integridad, IDs únicos y concordancia OPML/catálogo.
- [x] Ejecutar auditoría y baterías pertinentes; comprobar carpetas nuevas y preferencias en navegador.
- [ ] Revisión independiente final, PR, CI del commit exacto y publicación autorizada; comprobar catálogo servido y estado de las nuevas fuentes.
