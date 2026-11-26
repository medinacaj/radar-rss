# Cambios de Radar-RSS

Registro consolidado, sin reconstruir releases no demostradas. Al 26-11-2026 GitHub no mostraba releases globales. Interfaz `app.js?v=9.12.5`, caché `radar-rss-v82`.

## 26-11-2026 — código integrado

Base de código: `76c0d8a797cb0a51886a8e6646e717e8ddf9cff9`, no SHA del commit que contiene este archivo.

- [#176](https://github.com/medinacaj/radar-rss/pull/176): AUTO cada 48h, catálogo derivado persistente, procedencia, ingesta HTTPS/DNS fijado, robots y plazos. Corrige espera sin consulta previa (regresión reloj 0/119/120), artefacto Pages por intento y respaldo compatible con reintentos. **Primera revisión real: unavailable, 0/11 búsquedas y cero altas; no descubrimiento funcional demostrado.**
- [#182](https://github.com/medinacaj/radar-rss/pull/182): identidad pública corregida y ocho originales históricos conservados fuera de web. Squash `06caa3ae54debc1393fd9d582fc3068d1fd4e165`.
- [#183](https://github.com/medinacaj/radar-rss/pull/183): documentación de continuidad. Squash `c14db875a6d05244aabb66fac0becc33691dc018`.
- Respaldo documental: memoria operativa, decisiones, transferencia y referencias actualizadas. Sin cambios de ejecución, datos o infraestructura.

## Avances anteriores integrados de esta conversación

- [#175](https://github.com/medinacaj/radar-rss/pull/175): Actualizar informa generación real, novedades y recopilación pendiente tras cuatro horas; conserva preferencias. Squash `a475446fe9b318f00d63f56ba45caf54ef599bcf`.
- [#147](https://github.com/medinacaj/radar-rss/pull/147): investigación 730 días y hasta 200 plazas dentro de 5.000.
- [#148](https://github.com/medinacaj/radar-rss/pull/148): 34 altas; catálogo 443 fuentes/once carpetas, IDs conservados.
- [#178](https://github.com/medinacaj/radar-rss/pull/178) y [#180](https://github.com/medinacaj/radar-rss/pull/180): filtros de URL pública OPML/colector/auditoría, conservados.
- UX/editorial: [experiencia de lectura](docs/reading-experience-2026-11-10.md) y [comodidad visual/enlaces](docs/visual-comfort-2026-11-10.md). Sus cifras de pruebas son históricas; la memoria registra evidencia actual.

## Sin integrar ni publicar

- [#184](https://github.com/medinacaj/radar-rss/pull/184), `fix/discovery-robots-rfc9309-20261126`, `88a653e0f12fbfcab9d8d30b22b224a557617132`: siete regresiones nuevas; 414 pruebas con tres fallos/cuatro errores. **Solo reproducción, no corrección terminada.** Protego/marca persistente siguen propuestos.
- [#165](https://github.com/medinacaj/radar-rss/pull/165): contratos obsoletos del lateral y navegadores fallidos; conservar y resolver superposición con #170/#171.
- `design/pulso-editorial`: diseño separado sin PR, preservado y no adoptado.

SHA final documental y resultado de su publicación se entregan fuera del archivo para evitar autorreferencia.
