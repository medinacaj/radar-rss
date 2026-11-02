# Estado del proyecto — Radar RSS

Actualizado el 1 de noviembre de 2026. Este archivo distingue código implementado de verificaciones que necesitan evidencia externa. La versión publicada y los resultados más recientes se consultan en GitHub Actions.

## Estado del código

- Web pública: https://medinacaj.github.io/radar-rss/; repositorio https://github.com/medinacaj/radar-rss y rama estable `main`.
- Migración de identidad: `scripts/site_config.py` mantiene nombre y URL canónicos compartidos por monitor, recuperación de noticias/agenda y RSS derivados. Se conservan los GUID RSS y las claves/formatos locales anteriores para no duplicar artículos ni perder preferencias. Las referencias de PR históricos redirigen al repositorio renombrado.
- Publicación: `.github/workflows/deploy.yml`, cada tres horas UTC (`17 */3 * * *`), con posibles demoras de GitHub. El navegador comprueba nuevas publicaciones cada 15 minutos.
- Catálogo: **311 suscripciones en ocho carpetas**. Se conservan los 276 registros previos y se añaden 35 canales de cobertura mundial: diez ámbitos regionales, doce temáticos y portales/agencias, incluyendo RSS nativo de MIT en español. Nuevos canales en Internacionales/Latinoamérica y uno en Tecnología; sin carpetas adicionales. Concepción 33 y Monagas 8 intactos. [Informe y evidencia](fuentes-cobertura-mundial-2026-10-28.md); observaciones RSS no equivalen a hechos verificados ni cobertura exhaustiva.
- Noticias: archivo de hasta 5000 entradas y 45 días, listado paginado de 36 por defecto. Los contadores completan el archivo en segundo plano, respetan filtros/lectura y anuncian carga o total no disponible si no pueden verificarlo. Hasta tres descargas históricas simultáneas, canceladas al fallar o cambiar generación.
- Agenda: recopilación independiente desde diez RSS y doce fuentes oficiales directas activas (HTML/JSON-LD/ICS/Tribe), horizonte de 90 días y fecha local de la actividad. Lista/calendario, filtros propios, guardadas locales, compartir y descarga ICS. Conserva actividades vigentes hasta acabar su último día, separa anuncios pendientes y excluye cancelados de próximos eventos. No deduce la fecha de actividad de la publicación. No garantiza cobertura exhaustiva.
- Interfaz: lector moderno aprobado, con azul como acento, superficies neutras y marca visible **Radar RSS**. Temas claro/oscuro, logo e iconos de instalación/social renovados, cabecera compacta y navegación lateral. Tarjetas sin desplazamiento al interactuar ni entradas escalonadas; indicadores breves, foco visible, movimiento reducido y colores forzados. El tamaño normal de los titulares coincide con el control de preferencias; texto grande sigue escalando la lectura. Se conservan Inicio, Noticias, Agenda, Resumen, filtros, columnas, lector y configuración. Implementado y validado localmente en la rama de trabajo; publicación no verificada.
- Lectura y respaldo: filtros visibles y plegables en móvil, navegación anterior/siguiente en el lector, regreso al contexto, Deshacer lectura masiva y aviso de publicación nueva bajo demanda. Guardadas, marcas, búsquedas y preferencias locales, incluidas actividades y vista de agenda; respaldo v3 compatible con v2. Las marcas masivas globales/de carpeta esperan el archivo completo y no se aplican si falta metadata válida o falla su verificación.
- Recuperación: Pages y caché se comparan por instantes UTC; fechas inválidas o sin zona no validan un respaldo. Si no hay copia verificable se detiene la recuperación. Artefactos con retención limitada, sin garantía de almacenamiento permanente.
- Privacidad: preferencias sólo en este navegador, sin cuentas, sincronización ni analítica central.

## Evidencia publicada y regresiones

- Configuración/fuentes: [gestor y portabilidad](gestion-fuentes-2026-10-28.md) documenta enlaces RSS/web visibles, búsqueda por URL/carpeta, filtros de estado/tipo/visibilidad, identidad por ID, OPML con organización personal, CSV completo e importación OPML con previa. Se corrigen conteos por carpeta, recorte de más de160 miembros al recargar y reinicio del modo ligero; catálogo311/8 intacto. Las fuentes desconocidas de un OPML quedan en un informe para su posterior incorporación pública; no hay altas remotas desde el navegador.

- PR89: auditoría, respaldo Concepción, navegación y personalización; PR90: eliminación de carpeta cultural independiente y selección en español.
- PR91: separación de noticias/agenda de 90 días y preservación de actividades independiente del límite de noticias.
- PR93: contadores reales, estados de error/reintento y cambio de generación; publicación verificada sobre `ebd1b157169e9189553bdb4ddd9a1a0c17d8dd23`.
- Referencias: [PR publicados](https://github.com/medinacaj/radar-rss/pulls?q=is%3Apr+is%3Amerged), [Actions](https://github.com/medinacaj/radar-rss/actions) e [incidencias abiertas](https://github.com/medinacaj/radar-rss/issues).
- Calidad: suite Python/Node sin red real. Pruebas de navegador con fixtures RSS y HTTPS local en Chromium, Firefox y WebKit, siete anchos de 320–1440 px. Las nuevas regresiones de lectura masiva y recuperación acompañan el código; sus resultados de CI constan en cada PR.
- Verificador público: contrasta la generación esperada del build y valida datos/noticias/agenda. La anotación «Publicación verificada» informa cantidades observadas sin inventar artículos ni actividades.

## Revisión de propuestas anteriores

| Referencia | Situación en este código |
|---|---|
| PR76 | Se recupera la corrección de cronología y se añaden regresiones de offsets, equivalencias, fechas inválidas y fallo de red. |
| PR92 | Encabezado OPML corregido a 221 fuentes/ocho carpetas; cuerpo, fuentes y URL conservados. |
| PR77 | Contadores resueltos por PR93. No se adoptan de esa rama los cambios a 9000 noticias/90 días ni el contador global que ignora filtros. |
| PR78 | Capacidades de filtros, lector, Deshacer y publicación bajo demanda adaptadas al diseño actual, preservando los contadores/archivo seguro de PR93–94. |
| PR88 | Capacidades de recolección oficial y calendario adaptadas a una única agenda de 90 días, conservando Monagas. No se importan snapshots/semillas antiguos ni una segunda aplicación. Catálogo directo con 12 fuentes activas y 32 candidatas deshabilitadas con motivo. |
| Referencia PR96 de la solicitud original | Al consultarla antes del rediseño devolvía404. No se importó código de una referencia inexistente; los PR creados posteriormente se identifican por su título y commit. |

## Verificaciones pendientes y límites

- [Issue #31](https://github.com/medinacaj/radar-rss/issues/31): pruebas físicas Safari/iPhone con VoiceOver, Android con TalkBack, tabletas, teclado, zoom y orientación. WebKit automatizado no sustituye esos dispositivos; no se declara realizado ese trabajo.
- [Issue #32](https://github.com/medinacaj/radar-rss/issues/32): curación manual de coincidencias de titulares, enlaces, fechas y atribución. Los informes son heurísticos; no se retiran fuentes ni se cambia el deduplicador automáticamente.
- Disponibilidad: `sources/reliable-expansion-verification.json` registra las23 altas y revalida los diez canales de `sources/discovery-verification.json`, conservado como historia del 24 de octubre. Son respuestas/fechas puntuales del RSS, sin comprobar todos los hechos ni garantizar disponibilidad futura. El Faro sigue pendiente por la consulta ensayada. Concepción conserva su evidencia del 24 de octubre en `sources/concepcion-verification.json`.
- Respaldos durables externos y sincronización entre dispositivos siguen fuera de la arquitectura estática. Caché y artefactos caducan; el archivo público no es permanente.
- La inclusión de una fuente, un HTTP correcto o una prueba automatizada no certifica licencias, derechos de reproducción ni cumplimiento legal. Se mantienen atribución, extractos y enlaces originales.

## Fuente de verdad

GitHub Issues/PR/Actions contienen incidencias, diffs y evidencia de integración. `docs/decisions.md` recoge decisiones duraderas; los planes de `docs/superpowers/` explican cambios acotados, sin sustituir la evidencia de CI o de dispositivos reales.
