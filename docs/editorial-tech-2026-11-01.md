# Radar RSS — Editorial + tecnológico (propuesta de diseño, issue #129)

**Estado:** solo rama de revisión; no publicado. Se apoya en el rediseño inicial del PR #123; este cambio es **incremental** y su integración depende del PR #123. No fusionar ni publicar sin aprobación humana.

## Dirección visual aprobada
Una portada con noticia principal dominante y titulares secundarios; centro de información con jerarquía editorial y controles precisos. Se eliminan violetas como acento dominante y el efecto de superficies de igual tonalidad. Se conserva la marca y la lógica editorial del PR #123, sin cambiar el motor de extracción.

| Propiedad | Oscuro | Claro |
|---|---|---|
| Fondo | `#10151d` grafito | `#edf1f5` gris frío |
| Tarjetas | `#202a36` | `#ffffff` |
| Superficie secundaria | `#17212c` | `#e1e8ee` |
| Texto principal | `#f6f8fb` | `#1b2530` |
| Acción principal / foco | `#ff8968` coral | `#b5422a` coral profundo |
| Acción de texto | `#171d27` | `#ffffff` |
| Estado / radar | `#37cfa4` verde funcional | `#16785d` verde funcional |

Los colores de categorías derivados del feed permanecen separados de la acción principal.

## Geometría y componentes

- Anchura máxima de contenido: **1450 px**, columnas de noticias automáticas desde 300 px y márgenes fluidos entre 16 y 44 px; cabecera, contenido y pie comparten guía.
- Sidebar y cabecera con bordes definidos; botones y navegación de lectura consistente; enfoque visible.
- Portada principal a dos columnas en escritorio y vertical en móvil. Imágenes 16:9 y titulares más fuertes, respetando la opción guardada de tamaño de texto.
- Tarjetas con sombras distinguibles, elevación al pasar el puntero, ampliación moderada de imagen y estados accesibles al foco.
- Agenda, resumen, radar, lector y configuración comparten superficie, radios, borde y profundidad.
- CSS integrado **en el archivo existente `web/dimension.css`**; no se añade una hoja temática adicional.
- Cambios en `web/index.html` y `web/sw.js` únicamente para metadatos, versión CSS y caché PWA (v58).

## Movimiento y accesibilidad

- Animaciones cortas de aparición y respuesta para nuevas noticias; hover táctil no imprescindible.
- La elevación de tarjeta se aplica solo cuando hay puntero fino y hover real; controles con transición de posición y sombra.
- `prefers-reduced-motion: reduce` deshabilita las animaciones nuevas, los desplazamientos y las transiciones en esos elementos.
- `forced-colors: active` conserva contornos; selección con teclado usa foco visible.
- No se activan efectos continuos y no se añade una librería de animación.

## Verificación

- `python -m unittest discover -s tests -v`
- `python browser_tests/dimension_regressions.py` con Playwright en Chromium, Firefox y WebKit (según CI).
- `node --check web/app.js` y `node --check web/sw.js`.
- Contraste real, capturas, navegación con teclado, lectores de pantalla y prueba física de móviles deben comprobarse en browser/QA; los contratos estáticos no prueban una imagen renderizada.
- Rutas y anchuras a revisar: Inicio, Noticias, Resumen, Agenda, lector y configuración; 320, 390, 768, 950, 951, 1440, 1842 y 2560 px, ambos temas, texto grande, sidebar variable y modo reducido.
- En el browser test anterior, el techo de ancho de contenido se cambia de 1200 a 1450 px en concordancia con la nueva cuadrícula.

## Riesgos y límites

No se han tocado fuentes RSS, la lógica de ingesta, claves de usuario, respaldos ni las APIs públicas. El cambio en anchura máxima puede exigir ajustes visuales en pantallas grandes; el nuevo contraste y los estados activos deben verificarse con mediciones reales. Las pruebas estáticas no reemplazan una inspección visual de producción. El PR #123 aún está en borrador y es requisito previo de esta propuesta.
