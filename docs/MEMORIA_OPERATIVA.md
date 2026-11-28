# Memoria operativa — Radar-RSS

Corte: **28-11-2026, America/Santiago** (contraste remoto alrededor de 09:45–10:10 locales). Revalidar GitHub al retomar; esta memoria no promete salud permanente. La sección «Actualización 28-11» manda sobre las tablas anteriores cuando difieran; estas se conservan como historia del corte del 26-11.

## Actualización 28-11 (estado real contrastado)

| Hecho | Evidencia |
|---|---|
| `main` = `f07a9fbe9a6e9f6819a491f2549449dee4c03da8` (#186, D-11) | git local/remoto coinciden; CI [46145224151](https://github.com/medinacaj/radar-rss/actions/runs/46145224151) success. |
| **#184 integrado** (`7a61a00`): Protego en `requirements.txt` (`>=0.6.2,<0.7`), diagnóstico `robots_http/rule/delay` y marca `last_scan.robots_policy="rfc9309-v1"` | CI [46144614768](https://github.com/medinacaj/radar-rss/actions/runs/46144614768) success; despliegue [46144614771](https://github.com/medinacaj/radar-rss/actions/runs/46144614771) success. |
| **AUTO tras #184** (log del job 140977788821, 12:26:04Z): la migración revisó una sola vez; `robots_denials: 11`, **`robots_rule: 11`**, `robots_http: 0`, `robots_delay: 0`, `added: 0`, `outcome: unavailable` | Las once semillas fueron rechazadas por **regla explícita** del robots.txt real, no por HTTP ni crawl-delay. El defecto del parser deja de ser causa probable. Por D-08 se respeta la denegación; no se suplantan crawlers ni se desactiva robots. Altas AUTO reales siguen en **cero**. |
| **Agenda con D-11** (despliegue #335 [46145224099](https://github.com/medinacaj/radar-rss/actions/runs/46145224099), job 140979695940) | `Agenda validated: 0 events 108 pending` (antes 101 pendientes): **D-11 está integrado y desplegado pero aún no demuestra efecto**. Causa no determinada: el log no distingue por qué quedan pendientes. |
| Despliegues programados | Cron :17 cada hora UTC con éxito hasta #335 (12:33Z). #165 sigue abierto sin cambios (único PR abierto). |
| No verificable desde este entorno | Pages, blobs de artefactos y logs completos bloqueados por el proxy del entorno; sin lectura directa de `events.json`/`discovered-sources.json` publicados. |

### Cambio de esta sesión (rama `claude/gracious-meitner-j6bfz1`, sin integrar)

Diagnóstico **solo de log** para la agenda: `extract_event(..., diagnostics=dict)` y `_text_date(..., trace=list)` clasifican cada anuncio de actividad sin fecha estructurada (`confirmada_texto`, `confirmada_ano_deducido`, `sin_fecha_en_texto`, `fecha_sin_clausula`, `fecha_no_inmediata`, `contexto_inscripcion`, `sin_ano_sin_ancla`, `sin_ano_fuera_de_margen`, `alternativa`, `negacion`, `fechas_contradictorias`); `collect_events.py` imprime el recuento en stderr (`Agenda, fechas en texto: ...`). No cambia reglas de confirmación, JSON publicado ni esquema (comprobado: resultado idéntico con y sin diagnóstico). Pruebas: 422 Python (Python 3.13 local, CI usa 3.12), `node --check` de siete archivos y las dos suites Node citadas en AGENTS.md. **Implementado y probado localmente; no integrado ni desplegado.**

Observación a decidir (no cambiada): `REALIZATION` reconoce «se realizará/celebrará/…» en singular; el plural «se realizarán» queda como `fecha_no_inmediata`. Puede ser una causa de pendientes, pero ampliar el reconocimiento afecta D-05/D-11 y exige decisión del propietario con evidencia del log.

**Siguiente acción concreta:** integrar este diagnóstico (PR único tras CI), leer en el siguiente despliegue la línea `Agenda, fechas en texto:` y decidir con esos recuentos si hace falta ampliar el reconocimiento o si el 0 confirmadas es legítimo. Para AUTO: investigar una vía legítima (feeds publicados explícitamente, APIs o acuerdos) en lugar de reintentar sobre robots que prohíben; no forzar altas.

## Identidad e infraestructura

| Dato | Evidencia confirmada |
|---|---|
| Producto/propósito | Radar-RSS: agregador y lector RSS/Atom, monitoreo, tendencias, resumen, fuentes y agenda. |
| Propietario/repositorio | `medinacaj` (cuenta indicada por AJ-Med!n@); https://github.com/medinacaj/radar-rss, público, no archivado. |
| Principal/código | `main`, base `76c0d8a797cb0a51886a8e6646e717e8ddf9cff9`. |
| Continuidad de código | `fix/discovery-robots-rfc9309-20261126`, [#184](https://github.com/medinacaj/radar-rss/pull/184), head `88a653e0f12fbfcab9d8d30b22b224a557617132`. |
| Respaldo documental | Rama `docs/respaldo-continuidad-20261126`, basada en main. SHA final comunicado tras publicación, no dentro de su propio commit. |
| Versiones | `app.js?v=9.12.5`, `radar-rss-v82`; sin releases globales publicadas en GitHub. |
| Producción | https://medinacaj.github.io/radar-rss/; coincide en site_config, canonical y logs de Pages. |
| Stack | Python 3.12, feedparser/requests; HTML/CSS/JavaScript sin framework; Node 22 y Playwright para CI. |
| Infraestructura | GitHub Actions → JSON/RSS estáticos → GitHub Pages. Sin backend, cuentas, BD, pagos, Vercel ni sincronización actual. |
| Entornos | Desarrollo con fixtures/servidor local; no se identificó staging desplegado independiente. |

La descripción de GitHub aún dice Notisonda; documentación antigua usa /notisonda/ y radar-rss-publico. Son residuos/historia. Código, propietario, URL canónica y despliegue confirman este destino. No se cambiaron ajustes del repositorio.

## Estado implementado, integrado y verificado

| Capa | Estado |
|---|---|
| Código integrado | #175/#176/#178–#180/#182/#183, lectura/UX, catálogo 443/11, investigación y automatización. |
| Calidad main | [45802350978](https://github.com/medinacaj/radar-rss/actions/runs/45802350978) success: 407 Python, sintaxis y suites Node. |
| Navegadores de integración | Head `eab9619d0e84235c3330cbb4690f9b4b3e807679`: [calidad](https://github.com/medinacaj/radar-rss/actions/runs/45799365110) y [Chromium/Firefox/WebKit](https://github.com/medinacaj/radar-rss/actions/runs/45799365137) success antes del squash #176. |
| Última producción demostrada | [45846110685](https://github.com/medinacaj/radar-rss/actions/runs/45846110685), deploy job 140001714747: generación `2026-11-26T15:09:06Z`, comprobada a 15:11:49Z (12:11:49 Santiago). |
| Datos en ese instante | 443 fuentes, 300 noticias iniciales, 5.000 totales y 122 trabajos de investigación; agenda 0 confirmadas/101 pendientes, 11/22 orígenes disponibles. No inventar actividad para llenar la agenda. |
| Monitor | [45846651508](https://github.com/medinacaj/radar-rss/actions/runs/45846651508) failure: siete RSS en error, umbral cinco. No prueba caída completa de Pages. |
| Frescura actual | A las 21:03 UTC la última generación demostrada tenía casi seis horas. La herramienta web no pudo leer meta/registro directamente. Revalidar frescura y cron; no declarar producción actualmente fresca por aquel log. |
| AUTO | **No funcionalmente verificado**: revisión 10:33:14Z, 0/11 búsquedas, once comprobaciones robots rechazadas, cero altas, outcome unavailable. El ciclo de 15:09 reutilizó caché y respetó 48h. |
| #184 | **Incompleto**: solo siete regresiones RED; Protego y migración aún no implementados. Navegadores verdes no corrigen las pruebas de calidad fallidas. |
| Staging/carga/dispositivos | No verificados. Playwright no acredita usuarios concurrentes, dispositivos físicos ni VoiceOver/TalkBack. |
| Local | El entorno falló al consultar capacidades del ejecutor. No se inspeccionaron git status, remotos locales, archivos nuevos/eliminados/sin seguimiento ni commits locales sin publicar. No afirmar árbol limpio ni recuperación total del disco. El trabajo realizado mediante conector está en remoto. |

## Avances disponibles

- **UX:** Visual/Compacto/Solo titulares, columnas ajustadas al contenedor sin sobrescribir preferencias, títulos con preferencia base 14–22 px y escalado por ancho aprobado (resolución #132), tarjetas compactas, filtros móviles con Escape/foco, navegación original y comparación aparte. [Comodidad visual](visual-comfort-2026-11-10.md).
- **Editorial:** hasta siete historias por resumen y misma selección al escuchar/copiar/compartir, atribución/diversidad, agrupación conservadora, tipo solo con metadata explícita, Guardadas/lectura/Deshacer preservados. [Experiencia](reading-experience-2026-11-10.md).
- **Fuentes:** [catálogo](../sources/feeds.opml) 443/11, #148 añadió 34 conservando IDs. Investigación y Gestión retiene 730 días y protege hasta 200 entradas dentro de 5.000; noticias 45 días, agenda independiente de 90. [Retención](research-retention-2026-11-10.md).
- **Actualizar:** comprueba y aplica lo publicado con generación coherente, recuento y preferencias. No inicia ingesta desde el navegador. Publicación mayor de cuatro horas informa recopilación pendiente. Cron previsto :17 cada hora UTC; comprobación del navegador cada quince minutos, con posibles retrasos de GitHub. [Diagnóstico](refresh-delay-2026-11-14.md).
- **AUTO integrado:** ciclo 48h, once carpetas, cinco altas/ciclo/cien AUTO máximo, 22 candidatos, 100 solicitudes y 180s; procedencia/estado público, OPML temporal, caché, respaldo y transporte seguro. **Cero altas reales comprobadas.** [Detalle](automatic-source-discovery.md).
- **Identidad:** #182 archivó ocho originales byte por byte fuera de web y corrigió aliases públicos; #183 documentó continuidad. Históricos no equivalen a la marca actual.
- **Seguridad:** #178/#180 y transporte AUTO conservan URL/host público, IP fijada, robots, presupuesto y saneamiento; AUTO sin imágenes/OG.

## Historia 26-11 — plan de #184 (ya ejecutado; ver actualización 28-11)

Python 3.12 robotparser usa primer prefijo y no interpreta correctamente precedencia, comodines ni end anchors RFC 9309. El código consulta RadarRSS y el AGENT completo (interpretado como Mozilla por stdlib). Los fixtures demuestran falsos bloqueos y falsos permisos.

**Falta evidencia para atribuir los once rechazos reales a ese defecto:** reason=robots también engloba HTTP no permitido y crawl-delay. No se obtuvo status/cuerpo/digest/regla decisiva del robots real; no presumir permiso de Google.

Plan propuesto, no implementado:
1. Evaluar `protego>=0.6.2,<0.7` (release oficial 0.6.2 corrige ReDoS), licencia y versión vigentes; justificar dependencia conforme a AGENTS. API Protego.parse(str), can_fetch(url, "RadarRSS"), crawl_delay/request_rate.
2. Mantener UA honesto, HTTPS/DNS/IP fijados, límites, denegaciones HTTP y delay. No ordenar todos los Allow primero, desactivar robots, suplantar crawlers ni eludir restricciones/proxies.
3. Diagnóstico acotado HTTP/regla/delay; marca `last_scan.robots_policy="rfc9309-v1"` persistida también por sanitize_state, caché y recuperación.
4. Un estado antiguo unavailable sin marca puede revisarse una sola vez tras corregir; estados nuevos respetan 48h. Añadir round trip JSON para que el saneamiento no pierda la marca y dispare búsquedas horarias.
5. GREEN y revisión/CI antes de integrar. Verificar luego investigación real, estado público, altas si proceden y atribución en una tarea productiva autorizada, con recuperación comprobada; no como parte del respaldo. Si la política real deniega, respetarla y evaluar una fuente de investigación legítima.

Módulos: scripts/safe_publisher.py, scripts/source_discovery.py, requirements.txt, tests/test_source_discovery.py, docs/automatic-source-discovery.md. Leer la documentación nueva desde main antes de retomar su rama existente; no reconstruir la funcionalidad.

## Ramas, PR e issues

Inventario de entrada: 144 ramas antes de la rama documental (143 auditadas inicialmente + #184); no se borró ninguna. Main code `76c0d8a...` corresponde al squash #176; #182 squash `06caa3ae54debc1393fd9d582fc3068d1fd4e165`; #183 `c14db875a6d05244aabb66fac0becc33691dc018`.

- #184: **integrado** (`7a61a00`); el estado «RED» y la sección «Siguiente acción P1: #184» de abajo son historia del 26-11.
- [#165](https://github.com/medinacaj/radar-rss/pull/165) abierto: test/sidebar-browser-contracts-20261113, head `100afc385fec8c8dcdafcd1da0b46a9128504907`, selectores obsoletos y tres navegadores fallidos; superposición #170/#171. No fusionar sin resolver.
- design/pulso-editorial: sin PR; head observado abreviado 3e2f9fb9, conservado, no adoptado.
- Quince ramas cerradas sin merge: #120/#121/#123/#125/#126/#128/#132 consolidadas en #138; #76/#77/#78/#88/#92 incorporadas/sustituidas posteriormente; #36 por #39, #163 por #170, #48 obsoleta. Exclusividad de commits tras squash no justifica importar ramas enteras. [Consolidación](integracion-pendientes-2026-11-03.md) y [historia](project-status.md). Crónica Uno/candidatas deshabilitadas siguen como investigación.

Prioridades, conservando las previamente registradas:
- **P0:** ningún incidente crítico nuevo confirmado en el respaldo. Si aparece exposición real, contener y preservar evidencia.
- **P1:** #184; frescura/cron y alerta [#161](https://github.com/medinacaj/radar-rss/issues/161), sin duplicarla. [#177](https://github.com/medinacaj/radar-rss/issues/177): auditoría v3.0 parcial y main.protected=false observado; no se cambiaron permisos.
- **P1 ya abiertos:** dispositivos [#31](https://github.com/medinacaj/radar-rss/issues/31), canonical/monitor [#124](https://github.com/medinacaj/radar-rss/issues/124), IA/ElevenLabs [#127](https://github.com/medinacaj/radar-rss/issues/127), UI/títulos [#129](https://github.com/medinacaj/radar-rss/issues/129)/[#131](https://github.com/medinacaj/radar-rss/issues/131), identidad [#181](https://github.com/medinacaj/radar-rss/issues/181). Varios son históricos/parcialmente resueltos: contrastar antes de rehacer o cerrar.
- **P2:** fuentes [#160](https://github.com/medinacaj/radar-rss/issues/160), curación [#32](https://github.com/medinacaj/radar-rss/issues/32), #165, carga/CWV/SEO/accesibilidad según alcance aprobado. No retirar medios por fallos transitorios.
- **P3 propuestas:** conservación durable externa, cuentas, sincronización y backend V2, no implementados ni autorizados por el respaldo. Pulso no sustituye la UI.

## Pruebas y evidencia

| Verificación | Resultado real |
|---|---|
| python -m unittest discover -s tests -v, main | 407 correctas en CI. |
| node --check y diez archivos de pruebas Node de ci.yml | Success; lectura, respaldo, editorial, experiencia, render y visitas. |
| responsive.yml sobre head de integración #176 | Chromium/Firefox/WebKit success. Primer intento Firefox/WebKit agotó instalación; reintento pasó sin cambios. |
| python scripts/audit_feeds.py --opml ... | 443 fuentes/11 carpetas/cero problemas en primer build #176. |
| python scripts/validate_data.py web/data | 5.000 artículos/16 particiones; siete errores RSS último build. |
| python scripts/check_pages.py ... --expected-generation ... | Log público exacto de 15:11:49Z, no garantía de frescura actual. |
| #184 calidad | [45803425970](https://github.com/medinacaj/radar-rss/actions/runs/45803425970): 414 pruebas, **3 fallos y 4 errores** reproducidos. [Navegadores](https://github.com/medinacaj/radar-rss/actions/runs/45803425888) success. |
| Documentación | Revisar diff, rutas/enlaces relativos y patrones de secretos; verificar CI del PR documental antes de integrar. SHA final se informa tras publicación. |
| No ejecutado | Pruebas locales por entorno fallido, carga real concurrente, dispositivos/lectores físicos, staging, restauración, auditoría v3.0 completa y nuevas altas AUTO. |

## Protección, operación y recuperación

Dependencias actuales: feedparser>=6.0.11,<7 y requests>=2.32,<3; no Protego todavía. Sin clave RSS/LLM. Variables de Actions por nombre, sin valores: GITHUB_TOKEN/GH_TOKEN, GITHUB_REPOSITORY, RUNNER_TEMP; verificador RADAR_EXPECTED_GENERATION/RADAR_PAGE_URL; monitor DEPLOY_CONCLUSION/CHECK_RESULT/GH_REPO; recuperación restore_run_id/RESTORE_RUN. HTTP_PROXY/HTTPS_PROXY/ALL_PROXY hacen fallar seguro a AUTO; no neutralizarlas para eludir la red.

Último artefacto observado: radar-public-data-45846110685, [15131962728](https://github.com/medinacaj/radar-rss/actions/runs/45846110685/artifacts/15131962728), subido 26-11-2026, retención prevista 90 días sujeta a política. Contiene JSON públicos y registro AUTO, no preferencias privadas. No se descargó ni ensayó restauración durante este respaldo.

La recuperación manual con restore_run_id valida y vuelve a recopilar/publicar: necesita una tarea autorizada. No ejecutar resets, semillas, migraciones ni cambios de infraestructura como comprobación documental. Mantener IDs/GUID, fechas, atribución y respaldo v2/v3. No publicar conversaciones, credenciales, datos personales ni exportaciones privadas del navegador. No se certifican licencias o cumplimiento legal por este respaldo.

**Próximo paso concreto:** cuando el entorno vuelva, comprobar cwd/remoto/árbol y preservar cualquier trabajo local; retomar #184 con este plan, regresiones y límites. La autorización general de integración evita confirmaciones repetidas, pero no convierte este respaldo documental en orden de despliegue.
