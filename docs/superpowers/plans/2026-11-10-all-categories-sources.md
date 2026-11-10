# All categories sources implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement task-by-task.

**Goal:** Añadir canales pertinentes a las once carpetas, con evidencia honesta y preservación de las 409 suscripciones.
**Architecture:** Ampliación del catálogo OPML y registro de descubrimiento; reutilizar ingesta y frontend existentes.
**Tech Stack:** OPML/XML, JSON, unittest, navegador de búsqueda.
**Spec:** docs/superpowers/specs/2026-11-10-all-categories-sources.md

## Global constraints
Once carpetas existentes, baseline 409 inalterado; mínimo objetivo dos altas útiles por carpeta; español preferente; RADAR identificado y acotado al editor; no inventar verificación operativa ni eludir límites de red. Sin cambios en deploy.yml, retención o dependencias.

## Review Focus
Duplicados de cobertura del mismo editor; canales RSS supuestos; fechas de rastreo confundidas con publicación; resultados nacionales en carpetas locales; exclusión inadvertida de futuras altas al mantener snapshots históricos.

## Task 1: Descubrimiento e integración
Files: sources/feeds.opml, sources/all-categories-discovery-2026-11-10.json, web/data/sources.json (catálogo generado), tests/test_all_categories_catalog.py, tests/pending_catalog_history.py, docs/fuentes-todas-carpetas-2026-11-10.md.
- [x] Contrastar candidatos con baseline y evidencia primaria, en trabajos de investigación independientes por territorio/tema.
- [x] Añadir regresiones sin red: baseline 409/sha inalterado, once carpetas con altas, URLs/IDs únicos, proveedores y evidencia explícitos, RADAR territorial y dominios seguros. Observar fallo antes de integrar.
- [x] Integrar altas en OPML y registro; acotar snapshots históricos exclusivamente mediante URLs de este registro, conservando detección de futuras altas desconocidas.
- [x] Auditoría y batería Python completas, sin solicitudes externas desde tests.

## Task 2: Revisión y publicación
- [ ] Revisión independiente del diff y evidencia; corregir hallazgos importantes con regresiones.
- [ ] PR, CI, fusión y publicación del flujo normal del sitio; contrastar salud de las nuevas fuentes con logs y generación pública.
