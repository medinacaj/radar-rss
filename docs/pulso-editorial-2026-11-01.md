# Pulso editorial · Radar RSS

Dirección elegida por el usuario: opción 1 del tablero visual. Sustituye la interfaz de tarjetas azules por papel cálido, negro y naranja, marca condensada, titular «Lo que pasa. Ahora.», líneas editoriales y noticias numeradas. La composición mantiene las noticias cronológicas y usa dos columnas a partir de 1100 px.

La navegación principal es horizontal. El lateral de fuentes empieza cerrado si no existe una preferencia explícita; quien eligió mantenerlo abierto o ajustó su ancho conserva esa elección. El botón de menú y «Fuentes y carpetas» dan acceso al panel. Agenda, Resumen, filtros, guardados y lector conservan sus funciones. La tipografía display Anton se sirve localmente y se distribuye con su licencia OFL, incluida en `web/fonts/Anton-OFL.txt`; no se añade un servicio externo al navegador.

Se renuevan logo, iconos PNG y tarjeta social. Los maestros azules anteriores se archivan. Caché `radar-rss-v62`, incluyendo la fuente para uso sin conexión, con instalación atómica y migración conservadas. No se modifica catálogo, recopilación ni programación de 15 minutos. El sitio no promete tiempo real.

## Verificaciones

- 304 pruebas Python y todas las suites Node/sintaxis JavaScript aprobadas.
- 45 regresiones generales de Chromium aprobadas, incluyendo contraste, almacenamiento, lectura y migración offline.
- Siete anchos responsive (320–1440 px) aprobados.
- Revisión independiente: se corrigió el foco de teclado al abrir Fuentes y carpetas en escritorio; test RED→GREEN y estado ARIA sincronizado.
- Seis pruebas de portada, incluida navegación horizontal, apertura/persistencia del lateral y marca visible en móvil.
- Catálogo conservado: 311 fuentes en ocho carpetas, cero problemas.

Las capturas de `test-results/ahora/` usan titulares ilustrativos. No se ejecutó publicación remota, Firefox/WebKit ni pruebas físicas de dispositivos. El cambio está en rama para revisión humana.
