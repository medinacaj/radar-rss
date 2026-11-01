# Radar-RSS: identidad editorial completa

Se renueva toda la identidad de **Radar-RSS** con la dirección elegida por el usuario: petróleo, turquesa y coral. El cambio abarca logo, iconos, tarjeta social, colores, jerarquía, navegación, tarjetas, botones, formularios, agenda, lector y configuración. La cabecera conserva un único logo de 24 píxeles; no se incorpora un banner grande ni otra barra superior.

| Tema | Fondo | Texto | Acción principal |
|---|---|---|---|
| Claro | `#f3f7f7` | `#183442` | `#146e7b` con texto blanco |
| Oscuro | `#111e29` | `#e7eff2` | `#7dd5ce` con texto petróleo |

Los textos largos permanecen neutros. El color identifica secciones, selección, estados y acciones; los bordes y sombras dan profundidad sin desplazar tarjetas al interactuar. El foco del teclado es visible, los controles principales tienen 44 píxeles y se respeta reducción de movimiento. El barrido del gráfico se activa al interactuar, evitando un movimiento continuo en reposo.

## Logo y activos

El símbolo RSS/radar y la tarjeta social se generaron para el proyecto mediante `image_gen`. Los maestros se conservan en `assets/brand/`. Los tamaños web y de instalación se exportan con `browser_tests/export_radar_brand.py`, usando el renderer del navegador sin modificar el dibujo. No se añaden dependencias a producción ni se afirma exclusividad jurídica de la marca.

Los activos activos usan el prefijo `radar-rss-`: marca de 128 píxeles mostrada a 24, favicon de 64, iconos de 192 y 512, maskable de 512 con área segura, Apple de 180 y tarjeta social de 1200×630. Los originales anteriores de RSS y Notisonda se conservan como históricos. HTML, manifest, iconos, metadatos y caché apuntan a la nueva identidad; el manifest se referencia con versión para evitar una copia HTTP anterior.

## Compatibilidad y publicación

La ruta verificada es **https://medinacaj.github.io/radar-rss/**. GitHub confirma `medinacaj/radar-rss`; página y metadatos responden 200, mientras `/notisonda/` devuelve 404. La recuperación y el monitor usan la ruta vigente mediante `scripts/site_config.py`; la comprobación real de salud pasó. Esto no implica que el código propuesto ya esté publicado.

Se conservan las claves de almacenamiento, respaldos v2/v3 y formato `radar-rss-settings-v3`, GUID de noticias y UID `@agenda.radar-rss`. El catálogo JSON sigue idéntico byte a byte: 311 fuentes en ocho carpetas. Se mantienen rutas, navegación, filtros, estados de lectura y guardados. Los PR #120 y #121 de fuentes continúan separados y aplazados.

La caché se renueva a `radar-rss-v57`, manteniendo migración de ambas marcas, lectura offline y exigencia de red al comprobar novedades manualmente. La nueva versión solo se activa después de descargar todos los recursos y datos necesarios: si una descarga falla, la versión anterior sigue funcionando con su caché. Los accesos instalados que apuntan a la ruta anterior deberán abrir la dirección vigente; este cambio no puede crear una redirección desde el proyecto anterior de GitHub Pages.

## Comprobaciones

- 292 pruebas Python y auditoría OPML sin problemas; todos los activos históricos protegidos conservan sus hashes.
- 43 regresiones de interfaz, siete tamaños responsivos y cuatro tamaños de lectura; pruebas de controles, fuentes y compatibilidad de respaldos.
- Regresión de contraste en el lector: el texto «en otra pestaña» heredaba blanco sobre una acción clara. Se observó el fallo, se corrigió en su regla original y se comprobó tanto en reposo como al pasar el puntero, en ambos temas.
- Auditoría ampliada: 2.570 muestras de texto, mínimo observado 4,52:1 y ninguna por debajo de 4,5:1. Incluye categorías y tres carpetas adicionales previstas, sin añadirlas al catálogo.
- Actualización desde los scripts exactos anteriores e importación de su respaldo original de Notisonda aprobadas; se conservan lectura, guardados, fuentes ocultas y carpetas personales.
- La revisión independiente detectó un riesgo al activar una caché incompleta. Se reprodujo en un navegador real y se corrigió con instalación atómica. La regresión comprueba fallos HTTP en el código y de conexión en las noticias, lectura posterior sin red y actualización correcta al recuperar la conexión.
- Vista con la instantánea pública completa de 5.000 artículos y 311 fuentes: Inicio, Noticias, Resumen, Agenda, lector y configuración, en ambos temas y anchos de 320, 390, 768, 1440 y 2560 píxeles, sin desbordamiento.

Las imágenes de noticias externas estuvieron limitadas por la política de red de la herramienta de pruebas. Se comprobó la alternativa sin fotografía, sin inventar imágenes de noticias. Las capturas y métricas son evidencia de las condiciones probadas, no una garantía de ausencia de fallos o de comodidad visual idéntica para todas las personas.

La publicación continúa pendiente por indicación del usuario. La descripción del PR documenta revisión y CI del commit final.
