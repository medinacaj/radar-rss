# Comodidad visual y enlaces directos

El usuario aprueba las seis mejoras visuales propuestas y excluye expandir titulares. Reitera que abrir una noticia debe llevar directamente al sitio del medio. La autorización de revisar, fusionar y publicar sigue vigente.

## Aceptación
- Cabecera: fuente y tipo siguen accesibles; perfil, columnas y tamaño del titular se agrupan bajo Presentación. Reutilizar controles, IDs y preferencias existentes; guardar/importar/restablecer conserva el funcionamiento.
- Tarjetas: una sola identificación visible del medio cuando hay cabecera sin foto; menos relleno, separaciones y espacio interior vacío, sin reducir la letra elegida ni los botones de 44px. Filas mantienen orden de lectura y alineación superior, sin masonry.
- Leídas: mismo contraste de título y extracto; marca discreta «Leída» y estado del botón para distinguirlas. No depender solo del color.
- Móvil: filtros en diálogo inferior con cierre, Escape, foco contenido y devolución al botón; conservar filtros activos en el listado y las selecciones. Redimensionar o navegar cierra el diálogo y devuelve los controles a escritorio sin duplicarlos.
- Superficies: una separación/borde claro por tarjeta; sombras suaves y énfasis reservado a selección, hover y foco. Conservar paleta y categorías actuales.
- Titulares e imágenes de noticias, Inicio, Resumen y cobertura abren la URL HTTP(S) original. Respetar la opción de pestaña, Ctrl/Cmd y clic central, sin impedir navegación nativa ni reescribir noticias. Se marca la lectura sin retirar el enlace antes de la navegación. Comparar medios sigue siendo una acción explícita independiente. Sin expansión de titulares ni nueva preferencia que reactive la vista previa al pulsar el título.

## Referencias y decisiones
Referencia principal: capturas aprobadas de la versión ca4897b, 320 y1440px; guía Refero typography (jerarquía/contraste/ritmo) y craft-details (diálogo, foco, controles nativos y enlaces). Refero remoto no dispone de suscripción en esta sesión. Se conserva el sistema Dimension. Elección técnica: ampliar app/feed-ux/experience existentes; diálogo nativo para filtros y details para Presentación. No nueva dependencia ni servicio. Se descarta rehacer la aplicación o cambiar de paleta: añade riesgo sin mejorar el objetivo.

## Riesgos y controles
Fuentes y países (Chile/Venezuela y demás medios) mantienen atribución, extractos y enlaces; no cambia recolección ni licencias. Preferencias siguen locales, sin telemetría ni datos nuevos. Riesgo de foco/enlaces → controles semánticos y enlaces nativos → pruebas de popup/misma pestaña/modificadores y móvil → mantenedores. Licencias/cumplimiento jurídico no se certifican en esta tarea.
