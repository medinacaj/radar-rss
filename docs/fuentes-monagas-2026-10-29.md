# Fuentes de Maturín y Monagas

Se preparan **dos altas** en `08 - Maturín / Monagas`: un RSS nativo y un canal RADAR de Google Noticias. La carpeta pasa de ocho a **10 suscripciones**. Los 311 registros anteriores conservan exactamente sus URLs, IDs, nombres y carpetas. No se cambia la interfaz ni las preferencias.

Esta tarea parte del catálogo publicado de `main`. El PR #120 de fuentes de negocios queda separado y pendiente, según la indicación del usuario. Ninguno se fusiona ni se publica en esta tarea.

| Medio solicitado | Resultado | Canal local |
|---|---|---|
| La Verdad de Monagas | Se añade RSS nativo de Maturín. Se conservan su RSS general en Venezuela y el RADAR local existente. | [RSS nativo](https://laverdaddemonagas.com/maturin/feed/) |
| El Periódico de Monagas | Su RADAR local ya está incluido y su última publicación figura operativa; se conserva. RSS nativo pendiente de acceso. | [RSS RADAR existente](https://news.google.com/rss/search?q=site%3Aelperiodicodemonagas.com.ve+%28Matur%C3%ADn+OR+Maturin+OR+Monagas%29&hl=es-419&gl=VE&ceid=VE%3Aes-419) |
| La Prensa de Monagas | Su RADAR local ya está incluido y su última publicación figura operativa; se conserva. RSS nativo pendiente de acceso. | [RSS RADAR existente](https://news.google.com/rss/search?q=site%3Alaprensademonagas.com+%28Matur%C3%ADn+OR+Maturin+OR+Monagas%29&hl=es-419&gl=VE&ceid=VE%3Aes-419) |
| Maturín News | Nuevo RADAR con titulares de Monagas y publicaciones recientes. RSS nativo pendiente de acceso. | [RSS RADAR](https://news.google.com/rss/search?q=site%3Amaturinnews.com+intitle%3AMonagas+-intitle%3Aarchivos+when%3A45d&hl=es-419&gl=VE&ceid=VE%3Aes-419) |
| El Pitazo | Su RADAR específico de Monagas/Maturín ya está incluido y operativo; se conserva, junto al RSS general en Venezuela. RSS nativo local pendiente de acceso. | [RSS RADAR existente](https://news.google.com/rss/search?q=site%3Aelpitazo.net+%28intitle%3AMonagas+OR+intitle%3AMatur%C3%ADn+OR+intitle%3AMaturin%29+when%3A30d&hl=es-419&gl=VE&ceid=VE%3Aes-419) |
| Crónica Uno | Alta local pendiente: no se pudo demostrar la pertinencia de la entrada encontrada para Monagas/Maturín. Su canal general de Venezuela se conserva. RSS nativo local pendiente de acceso. | [Portal](https://cronica.uno/) |

Los RADAR son RSS de Google Noticias, no RSS de los editores. La búsqueda de Maturín News exige Monagas en el título y excluye páginas de archivo; una consulta amplia del portal devolvía también navegación y noticias nacionales. Crónica Uno mostró una entrada reciente en la búsqueda, pero su título y extracto RSS no permiten confirmar la relación local. Se deja pendiente, conservando la observación sin suscribir ese canal; tampoco se incorpora una sección genérica de Oriente que pueda mezclar otros estados. La cobertura de Google puede omitir artículos no indexados.

El RSS nativo de Maturín en La Verdad de Monagas devolvió RSS 2.0 con diez entradas y noticias recientes. La ruta de Monagas sufrió un tiempo de espera; no se añade como si funcionara. Un `/feed/` supuesto o una ruta que devuelve HTML no se considera un feed verificado.

La verificación directa de los otros cinco portales sigue pendiente: la red vigente del entorno no permite sus dominios. Se guardaron en el borrador de configuración `elperiodicodemonagas.com.ve`, `laprensademonagas.com`, `maturinnews.com`, `elpitazo.net` y `cronica.uno`, conservando los dominios y cambios anteriores. El borrador debe guardarse y publicarse en la configuración del entorno para activar ese acceso; guardarlo desde el agente no lo activa. Esto no demuestra que los portales carezcan de RSS.

`sources/monagas-verification.json` conserva el resultado individual de los seis medios, IDs existentes y nuevos, proveedor, consulta, fecha, entradas observadas y SHA256 de cada respuesta RSS. La evidencia de disponibilidad es una instantánea, no garantiza respuestas futuras. Las verificaciones automáticas de integridad no consultan servidores externos.

Se mantiene la atribución de los medios y los enlaces originales. Verificar un RSS público no certifica licencia, independencia editorial ni cumplimiento jurídico. No se modifican la retención de 45 días, la programación de recolección ni las políticas existentes sobre resúmenes e imágenes.

La auditoría registra 313 suscripciones en ocho carpetas, con cero problemas. Pasan las 293 pruebas Python, incluidos los hashes históricos sin modificar y el hash completo de los 311 registros anteriores. La prueba de navegador comprueba la actualización 311→313, la carpeta local con 10 fuentes, las preferencias de lectura, guardados, fuentes ocultas y carpetas personales; también las URLs RSS, exportación OPML y visualización a 390/1440 píxeles en ambos temas. El parser del recolector procesó las respuestas RSS guardadas de los dos canales sin errores y encontró 21 artículos recientes entre sus entradas iniciales; esta comprobación no sustituye una recolección posterior en producción. La revisión independiente detectó la pertinencia no demostrada de Crónica Uno; una regresión impide presentar ese candidato como suscripción local verificada.
