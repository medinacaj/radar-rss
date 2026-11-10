# Plan: experiencia de lectura Radar RSS

Spec: docs/superpowers/specs/2026-11-09-reading-experience.md

## Restricciones
JS estático y Python existentes; sin dependencias/servicios externos; conservar IDs, rutas, fuentes, preferencias y atribución. User ya autorizó aplicar y publicar. Una rama/PR para toda la tarea. Pruebas de red con fixtures.

## Tareas y archivos
1. Modelo e interfaz editorial (delegada): web/editorial-model.js, web/editorial-ux.js, web/editorial-ux.css; scripts/collect.py solo para conservar tipo editorial explícito; tests/test_editorial_model.cjs, tests/test_content_type.py y browser_tests/editorial_experience.py. Modelo exporta window.RadarEditorial: groupStories(items), contentType(item), selectDigest(items,now,limit=7), selectLocal(items,categories,now). API sin mutaciones, fuentes/fechas originales, agrupación conservadora. Interfaz usa applyFilters/dashboardEligible existentes y añade filtro de tipo, resumen y destacados. Consume opcionalmente RadarExperience.getPinnedDestinations(). Escribir tests, observar fallos, implementar y comprobar.
2. Experiencia y navegación (delegada): web/experience.js, web/experience.css y browser_tests/experience_regressions.py. Perfiles basados en state.layout/density/showImages/showSummaries preservan cardTitleSize; columnas efectivas sin alterar preferencia guardada, etiquetas visibles y filtros sticky; búsqueda/favoritos de carpetas y fuentes usando nodos existentes, almacenamiento defensivo y respaldo mediante RadarLibrary.registerBackupModule. Exporta window.RadarExperience.getPinnedDestinations(): array de destinos de categoría o carpeta. Probar primero con fixtures, teclado, móvil, respaldos y retorno del lector.
3. Rendimiento e integración (principal): web/app.js, web/index.html, web/sw.js y pruebas relevantes de estado/cuentas. Mantener render inicial, limitar trabajo repetido, progreso/cancelación del archivo y navegación responsiva; conectar modelos antes de app.js, experience.js y editorial-ux.js tras reader-ux.js; estilos al final, versionado y caché. No tocar deploy.yml. Probar archivo lento/incompatible, reintento, refresh simultáneo y contadores completos.
4. Revisión del conjunto, regresiones, capturas y publicación: ejecutar Python y Node, recorridos de lectura/columna/móvil/editorial con fixtures; revisar datos/preferencias y diffs; crear PR, fusionar y verificar deploy según autorización.

## Revisión de riesgos
- Una noticia agrupada no debe mezclar hechos con números/fechas distintos; pruebas de falsos positivos.
- Filtro de tipo desconocido no debe inventar clasificación ni ocultar noticias por defecto.
- Intereses/fuentes ocultas se respetan en resumen y destacados; probar selección vacía.
- Favoritos corruptos/desconocidos no deben bloquear inicio; probar respaldo antiguo y restablecer.
- Archivo lento y refresco concurrente no deben bloquear lectura ni aplicar una generación antigua; conservar semántica de contadores.

## Interfaces compartidas
Root modifica app/index/sw; cada agente escribe únicamente sus módulos y pruebas propios. Las envolturas de render/applyFilters se encadenan sin sustituir estado. Orden de carga: editorial-model → app y módulos actuales → experience → editorial-ux. Nuevos estilos: experience.css y editorial-ux.css. Root integra registros de backup sin sobrescribir módulos existentes. No se ejecutan suites pesadas de navegador en paralelo en la máquina de 2 CPU.
