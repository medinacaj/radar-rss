# Radar RSS: actualidad continua

El usuario quiere informarse al momento y autoriza proceder con la propuesta de lector de actualidad continua. Se conserva el diseño azul aprobado y la arquitectura estática. Alternativas: seguir con la portada editorial anterior (demasiada prioridad a cobertura frente a recencia), incorporar un servidor de streaming (nuevo coste/infraestructura), o evolucionar Pages con actualización frecuente. Se adopta la tercera.

## Experiencia

La ruta histórica #inicio sigue funcionando, ahora llamada **Ahora**, con un listado cronológico compacto de titulares reales, fuente, categoría, hora de publicación y detección por Radar cuando existan. Sin imágenes grandes, popularidad inventada ni etiqueta automática Urgente. Se muestran 36 entradas y un botón para ampliar hasta las disponibles. Una fecha futura no ocupa la primera posición; se usa detección válida como alternativa cuando no hay publicación válida. Fechas desconocidas se identifican sin inventarlas.

Vistas internas: Ahora; En desarrollo (historias recientes de 24 horas con varias publicaciones agrupadas, no afirmación editorial de suceso activo); Mi zona (selector de carpetas regionales, sin geolocalización); Mi Radar (intereses ya guardados en la aplicación y acceso a preferencias). Solo los intereses filtran Mi Radar: Ahora respeta fuentes ocultas y palabras silenciadas, sin ocultar secciones por personalización de portada. Guardadas mantiene su acceso existente en Noticias. Agenda y Resumen permanecen secundarios. La cobertura y gráfico existentes quedan en un bloque ampliable, cerrado inicialmente.

Una nueva generación solo se anuncia; no cambia tarjetas ni mueve la lectura hasta pulsar Mostrar noticias. Se reutiliza la aplicación atómica y protección ante generaciones incompatibles. El navegador revisa metadata cada minuto solo en primer plano, sin consultar RSS externos. El aviso y el estado deben ser accesibles por teclado y lector de pantalla; no se roba foco con actualizaciones.

## Recopilación

Decisión de implementación: programación cada 15 minutos (7,22,37,52 UTC), en lugar de tres horas. GitHub Actions no garantiza ejecución puntual; no se promete instantaneidad ni cinco minutos. La nueva cadencia multiplica ejecuciones por doce (96 programadas/día frente a 8), depende de cuotas, duración del pipeline y entrega del RSS. No se activará en producción en esta tarea.

Peticiones condicionales con ETag/Last-Modified conservados en status.json; 304 reutiliza los artículos ya guardados y confirma conexión. No usar validadores cuando falta historia del feed o cambia URL. No filtrar cabeceras de validación a redirecciones. Mantener validación de host público, límites de tamaño, TLS, reintento limitado, caché persistida y publicación consistente con agenda. No se cambian fuentes, IDs, retención ni infraestructura.

## Validación y entrega

Pruebas Node de selección temporal, agrupación, filtros y no mutación; Python de cabeceras HTTP condicionales, 304, ausencia de historia y conservación de primer avistamiento; navegador de navegación/timestamps, avisos sin reemplazo, foco y responsive en claro/oscuro; suites actuales adaptadas solo donde cambia un contrato visual aprobado. Cache nueva atómica. No se despliega ni dispara ingesta masiva durante pruebas.
