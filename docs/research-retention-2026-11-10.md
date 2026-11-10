# Investigación y Gestión: retención

La ingesta aplicaba a las revistas académicas el mismo corte de 45 días que a las noticias diarias. Además, las 5.000 entradas más recientes podían desplazar toda la carpeta. El catálogo ya contenía ocho fuentes y consultas académicas con ventanas de hasta 730 días.

El colector conserva ahora los trabajos de «11 - Investigación y Gestión» durante 730 días y protege hasta 200 entradas de esa carpeta al seleccionar candidatos y artículos finales. Los espacios libres se aprovechan para otras noticias. Se mantienen los límites de 7.500 candidatos, 5.000 artículos y particiones de 300, además del orden cronológico, las fechas y los créditos originales. La pertenencia se calcula con las fuentes del catálogo actual; una etiqueta antigua en caché no concede retención adicional.

Los filtros personales de antigüedad siguen vigentes. Por ejemplo, seleccionar 90 días puede ocultar trabajos anteriores aunque se conserven en el archivo. El titular sigue abriendo directamente la web del medio.

## Evidencia

- Seis regresiones del colector reproducidas antes de corregirlo: antigüedad, límite exacto, ventana personalizada, catálogo/caché, saturación y agrupación/persistencia. Después: seis correctas y batería completa de 322 pruebas Python correcta.
- 14 suites Node y seis controles de sintaxis correctos.
- Prueba de navegador con archivo de 5.000 entradas y trabajos de 400 días: carpeta, fecha original, navegación al editor y filtro de antigüedad, en móvil y escritorio. Incluida en CI.
- El resumen `RESULTADO` de cada ingesta informa `research_articles` para contrastar la cantidad retenida en la generación publicada.

## Alcance y controles

Confirmados: corte global anterior y selección por recencia; fuentes académicas ya presentes. La cantidad disponible en cada actualización depende de lo que publiquen y devuelvan los RSS. No se añaden fuentes, servicios, dependencias ni datos personales. El almacenamiento sigue acotado y no se copia el texto completo de los artículos.

Riesgo → evidencia → control → prueba → responsable → estado: exclusión de trabajos académicos → política anterior de 45 días y archivo saturado → ventana propia y reserva acotada → regresiones sin red y generación de ingesta → mantenedor del colector → corregido en esta rama, publicación verificada en el PR.

Las jurisdicciones y condiciones de los editores, incluidos los de Chile y Venezuela, no se modifican. Las fechas, enlaces y atribución se conservan. Esta corrección no certifica licencias ni cumplimiento jurídico ajeno al alcance revisado.
