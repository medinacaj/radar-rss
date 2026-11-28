# Decisiones confirmadas — Radar-RSS

Consolidación 26-11-2026. [Memoria operativa](MEMORIA_OPERATIVA.md) para estados cambiantes; [ADR históricos](decisions.md) conservados, sin duplicar su historia. Una decisión posterior expresa prevalece y su sustitución se documenta.

## D-01 — Identidad y arquitectura [CONFIRMADO]

Radar-RSS, medinacaj, https://github.com/medinacaj/radar-rss, main, https://medinacaj.github.io/radar-rss/. Python → JSON/RSS → GitHub Pages. Sin backend/cuentas/BD/sincronización actuales. No trasladar infraestructura o reglas de otros productos. Notisonda/radar-rss-publico son históricos.

## D-02 — Autonomía con evidencia [CONFIRMADO]

El propietario autorizó el 03-11-2026 revisar, fusionar y publicar PR validados sin pedir aprobación en cada ocasión. **Sustituye ADR-003 del 18-10 y exigencias antiguas de revisión humana repetidas en #124/#129/#131.** Mantener alcance, revisión, pruebas y controles; una tarea/rama/PR, nunca push directo a main ni force push. No fusionar #184 en RED o #165 obsoleto.

## D-03 — Enlaces originales [CONFIRMADO] [NO MODIFICAR]

Decisión expresa reafirmada el 10-11: titular/imagen abren directamente al medio, sin expandir ni interceptar con vista previa, también en móvil/teclado. Conservar pestaña, Enter/modificadores/clic central. Comparar medios es acción aparte; la existencia histórica del lector no permite reintroducir interceptación.

## D-04 — UX y preferencias [CONFIRMADO] [NO MODIFICAR]

Priorizar experiencia de lectura: adaptar tarjetas/textos a todas las columnas y pantallas, compactar espacios, foco/accesibilidad. Conservar columnas guardadas y la preferencia base de titulares de 14–22 px. La decisión posterior del propietario mantiene el escalado según ancho de tarjeta (container queries), con mínimo de 14 px: el control no fija el mismo tamaño renderizado en todas las columnas. Se eliminó el multiplicador oculto 1,15; no introducir nuevos multiplicadores fuera de las escalas aprobadas. Fuente grande/destacado tienen escala propia. [Resolución de #132](integracion-pendientes-2026-11-03.md). Mantener tema, preferencias, lectura, Guardadas y backup; respetar movimiento reducido/contraste. Pulso no es un rediseño adoptado.

## D-05 — Integridad editorial [CONFIRMADO] [NO MODIFICAR]

Preservar titulares, fechas, extractos y atribución. No inventar noticias, fotos ni actividades/fechas de agenda. Tipo editorial solo por metadata explícita; desconocidos visibles. Agrupación conservadora, curación humana y sin prometer veracidad o sesgo detectado.

## D-06 — Fuentes y retención [CONFIRMADO] [NO MODIFICAR]

443 curadas/once carpetas e IDs estables salvo cambios aprobados/validados. Noticias 45 días; investigación 730 con hasta 200 plazas dentro de 5.000; agenda independiente de 90 días. No importar límites históricos 9.000/90 días, snapshots viejos ni segunda agenda. No eliminar medios por una caída.

## D-07 — Actualizar y AUTO [CONFIRMADO]

Actualizar consulta lo publicado; no dispara ingesta desde navegador. Cron horario previsto a :17 UTC y consulta cada quince minutos, con demoras posibles. AUTO autorizado como investigación técnica cada48h con procedencia y límites, no verificación editorial. Código integrado no acredita altas: primera revisión indisponible.

## D-08 — Seguridad de AUTO [CONFIRMADO] [NO MODIFICAR]

HTTPS público, URL/DNS/IP fijada durante TLS, mismo editor, robots y presupuestos; sin sortear 401/403/429 o proxies. No sustituir transporte por requests común ni añadir imágenes/OG AUTO. Corregir interpretación exige probar permisos y prohibiciones; respetar denegación real.

Actualización 28-11: Protego `>=0.6.2,<0.7`, diagnóstico (`robots_http/rule/delay`) y marca persistente `robots_policy=rfc9309-v1` **están implementados e integrados** (#184). Con el parser corregido, las once semillas siguen rechazadas por regla explícita de su robots.txt (`robots_rule: 11`, log del despliegue 46144614771): la denegación es real y **se respeta**; no se suplantan crawlers, no se desactiva robots y no se elude con proxies. Esto no prueba permiso de Google ni de ningún editor.

## D-09 — Privacidad [CONFIRMADO] [NO MODIFICAR]

Preferencias/búsquedas/lectura/Guardadas en localStorage; sin telemetría o sincronización central. No subir credenciales, conversaciones o exportaciones privadas. Artefactos públicos caducan; no conservación permanente ni certificación legal implícita.

## D-10 — Respaldo actual [CONFIRMADO]

Solicitud del 26-11: consolidar este producto y continuidad verificable sin abrir otro producto ni desplegar/cambiar infraestructura durante respaldo. Preservar incompletos en remoto, separar implementación/CI/integración/staging/producción y declarar límites del entorno. No inventar árbol limpio, carga real, pruebas físicas, restauración o frescura actual. SHA base/código dentro del archivo; SHA documental final después de publicar, evitando autorreferencia.

## D-11 — Agenda: año deducido con resguardos [CONFIRMADO]

Decisión expresa del propietario (28-11-2026), que acota D-05 sin sustituirla: un anuncio que da día y mes sin año («se realizará el próximo sábado 6 de diciembre») puede confirmarse **solo si** cumple todas las exigencias de texto ya vigentes (título de actividad, cláusula de realización inmediata, sin fechas alternativas ni negaciones) y el año se toma de la **fecha de publicación del propio anuncio**: la siguiente ocurrencia de ese día y mes en los 90 días posteriores. Sin fecha de publicación, o fuera de ese margen, sigue pendiente. Una publicación con fecha futura usa la hora actual como referencia. La ficha queda marcada (`date_evidence.year_inferred`) y la agenda muestra «año deducido del anuncio». No aplica a calendarios directos (`event_sources.py`), que siguen exigiendo hechos explícitos. Motivo: con la regla anterior la agenda mostraba 0 confirmadas y 101 pendientes.
