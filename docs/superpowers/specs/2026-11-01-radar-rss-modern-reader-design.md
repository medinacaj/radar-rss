# Radar RSS: identidad y lector moderno

## Intención y alcance

El propietario confirma el nombre **Radar RSS** y pide actualizar referencias, sitio, logos, animaciones y estilo. Rechaza el aspecto actual. Se propone una aplicación de lectura limpia, azul como acento y movimiento discreto. El «sí» del usuario permite avanzar con esta propuesta; todavía no aprueba este documento ni un despliegue.

El checkout ya utiliza Radar-RSS y la ruta `/radar-rss/` en la aplicación. `docs/project-status.md` conserva identidad y enlaces antiguos. No se ha verificado la publicación remota en esta revisión.

## Enfoques considerados

- **Aplicación de lectura (dirección propuesta):** navegación lateral compacta, listado claro y acciones de lectura accesibles. Favorece explorar muchas fuentes; ofrece menos protagonismo a una sola noticia.
- **Periódico digital:** destacado y composición de portada más grandes. Favorece la presentación editorial, pero ocupa más espacio antes del archivo de noticias.

Se continúa con aplicación de lectura interpretando el «sí» a la propuesta previa; el usuario puede corregir esta interpretación al revisar la maqueta.

## Resultado visual

Nombre visible exacto **Radar RSS**, sin guion. Mantener `radar-rss` en rutas, nombres técnicos y claves compatibles. Cabecera compacta con búsqueda y marca RSS azul; barra lateral clara con selección azul suave. Contenido sobre fondo gris frío muy tenue, superficies blancas y bordes neutros. Oscuro equivalente con fondo pizarra, superficies elevadas y azul claro accesible. Sin degradados ornamentales, marco multicolor ni sombras pesadas.

Sistema tipográfico local de la plataforma, títulos de lectura a tamaño configurable y texto secundario legible. Espaciado coherente de 4/8/12/16/24/32 píxeles; controles táctiles de al menos 44 px. Foco visible y contraste comprobado por tema. Las fotos de noticias siguen procediendo de la fuente; no se inventan fotografías ni se añaden imágenes externas decorativas.

Inicio conserva destacado, titulares, cobertura y tendencias con menor peso ornamental. Noticias permite lista y cuadrícula existentes. Agenda mantiene lista/calendario, fechas y exportación; Resumen y lector usan el mismo sistema. Configuración conserva todas sus opciones. No se crea una segunda navegación ni se eliminan funciones para simplificar la maqueta.

En móvil, lateral plegable, cabecera compacta, controles de filtro existentes y una columna de lectura. Se preservan opciones de columnas y tamaño de texto; no imponer una cuadrícula rígida. Validar 320, 390, 768 y 1440 px, zoom y texto grande.

## Identidad y referencias

Un símbolo sencillo que combine punto y ondas RSS en azul debe funcionar a 24 px. Preparar primero el maestro y aprobar visualmente sus derivados: favicon, marca, PNG 192/512, maskable con área segura, Apple 180 y tarjeta social 1200×630. Mantener prefijo `radar-rss-` y herramientas de exportación existentes. La maqueta usa un símbolo provisional en HTML/CSS y no constituye un logo final.

Actualizar textos visibles, title, descripción, Open Graph, Twitter, manifest, alt/aria, ayuda, resúmenes compartidos, nombres de descargas y `SITE_NAME` a Radar RSS. Actualizar documentación vigente y enlaces canónicos a `/radar-rss/` y `medinacaj/radar-rss`, sin afirmar que se verificó la web remota.

Preservar el historial documental con una nota de identidad vigente en lugar de reescribir hechos pasados. Los identificadores `notisonda-` solo permanecen cuando son necesarios para limpiar/migrar cachés anteriores o probar compatibilidad. Los activos históricos quedan archivados fuera de referencias activas; no borrar maestros ni romper pruebas que los preservan. Revisar referencias por propósito, nunca reemplazar texto a ciegas.

## Movimiento

Transiciones de color/opacidad de 120–180 ms. Evitar entrada escalonada, traslaciones y animaciones permanentes del radar, logos o tarjetas. Mantener indicadores funcionales de carga y novedades, con alternativa estática cuando `prefers-reduced-motion: reduce`. No ocultar contenido detrás de una animación.

## Implementación y límites

Mantener frontend estático y herramientas actuales, sin framework, fuentes remotas ni nuevas dependencias de producción. Consolidar reglas activas del tema al modificarlo; evitar agregar otra capa completa de overrides al final de `dimension.css`. Se deja al implementador dividir el CSS en secciones manteniendo selectores que usa el comportamiento JS y las pruebas. No cambiar ingesta, catálogo, datos publicados, workflows ni límites de retención.

Archivos principales: `web/index.html`, tema activo y estilos auxiliares afectados, manifest y service worker, maestros/derivados de marca, `scripts/site_config.py`, textos JS de compartir/exportar, documentación vigente y pruebas pertinentes. Aumentar versión de caché y referencias de activos; mantener instalación atómica y limpieza compatible. No tocar claves localStorage, esquema de respaldo v2/v3, IDs, GUID ni UID de agenda.

## Criterios de aceptación y evidencia

- Inventario de referencias activas: sin nombre anterior visible, identidad exacta Radar RSS y rutas canónicas coherentes. No borrar compatibilidad técnica.
- Temas claro/oscuro, foco, texto grande, columnas, lector, ajustes, navegación y movimiento reducido validados en navegador; sin desbordamiento a 320–1440 px.
- Logo coherente entre cabecera, instalación y tarjeta social; dimensiones y área segura verificadas.
- Suite Python, sintaxis y suites JS pertinentes, prueba de migración de caché y prueba funcional en Chromium. Firefox/WebKit se reportan por separado según ejecución real.
- Resolver la discrepancia existente entre tamaño de título esperado de 14 px y CSS calculado de 16.1 px conforme al contrato elegido: el control debe indicar el tamaño efectivo normal del título; el modo texto grande puede escalarlo explícitamente. No desactivar assertions.
- Conservar estados de lectura, guardados, fuentes ocultas, carpetas personales y respaldos compatibles; verificar actualización y uso offline.
- Revisar diff; dejar cambios en rama para revisión humana. No publicar ni fusionar automáticamente.

## Revisión y entregables

La maqueta `/workspace/design-radar-rss/reader.html` usa titulares ilustrativos y datos inventados de demostración, no una generación real de noticias. Permite alternar tema y ver adaptación móvil; no sustituye la aplicación y sus controles de noticias no se presentan como funcionales.

Tras aprobar esta propuesta: elaborar plan de implementación, realizar cambios, verificar y entregar capturas y resultados. Los matices de espaciado, color secundario y organización interna del CSS quedan a criterio del implementador dentro de los criterios anteriores.

No se añaden servicios ni tratamiento de datos. Se preservan atribución y enlaces de medios, preferencias locales y ausencia de analítica. El alcance es visual y de identidad, sin afirmar exclusividad legal de marca ni cumplimiento jurídico.
