# Visual comfort implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement task-by-task.

**Goal:** Aplicar las seis mejoras autorizadas y abrir titulares directamente en la web original.
**Architecture:** Reutilizar JS/CSS estático, controles y almacenamiento existentes. Separar visitar medio de comparar noticias, sin cambiar el modelo de contenido.
**Tech Stack:** HTML, CSS, JavaScript, Node y Playwright con fixtures.
**Spec:** docs/superpowers/specs/2026-11-10-visual-comfort.md

## Global constraints
Sin expansión de titulares; enlaces originales directos; conservar preferencias y atribución; botones44px; sin servicios/dependencias nuevos; no modificar deploy.yml; una rama/PR, autorización vigente de fusión/publicación.

## Review focus
Enlace retirado antes de navegación nativa; clic central/modificadores/pestaña actual; controles extraviados al redimensionar; diálogo/foco en cambios de ruta; letra grande y almacenamiento importado con Presentación cerrada.

## Task 1: Enlaces originales
Files: web/app.js, features.js, editorial-ux.js; tests/test_article_visits.cjs; browser_tests/visual_comfort.py.
- [x] Test RED: visita segura marca el grupo sin render síncrono, respeta enlaces y preferencias; URL insegura no navega.
- [x] Separar visitArticle de openArticleReader. Extender markRead/envolturas con opción render:false para persistir antes de navegación y aplazar redibujo. Enlazar titulares/imágenes/radar/historia con visita; mantener comparar explícito.
- [x] Test GREEN Node y navegador (popup, misma pestaña, teclado/modificadores).

## Task 2: Controles y tarjetas
Files: web/feed-ux.js, experience.js/css, editorial-ux.js/css; tests/test_feed_ux.cjs; browser_tests/visual_comfort.py.
- [x] Test RED: Presentación agrupa perfil/columnas/tamaño; filtros diálogo móvil con foco/Escape/restauración; fuente visible una vez, título leído con contraste, menor espacio y sin desbordamiento.
- [x] Crear details Presentación reutilizando display-controls, selector de tamaño que acciona el ajuste existente, diálogo inferior con campos reutilizados. Actualizar colocación del tipo editorial. CSS compacto, estado Leída y superficies discretas.
- [x] Test GREEN a320/390/768/1440/1842, claro/oscuro, importación/reset y lector de comparación.

## Task 3: Integración y publicación
Files: web/index.html/sw.js, browser_tests existentes afectados por contratos anteriores, workflows de pruebas pertinentes.
- [x] Actualizar expectativas: títulos abren medio; acceso al lector solo explícito comparar; controles de presentación requieren abrir grupo.
- [x] Versionar assets/cache; Python/Node/sintaxis y navegador relevantes; capturas y revisión independiente final. Corregir hallazgos importantes con regresión.
- [ ] Commit/PR; esperar CI y fusionar contra SHA verificado; comprobar publicación.
