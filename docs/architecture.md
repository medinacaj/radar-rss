# Arquitectura — Radar RSS

El contenido se extrae de `sources/feeds.opml` por `scripts/collect.py`, se normaliza/agrupa y se publica como JSON estático en `web/data/`. La aplicación `web/` se sirve desde GitHub Pages. El workflow `deploy.yml` recopila noticias aproximadamente cada hora (:17 UTC, sujeto a demoras de GitHub) y publica el sitio. Las pruebas Python usan `unittest`; las comprobaciones de UI incluyen Node y archivos `.cjs`. **No ejecutar recolección en la CI de PR:** depende de red externa y puede activar fuentes reales.

## Contratos a preservar
- No romper rutas públicas ni cambios de formato de datos sin actualizar consumidores y pruebas.
- Separar código de aplicación, datos, pruebas y automatización.
- Los cambios en deploy/monitorización deben verificarse con especial cuidado.
- Consultar `README.md` y el código actual como fuentes más recientes; este mapa es orientativo, no un inventario exhaustivo.

## Agenda y lectura (octubre 2026)

`collect_events.py` reúne RSS de `sources/events.json` y, con `--direct-config sources/events-direct.json`, calendarios oficiales mediante `event_sources.py`. Los hechos explícitos se normalizan y fusionan por `events.py` en un único `events.json` v1; ICS conserva UID y TZID y reduce el final exclusivo al último día local ocupado. La publicación usa la misma generación de noticias. La caché conserva futuras actividades aunque la fuente falle; `agenda.js` valida generación y datos antes de filtrar el horizonte de 90 días. Los opcionales de localidad/tipo/precio no invalidan documentos antiguos. No se importa el stack, workflow ni snapshots de PR88.

`feed-ux.js` y `reader-ux.js` se cargan tras los módulos actuales y extienden sus filtros y lector. La comprobación automática de `app.js` prepara nuevas publicaciones sin sustituir el estado hasta aplicar; el botón manual las aplica y anuncia el resultado. Ambas validan un lote coherente. La comprobación y la carga inicial tienen un tiempo máximo de 15 segundos; las peticiones manuales usan `no-store` para que el service worker no confunda una copia sin conexión con una comprobación reciente. Al aplicar cancela el histórico anterior y conserva su exclusión hasta que se asienten los trabajadores. Los contadores requieren archivo y manifiesto completos. El respaldo v3 incluye el módulo validado `agendaPreferences`; su ausencia en respaldos antiguos conserva los datos locales. Ningún guardado añade servicios ni sincronización.

## Sistema visual Dimension

`dimension.css` es la única capa activa de tema. Comparte tokens de claro marfil/oscuro grafito con acciones violeta y bordes discretos sobre superficies uniformes. El lateral sigue el tema elegido y los botones usan esquinas suaves, selección y foco visibles. Hover/foco conservan feedback discreto sin trasladar tarjetas; solo el icono Actualizar gira mientras hay una comprobación activa. El barrido continuo del mapa está desactivado y reduced-motion desactiva animaciones y transiciones. `font-large` amplía contenido de las cuatro rutas/lector. Las columnas Auto se resuelven según el contenedor (mínimo280px,320px con texto grande); el fallback de estado, restablecer y respaldos sin elección es `auto`, sin reemplazar valores válidos2–6. Controles de artículos44px y entradas móviles16px.

La única marca visible (`brandHome`) usa `favicon.svg` de24px con el símbolo RSS en la barra superior. No hay panel de presentación ni marca duplicada en el lateral; H1 de Inicio conserva su nombre para lectores de pantalla. `radar-logo.png` es la marca original generada, sin transformación, para instalación/PWA; `icon-maskable.svg` mantiene el símbolo en el área segura sobre un fondo opaco completo. `svgIcon()` mantiene su API con ocho símbolos de categoría y un icono propio para carpetas manuales. `styles.css` y las hojas de módulos conservan estructura/controles, y sus colores se resuelven con tokens del tema. La evolución histórica de Index y el shell SWv44 retiró siete referencias visuales antiguas; la caché actual es `radar-rss-v82`. `?preview=` deja de conmutar estilos anteriores. `app.js` añade la ruta `#agenda` con una vista independiente; los contadores de biblioteca se asocian mediante `data-destination`, no por posición. `homepage.js` conserva un único destacado y un carrusel sin IDs repetidos, sin fotografías decorativas. Cobertura/tendencias tienen una única instancia visible en Inicio, con mapa opcional inicialmente cerrado en todos los tamaños. Se actualizan al entrar directamente en Inicio y al cambiar fuentes/preferencias; Resumen conserva sus resúmenes por carpeta. Las filas de cobertura exponen `data-article-id` para recuperar foco/posición en el lector existente. Si no hay tendencias ni temas seguidos, no se reserva una columna vacía.

## Estado verificado del 26-11-2026

Identidad canónica: `scripts/site_config.py`, Radar-RSS, https://medinacaj.github.io/radar-rss/. Interfaz app9.12.5/SW82, sin release global ni staging independiente comprobados. [Memoria vigente](MEMORIA_OPERATIVA.md).

`source_discovery.py` reutiliza un registro derivado o investiga cada 48 horas; `web/data/discovered-sources.json` conserva procedencia/estado. El OPML efectivo es temporal; no modifica las 443 fuentes curadas. `auto_sources.py` revalida cada ingesta mediante `safe_publisher.py`: HTTPS público, IP/DNS fijado, robots y límites. AUTO omite imágenes/OG. La primera búsqueda real fue indisponible; la interpretación RFC es trabajo pendiente de #184, no corrección desplegada.

Caché, recuperación validada desde Pages y artefactos de JSON públicos conservan historial/registro. Retención de respaldo hasta 90 días; no almacenamiento permanente. El artefacto Pages identifica el intento del build y el deploy consume su output; no se ensayó un reintento productivo durante el respaldo. Noticias/investigación comparten 5.000 entradas, ventanas 45/730 días y reserva académica hasta 200; agenda de 90 días independiente.

El monitor se ejecuta tras publicaciones y cada seis horas a :45 UTC. Siete feeds en error (umbral cinco) no demuestran caída completa. Cron configurado y una generación verificada no prueban frescura permanente.

### Seguridad, datos y entornos

XML/HTML/URLs de terceros son datos no confiables: conservar saneamiento, URL/host público, atribución y transporte acotado. Los JSON generados son públicos. LocalStorage guarda preferencias privadas sin cuentas ni sincronización; no subir exportaciones personales. Tokens/credenciales de Actions quedan fuera del respaldo. Variables por nombre y recuperación en memoria. Desarrollo usa fixtures; no se identificó staging. Este respaldo no cambia dependencias, proveedores, workflow, infraestructura ni datos.
