# Experiencia de lectura — 10 de noviembre de 2026

Solicitud: aplicar las mejoras técnicas, de contenido y de experiencia visual autorizadas. Diseño y alcance: [spec](superpowers/specs/2026-11-09-reading-experience.md) y [plan](superpowers/plans/2026-11-09-reading-experience.md).

## Comportamiento entregado

- Resumen con hasta siete historias de las últimas 24 horas (48 si hay pocas), diversidad de carpetas, fuente, hora y cobertura. Escuchar, copiar y compartir utilizan la misma selección. Navegación anterior/siguiente conserva su secuencia.
- Duplicados: título completo equivalente o URL original compartida, ventana de 24 horas y atribución conservada. Cifras, fechas, negación, lugares y acciones diferentes impiden fusionar por título. Marcar una historia y Deshacer gestionan los miembros del grupo con revisiones por ID.
- Tipo editorial solo desde metadata explícita del editor: noticia, opinión, análisis o comunicado. Sin evidencia queda sin clasificar y permanece visible por defecto; el filtro temporal se puede retirar. No se reescriben noticias.
- «Cerca de ti» usa Chile, Concepción y Monagas, según los intereses fijados y las fuentes permitidas. El resumen y la portada respetan fuentes ocultas y palabras silenciadas. Guardadas conserva su excepción existente para fuentes ocultas.
- Perfiles Visual, Compacto y Solo titulares sobre las preferencias actuales. La letra elegida se mantiene y las columnas efectivas se reducen cuando falta espacio, sin sobrescribir las columnas guardadas. Tarjetas sin foto usan identificación compacta; acciones etiquetadas de al menos 44px; controles de escritorio en una segunda fila legible.
- Búsqueda de carpetas y fuentes y carpetas fijadas dentro del menú existente. Preferencias locales incluidas en respaldo v3 y restablecimiento. Si falla una escritura durante la importación se restauran el estado, los módulos y el almacenamiento anteriores.
- Últimas noticias utilizables antes del archivo completo. Descarga con tres trabajadores, progreso, límite de 15 segundos y reintento. Publicación atómica solo al validar generación y cantidad total. Texto de búsqueda normalizado en caché por noticia; resultados de filtros reutilizados dentro de cada render.

## Evidencia y revisión

- Python: 316 pruebas sin consultas a editores; JavaScript: 13 suites, incluidas agrupación, metadata, lectura, secuencia del lector, rollback y cálculos repetidos.
- Nuevas pruebas Chromium con fixtures: experiencia a 320, 768, 1440 y 1842px; resumen/atribución/filtros a 320 y 1440px; archivo lento de 5000 noticias y recuperación tras aborto. Se comprueban foco y posición visual de la noticia al regresar del lector.
- Revisión independiente: resueltos filtrado de variantes ocultas, rollback global, secuencia propia del resumen y lectura atómica. Segundo pase detectó acceso a archivo privado: se expone una copia saneada por RadarLibrary y se verifica con una noticia archivada real, sin noticias en state.items.
- Recorrido responsive Chromium: portada, noticias, navegación, búsqueda, configuración y resumen pasan a 320, 375, 390, 430, 768, 1024 y 1440px.
- Regresión Dimension: 46 pruebas Chromium, incluidas agenda, fuentes, portabilidad, lector, temas, contraste y caché sin conexión.
- CI incluye las nuevas suites. El workflow de publicación no cambia. Los resultados de navegador de CI y el despliegue corresponden al commit/PR y deben consultarse en Actions.

## Límites y controles pertinentes

Confirmado: arquitectura estática, sin cuentas, nuevas dependencias de producción, telemetría ni servicios de IA. Las preferencias siguen en este navegador y el usuario controla exportación/restablecimiento. El respaldo conserva únicamente campos acotados y URLs HTTP(S). No se añaden datos personales al servidor.

Riesgo → evidencia → control → prueba → responsable → estado:

- Atribución incorrecta al agrupar → variantes RSS y metadata heterogéneas → igualdad conservadora, URL y fuente original, sin reescritura → Python/Node y comparación en navegador → mantenedores → mitigado; no equivale a verificación periodística.
- Pérdida de preferencias → error de cuota simulado → validar antes y restaurar toda la importación → Node y navegador → mantenedores → mitigado; almacenamiento local no sustituye un respaldo externo.
- Archivo parcial o antiguo → carga retenida, aborto y generaciones incompatibles → conservar latest, abortar y validar antes de reemplazar → estado y navegador → mantenedores → mitigado.
- Clasificación incompleta → fuentes sin tipo explícito → conservar sin clasificar → pruebas de metadata/filtros → mantenedores → limitación prevista.
- Agrupaciones heredadas → el archivo ya publicado puede contener coincidencias del algoritmo anterior → cambio aplicado en próximas recopilaciones, sin inventar variantes faltantes → fixtures nuevos → mantenedores → no reconstruidas retroactivamente.
- Derechos de contenido en países de medios/lectores, en particular Chile y Venezuela → titulares/extractos/enlaces originales → atribución y extracción existente, sin nueva redistribución integral → revisión técnica → titular del sitio → licencias y cumplimiento jurídico no certificados por esta tarea.
- Capacidad pública y dispositivos físicos → pruebas locales con fixtures → ninguna afirmación de usuarios simultáneos de producción ni de VoiceOver/TalkBack físico → pendiente de pruebas específicas → titular del sitio → fuera de la evidencia de esta entrega.
