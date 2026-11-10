# Radar RSS — mejoras de contenido y experiencia de lectura

Solicitud aprobada: aplicar todas las mejoras técnicas y visuales propuestas, con prioridad en experiencia de usuario. La autorización permanente permite verificar, fusionar y publicar sin nuevas aprobaciones.

## Objetivos y aceptación
- Contenido: resumen selectivo de hasta siete historias recientes con fuente/fecha/cobertura; agrupación conservadora de duplicados; destacados de Chile/Concepción/Monagas según intereses; tipo noticia/opinión/análisis/comunicado solo cuando exista evidencia explícita del editor, con estado sin clasificar y filtro reversible.
- Lectura: tarjetas sin foto con identificación compacta; perfiles Visual/Compacto/Solo titulares sobre ajustes existentes; letra elegida legible y menos columnas cuando el espacio no alcance; controles reconocibles; filtros activos visibles y eliminables; móvil sin desbordamiento.
- Navegación: búsqueda de carpetas/fuentes y favoritos fijados en el menú, con almacenamiento local y respaldo/restablecimiento coherentes. Conservar IDs/rutas y la posición/foco al cerrar el lector.
- Rendimiento: mostrar latest antes del archivo completo; descargar archivo con concurrencia limitada, progreso, reintento y cambio de generación seguro; evitar cálculos completos repetidos dentro del mismo render. No presentar contadores parciales como totales completos.
- Verificación: pruebas Node/Python existentes y regresiones de navegador con fixtures, latencia/fallo de archivo, almacenamiento corrupto, fuentes ocultas, cambio de perfil y tamaños 320–1842 px. No recolectar editores en pruebas.

## Dirección y decisiones
Referencia principal: producto y capturas aprobadas. Conservar tipografía, esquema actual claro/oscuro, coral para selección/acciones, menú compacto y botones de 44px. Refero no tiene suscripción activa: usar referencias de craft ya consultadas, especialmente legibilidad, foco, táctil y estados asíncronos. Cada cambio visual debe facilitar localizar, leer o gestionar noticias; sin nuevos recursos decorativos ni fotos ficticias.

Se amplían módulos existentes con tres módulos pequeños (modelo editorial puro, interfaz editorial e interfaz de experiencia). Se conserva JS estático/Python; sin nuevas dependencias de producción, cuentas, IA externa ni telemetría. Las noticias no se reescriben: titulares, extractos y fechas se atribuyen al medio.

Se evita una reescritura del frontend por su riesgo sobre respaldos, rutas y lector. También se evita agregar otra capa de navegación paralela: favoritos y búsquedas operan sobre el menú actual. El filtro de tipo es temporal de la vista; no es una preferencia exportada. Los favoritos sí se incluyen en respaldos locales.
