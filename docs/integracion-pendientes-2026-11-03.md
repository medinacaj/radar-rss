# Integración de borradores pendientes

Autorización: el usuario pidió continuar con todos los PR pendientes; AGENTS.md permite revisar, fusionar y publicar sin aprobación manual adicional.

| PR | Resolución |
| --- | --- |
| #120 | Integradas las 95 altas de negocios, sus observaciones y documentación. |
| #121 | Integradas las dos altas de Monagas y su evidencia; Crónica Uno sigue pendiente de verificación local, como en el borrador. |
| #123 | Identidad, recursos gráficos, rutas canónicas y protección de caché ya presentes en main. Se conservan los cambios de interfaz posteriores; no se restaura el CSS antiguo. |
| #125 | Integrada la detección de estados RSS malformados y recuentos booleanos, con sus regresiones. |
| #126 | La URL canónica ya estaba corregida; añadida la regresión específica pendiente. |
| #128 | Integrado el canal RADAR específico de ElevenLabs, identificado como Google Noticias, y su regresión. |
| #132 | Eliminado el multiplicador oculto 1,15 y actualizada la caché PWA. Se mantiene el escalado por ancho de tarjeta solicitado después por el usuario; el control representa la preferencia base, no un tamaño fijo para todas las columnas. |

El catálogo conjunto tiene 409 fuentes y 11 categorías. Los contratos históricos siguen comprobando exactamente los 311 registros iniciales (IDs, URLs, nombres y carpetas); cada ampliación tiene sus pruebas de procedencia y unicidad. Las observaciones de disponibilidad de los documentos originales son históricas, no nuevas verificaciones en vivo. La recolección y la disponibilidad actual se comprueban por separado durante la publicación.

La prueba de interfaz deja de exigir un tamaño fijo independiente del ancho, pero conserva el mínimo de 14 px y el rango del control. La revisión de cubiertas detectó una base flex fija de 148 px en las fotos reales: se elimina para que se adapten como sus alternativas sin foto. El modo Compacto conserva el máximo de 96 px.

No se añaden cuentas, telemetría, proveedores nuevos ni cambios de permisos. Las altas usan RSS públicos o canales RADAR ya admitidos. La evidencia RSS no certifica licencias editoriales ni disponibilidad futura.
