# Radar RSS: lector moderno

Implementa el diseño aprobado en `docs/superpowers/specs/2026-11-01-radar-rss-modern-reader-design.md`.

## Cambios

- Nombre visible exacto **Radar RSS** en cabecera, metadatos, aplicación instalada, resúmenes, ayuda y OPML personal; prefijos técnicos y rutas conservados.
- Nuevo símbolo RSS azul, iconos de instalación y tarjeta social. Los maestros anteriores se archivan sin destruir originales históricos.
- Temas claro/oscuro con superficies neutras, bordes discretos y azul; sombras reducidas y hover sin desplazar tarjetas. Se elimina la entrada escalonada y el movimiento decorativo; se mantienen indicadores funcionales y movimiento reducido.
- El control del tamaño normal de títulos corresponde a los píxeles efectivos; texto grande conserva su escala explícita.
- Caché `radar-rss-v59`, instalación atómica y limpieza de cachés antiguas conservadas. No se modifican claves de preferencias, respaldos, catálogo, ingesta, datos ni workflows.
- Documentación vigente y enlaces del proyecto corregidos. Los planes históricos y las referencias necesarias para migrar versiones anteriores se conservan como evidencia y compatibilidad.

## Evidencia local

- 299 pruebas Python: aprobadas.
- Sintaxis de todos los JS de `web/`, todas las suites `tests/*.cjs`: aprobadas.
- Auditoría OPML: 311 fuentes, ocho carpetas, cero problemas.
- Chromium responsive: aprobado en 320, 375, 390, 430, 768, 1024 y 1440 px.
- 45 regresiones de temas/lectura/fuentes/respaldos/caché en Chromium: aprobadas, incluida la nueva prueba de contraste de Guardar carpeta en claro y oscuro.
- Revisión independiente: detectó texto blanco con contraste insuficiente en Guardar carpeta oscuro. Reproducido con prueba real (1,88:1); corregido usando los tokens de acción para ambos temas.

Las capturas en `test-results/modern-reader/` corresponden a la aplicación con fixtures locales, no a noticias publicadas. Las imágenes remotas se bloquean en estas pruebas. Firefox/WebKit y dispositivos físicos no se ejecutaron en esta tarea. No se afirma validación de producción ni publicación; se entrega en rama para revisión humana.
