# Comodidad visual y enlaces originales — 10 de noviembre de 2026

Solicitud: aplicar seis mejoras visuales aprobadas y excluir la expansión de titulares. Pulsar un titular o imagen debe abrir directamente la web del medio, como preferencia expresa registrada también en AGENTS.md.

## Resultado
- Presentación reúne perfil, columnas y tamaño del titular en un desplegable. Reutiliza los controles/preferencias existentes y sincroniza el ajuste original de tamaño.
- Tarjetas con menos relleno y altura según contenido, alineadas por la parte superior de la fila. Las letras elegidas y los botones de44px se conservan. El medio aparece una vez visualmente y una vez en el árbol de accesibilidad.
- Noticias leídas con texto de igual contraste y marca «Leída»; sin depender únicamente del color. Se suavizan las sombras y se reservan bordes destacados para interacción y foco.
- Filtros móviles en un diálogo inferior nativo, con campos desplazables, botones de cierre/retorno, Escape y foco contenido. Al cerrar se vuelve al botón Filtros; al redimensionar se reutilizan los mismos nodos en escritorio.
- Títulos, imágenes, resumen y cobertura enlazan a la URL original. Se respeta la preferencia de pestaña y la navegación nativa con Enter/Ctrl/Cmd/clic central. Las marcas se persisten antes de navegar y el redibujo posterior mantiene foco y posición; «Comparar medios» es una acción independiente.

## Verificación
Python316, Node14 y sintaxis frontend. Nuevas pruebas Chromium a320,390,768,1440 y1842px, temas claro/oscuro, Presentación, tamaño elegido, filtros/resize, URL original en nueva/misma pestaña, modificadores, comparación, retorno del foco, altura real de tarjetas y contraste. Se mantienen las regresiones de lectura, editorial, archivo5000, respaldo y responsividad adaptadas a enlaces originales.

Selector de fuentes: conserva el mismo botón y el foco durante redibujos del menú; regresión forzada render→Enter verificada a320–1842px tras detectar una carrera en CI.

Revisión independiente: corregir la identificación accesible del medio, ocultando solo visualmente el texto repetido del pie cuando la cabecera visible tiene aria-hidden. Regresión de snapshot accesible antes/después.

## Controles y límites
No se añaden dependencias, proveedores, telemetría ni preferencias de almacenamiento nuevas. No cambian fuentes, datos RSS ni workflow de despliegue. Se conservan URLs HTTP(S), atribución y extractos sin reescritura. El diseño se basa en el producto y las capturas de referencia previas y en las guías Refero de jerarquía, ritmo y accesibilidad; no se cambia la paleta.

Riesgo → control → evidencia → responsable: perder navegación/foco → enlaces nativos y redibujo diferido → prueba de URL/pestaña/foco; controles extraviados → conservar nodos e IDs → prueba de resize; ocultar fuente a tecnologías de asistencia → ocultación solo visual → snapshot accesible; contraste insuficiente → tokens de acción claro/oscuro → ratio>=4,5. Mantenedores responsables de revisar futuras regresiones. No se certifican licencias ni cumplimiento jurídico de contenidos de terceros (países de fuentes/lectores, incluidos Chile y Venezuela); continúan los controles existentes. Estas pruebas no son una certificación de dispositivos físicos ni de carga concurrente pública.
