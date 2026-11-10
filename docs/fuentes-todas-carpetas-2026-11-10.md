# Fuentes añadidas a todas las carpetas — 10 de noviembre de 2026

Se incorporan 34 canales: 18 RSS del editor y 16 consultas RADAR identificadas. El catálogo pasa de 409 a 443 suscripciones en las once carpetas existentes. Los nombres, IDs, URLs, categorías y orden de las 409 anteriores se conservan. Una consulta RADAR no equivale a un RSS directo ni una suscripción adicional a un propietario editorial independiente.

| Carpeta | Antes | Altas | Total | Canales añadidos |
|---|---:|---:|---:|---|
| Inteligencia Artificial | 61 | +3 | 64 | [OFICIAL — CENIA · Investigación de IA en Chile](https://cenia.cl/noticias/); [RADAR — AESIA · Supervisión y gobernanza de IA](https://aesia.digital.gob.es/es/actualidad); [OFICIAL — Microsoft Source LATAM · IA en español](https://news.microsoft.com/source/latam/etiqueta/ia/) |
| Tecnología | 75 | +3 | 78 | [MEDIO — Pisapapeles · Tecnología móvil en Chile](https://pisapapeles.net/); [MEDIO — Mundo Xiaomi · Dispositivos y HyperOS](https://www.mundoxiaomi.com/); [MEDIO — Xataka México · Tecnología en México](https://www.xataka.com.mx/) |
| Internacionales | 65 | +2 | 67 | [RADAR — Público · Internacional](https://www.publico.es/internacional); [OFICIAL — Vatican News · Español](https://www.vaticannews.va/es.html) |
| Chile | 35 | +4 | 39 | [MEDIO — Diario El Día · Coquimbo](https://www.diarioeldia.cl/); [RADAR — Fiscalía Nacional Económica](https://www.fne.gob.cl/); [RADAR — Universidad de Chile · Noticias](https://uchile.cl/noticias); [MEDIO — Diario El Centro · Maule](https://www.diarioelcentro.cl/) |
| Venezuela | 29 | +3 | 32 | [MEDIO — Contrapunto · Venezuela](https://contrapunto.com/); [RADAR — Diario de Los Andes · Regiones](https://diariodelosandes.com/); [MEDIO — Correo del Caroní · Guayana](https://correodelcaroni.com/) |
| Latinoamérica | 26 | +4 | 30 | [MEDIO — Página/12 · Argentina](https://www.pagina12.com.ar/); [RADAR — Confidencial · Nicaragua](https://confidencial.digital/); [MEDIO — Plaza Pública · Guatemala](https://plazapublica.com.gt/); [RADAR — La Jornada · México](https://www.jornada.com.mx/) |
| Concepción | 33 | +4 | 37 | [RADAR — Municipalidad de Santa Juana](https://santajuana.cl/); [RADAR — Lanalhue Noticias · Biobío](https://www.lanalhuenoticias.cl/); [REGIONAL — Irade · Desarrollo del Biobío](https://irade.cl/); [RADAR — Municipalidad de Hualqui](https://www.munihualqui.cl/) |
| Maturín / Monagas | 10 | +3 | 13 | [RADAR — MundoUR / Unión Radio · Monagas](https://mundour.com/); [RADAR — Fedecámaras Radio · Monagas](https://fedecamarasradio.com/); [RADAR — Otilca Radio · Cultura en Maturín](https://radio.otilca.org/) |
| Startups y Capital | 32 | +3 | 35 | [OFICIAL — Startup Valencia · Ecosistema emprendedor](https://startupvalencia.org/es/category/noticias/); [RADAR — SpainCap · Capital privado y venture capital](https://www.spaincap.org/comunicacion/noticias); [RADAR — Enisa · Financiación de startups](https://www.enisa.es/actualidad/noticias/) |
| Empresas y Economía | 35 | +2 | 37 | [MEDIO — Ámbito · Economía](https://www.ambito.com/economia); [MEDIO — Economía Digital](https://www.economiadigital.es/) |
| Investigación y Gestión | 8 | +3 | 11 | [MEDIO — Estudios de la Gestión · UASB](https://revistas.uasb.edu.ec/index.php/eg/); [MEDIO — Cuadernos de Gestión · Español e inglés](https://ojs.ehu.eus/index.php/CG/); [RADAR — Retos · Administración y economía](https://retos.ups.edu.ec/index.php/retos/) |

## Evidencia y límites

La investigación utiliza páginas primarias de los editores y sus enlaces RSS, o la observación del tipo XML/RSS en un endpoint. La herramienta web no analizó el XML de los feeds. El acceso del ejecutor a dominios editoriales está restringido por su política de red: no se desactivó TLS ni se eludió esa restricción. Por ello no se inventan códigos HTTP, cantidades de entradas ni hashes de respuestas. El registro [de descubrimiento](../sources/all-categories-discovery-2026-11-10.json) identifica método, URL, fecha observada y una muestra mínima por canal. La fecha de rastreo no se usa como fecha de publicación.

Los canales RADAR se restringen al editor y a 45 días, salvo investigación académica (730 días). En las fuentes regionales amplias se exigen términos territoriales en el titular; los sitios municipales de Santa Juana y Hualqui ya tienen ámbito local y se consultan por dominio. No se confunde una cartelera de eventos con una noticia fechada. Los nuevos RSS propios se prefieren a su alternativa intermediada cuando se observa un endpoint XML/RSS.

Microsoft Source LATAM aporta una fuente corporativa primaria en español; el RADAR anterior de Microsoft es una búsqueda temática de noticias de diferentes medios. Mundo Xiaomi y Xataka México son publicaciones del grupo Webedia, que también posee cabeceras ya presentes; no se presentan como propietarios independientes. Vatican News es una fuente institucional religiosa, identificada como OFICIAL. Cuadernos de Gestión y Estudios de la Gestión pueden ofrecer contenido original en inglés además de español.

La salud y disponibilidad real se actualizan en la ingesta habitual y en data/status.json de la web publicada. La declaración de un RSS y una muestra reciente no garantizan su disponibilidad futura ni su indexación en Google Noticias. Las pruebas de catálogo se ejecutan sin red y comprueban preservación, cobertura, unicidad y trazabilidad; la validación operativa corresponde al flujo normal de publicación.

## Datos, atribución y condiciones

Los editores nuevos incluyen instituciones y medios de Chile, España, Venezuela, Argentina, México, Nicaragua, Guatemala, Ecuador, Estados Unidos y el Vaticano. No se añaden cuentas, dependencias, proveedores de ejecución ni datos personales del lector. Se mantienen los límites de archivo y retención, los enlaces al editor, la atribución y el tratamiento existente de titulares, extractos e imágenes. No se incorpora texto completo al registro de evidencia.

La página consultada de Cuadernos de Gestión identifica CC BY-NC-ND; su acceso abierto no concede permisos comerciales o de transformación adicionales. Las demás condiciones particulares de los editores siguen siendo responsabilidad de la curación: no se certifica una licencia global ni cumplimiento jurídico. La disponibilidad técnica de RSS no acredita derechos adicionales de reproducción.

Riesgo → evidencia → control → prueba → responsable → estado: duplicar o añadir cobertura ajena a una carpeta → catálogo y muestras editoriales → dominio/territorio explícitos y trazabilidad → auditoría OPML y regresiones sin red → mantenedor del catálogo → revisión del PR. Riesgo operativo de caída o ausencia de resultados → estado real de la ingesta → monitorización existente y caché → comprobación de generación publicada → mantenedor de ingesta → estado dinámico en status.json.
