# Radar-RSS: identidad editorial

Paleta aprobada: petróleo `#16394A`, turquesa `#238A90` y coral `#E77B65`, con colores de interfaz adaptados al contraste de cada tema.

Los dos PNG maestros se generaron para este proyecto mediante `image_gen`: símbolo RSS/radar transparente y tarjeta social editorial. No se afirma exclusividad de marca o certificación jurídica. Se conservan los activos anteriores del repositorio.

Los tamaños de navegador e instalación se exportan desde los maestros con el renderer del navegador, sin alterar su dibujo:

```sh
python browser_tests/export_radar_brand.py
```

El comando usa el entorno de desarrollo con Playwright; no añade dependencias a producción. `RADAR_CHROMIUM_EXECUTABLE` permite seleccionar Chromium ya instalado. Exporta la marca de 128 píxeles, favicon de 64, iconos de 192/512, maskable de 512, Apple de 180 y tarjeta social de 1200×630. El área segura del icono maskable incluye margen adicional; todos los archivos activos usan el prefijo `radar-rss-`.
