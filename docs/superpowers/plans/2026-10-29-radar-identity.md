# Radar-RSS — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans, ejecución nativa y una revisión final independiente.

**Goal:** Rediseñar toda la identidad de Radar-RSS con logo original, paleta editorial y componentes coherentes, manteniendo datos y publicación pendiente.
**Architecture:** Identidad central de scripts en `site_config.py`; nuevo sistema visual en el tema existente, logo generado e iconos y tarjeta social consistentes. Mantener formatos, IDs y navegación funcional; actualizar los recursos y caché activos.
**Tech Stack:** Python, JavaScript y activos estáticos existentes, sin dependencias nuevas.
**Spec:** `docs/superpowers/specs/2026-10-29-radar-identity-design.md`.

## Global Constraints

- Catálogo de 311 fuentes y ocho carpetas intacto; PR #120/#121 separados y sin fusionar/publicar.
- Nombre público Radar-RSS y URL observada `https://medinacaj.github.io/radar-rss/`.
- Conservar almacenamiento, formato de respaldo, GUID de noticias y UID de calendarios.
- Paleta editorial elegida por el usuario: petróleo, turquesa y coral; logo compacto original de radar/RSS, con iconos y tarjeta social concordantes.
- Mantener los activos anteriores como históricos; sustituir sus referencias activas por la nueva identidad.
- Lectura cómoda en ambos temas, contraste de texto mínimo 4,5:1, foco visible, controles principales de 44 píxeles y reducción de movimiento.
- No modificar workflows ni programación, retención o comportamiento de actualización.

## Review Focus

- URL de recuperación y monitor distinta de la marca visible, validada con respuestas reales.
- PWA, Apple y metadatos con PNG existentes de dimensiones declaradas correctas.
- Marca coherente en descargas, resúmenes, calendario y RSS sin cambiar identidades de datos.
- Cachés de ambas marcas migradas sin romper lectura offline ni actualización manual.
- Fuentes y preferencias intactas, con los PR de fuentes pendientes conservados.

### Task 1: Identidad y compatibilidad

**Files:** `scripts/site_config.py`, URL del proyecto en el User-Agent de `scripts/collect.py`, `web/index.html`, `manifest.webmanifest`, scripts con textos públicos, `web/sw.js`, SVG RSS recuperados bajo nombres nuevos, `README.md`, cabecera OPML; pruebas de publicación/activos, exportaciones y navegador pertinentes.
**Interfaces:** `SITE_NAME` cambia a Radar-RSS, `SITE_URL` a la ruta comprobada; esquemas, GUID y UID permanecen idénticos. El paso inicial recuperó los SVG históricos; la instrucción ampliada de la tarea 2 sustituye las referencias activas por nuevos PNG. No se sobrescriben los originales anteriores.

- [x] Actualizar pruebas de límites HTTP, identidad/PNG y exportaciones al resultado solicitado; observar fallos antes del cambio.
- [x] Actualizar identidad activa y enlaces de publicación sin reemplazar formatos ni IDs técnicos.
- [x] Verificar pruebas, caché, catálogo intacto, importación de respaldos antiguos y ambos temas en navegador.
- [ ] Revisión independiente, PR con CI del commit exacto; dejar publicación pendiente.

### Task 2: Identidad visual completa

**Files:** `web/dimension.css`, logo y derivados nuevos, `web/index.html`, `manifest.webmanifest`, `web/sw.js`, documentación y comprobaciones pertinentes de activos.
**Interfaces:** Los tokens del tema abastecen todo el lector; se mantienen selectores e IDs funcionales, variables de anchura/alineación, preferencias y rutas. Los metadatos e iconos apuntan a activos de la misma marca.

- [x] Generar un símbolo nuevo, pequeño y reconocible; preparar iconos y tarjeta social con nombres nuevos, conservando originales.
- [x] Renovar paleta y lenguaje de componentes: navegación, tarjetas, botones, formularios, agenda, lector y configuración.
- [x] Verificar contraste, foco, movimiento reducido, ambos temas y pantallas de 320–2560 píxeles con contenido real y preferencias conservadas.
- [x] Ejecutar suites pertinentes y una revisión final del alcance ampliado; corregir hallazgos importantes y actualizar el PR #123 alrededor del diseño final.
- [ ] Comprobar CI del commit exacto y mantenerlo en borrador, sin fusionar ni publicar.

Los últimos controles son puertas de cierre. Su evidencia definitiva se registra en la descripción y los checks del PR #123, para identificar el commit comprobado sin crear otro commit solo por modificar estas casillas.
