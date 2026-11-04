# Fuentes de Monagas — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans, implementación nativa y una revisión final independiente.

**Goal:** Completar la carpeta local con fuentes verificadas de los seis medios solicitados, conservando catálogo y preferencias.
**Architecture:** OPML como origen y `parse_opml` para generar el catálogo; evidencia fechada y reporte por medio. Reutilizar navegación dinámica y deduplicación actuales.
**Tech Stack:** Python y aplicación estática existente, sin dependencias nuevas.
**Spec:** `docs/superpowers/specs/2026-10-29-monagas-feeds-design.md`.

## Global Constraints

- Preservar los 311 registros originales y las ocho carpetas; no tocar PR #120.
- RSS nativos primero; RADAR explícito solo si es verificable y no equivalente a uno existente.
- Exigir artículos locales recientes; una sección nacional genérica de Oriente no basta.
- Sin cambios en UI, retención de 45 días, workflows o preferencias; no fusionar ni publicar todavía.

## Review Focus

- RSS nativo válido y pertinente frente a HTML, comentarios o páginas estáticas.
- Bloqueo de red diferenciado de ausencia de RSS.
- Canales nacionales sin noticias de otros estados en la carpeta local.
- URLs equivalentes y conservación completa del catálogo previo.
- Carpetas y preferencias conservadas sin incorporar PR #120.

### Task 1: Verificación e integración

**Files:** `sources/feeds.opml`, `web/data/sources.json`, `sources/monagas-verification.json`, `docs/fuentes-monagas-2026-10-29.md`, pruebas pertinentes del catálogo.
**Interfaces:** `parse_opml(path)` conserva ID SHA256 de URL; la matriz relaciona cada medio, feed anterior/nuevo, proveedor, estado y observaciones.

- [x] Verificar los seis portales y las suscripciones previas, registrar respuestas y limitaciones de acceso.
- [x] Registrar el hash de los 311 originales y comprobar integridad del catálogo con las altas seleccionadas.
- [x] Añadir solo canales verificados y regenerar el catálogo, conservar los originales sin moverlos.
- [x] Ejecutar auditoría OPML, pruebas pertinentes y comprobación del catálogo en navegador.
- [ ] Revisión final independiente, PR separado y CI del commit exacto; dejarlo pendiente sin publicar.
