"use strict";
/* Activity dates are local calendar days. Publication time is attribution only. */
(() => {
  const section=$('agendaSection'), list=$('agendaList'), status=$('agendaStatus');
  if(!section||!list||!status)return;
  const pending=$('agendaPending'), pendingList=$('agendaPendingList'), retry=$('agendaRetry');
  let documentData=null, horizon=90, phase='loading', requestedGeneration=null, requestNumber=0;
  const preferencesKey='radar-agenda-preferences-v1';
  let preferences={version:1,saved:[],view:'list'}, onlySaved=false, calendarMonth=null, selectedDay=null, visibleRows=[];
  const filters={query:'',category:'',locality:'',event_type:'',price:''};
  const zones=new Map();
  const renderedRows=new WeakMap();
  const text=(value,limit=1000)=>typeof value==='string'&&value.trim().length>0&&value.length<=limit;
  const object=value=>value!==null&&typeof value==='object'&&!Array.isArray(value);
  const day=value=>{
    if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(value)||value.slice(0,4)==='0000')return false;
    const date=new Date(value+'T00:00:00Z');
    return Number.isFinite(date.getTime())&&date.toISOString().slice(0,10)===value;
  };
  const stamp=value=>{
    if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(value))return false;
    return day(value.slice(0,10))&&Number.isFinite(Date.parse(value))&&+value.slice(11,13)<24&&+value.slice(14,16)<60&&+value.slice(17,19)<60;
  };
  const zone=value=>{
    if(!text(value,100))return false;
    try{
      if(!zones.has(value))zones.set(value,new Intl.DateTimeFormat('en-CA',{timeZone:value,year:'numeric',month:'2-digit',day:'2-digit'}));
      return true;
    }catch{return false;}
  };
  const url=value=>{
    if(!text(value,4000)||!safeURL(value))return false;
    const parsed=new URL(value);
    return !parsed.username&&!parsed.password;
  };
  function validate(data){
    const require=condition=>{if(!condition)throw new Error('Agenda inválida');};
    require(object(data)&&data.version===1&&data.horizon_days===90&&stamp(data.generated_at));
    require(['items','pending','sources'].every(key=>Array.isArray(data[key])));
    require(data.items.length+data.pending.length<=20000&&data.sources.length<=1000);
    require(new TextEncoder().encode(JSON.stringify(data)).length<=8000000);
    const ids=new Set();
    for(const key of ['items','pending'])for(const row of data[key]){
      require(object(row));
      require([['id',128],['title',500],['source_id',128],['source_name',500],['category',500]].every(([name,limit])=>text(row[name],limit)));
      require(!ids.has(row.id)&&url(row.url));ids.add(row.id);
      require(['scheduled','cancelled','postponed'].includes(row.status));
      require(stamp(row.first_seen_at)&&stamp(row.last_seen_at)&&Date.parse(row.first_seen_at)<=Date.parse(row.last_seen_at)&&Date.parse(row.last_seen_at)<=Date.parse(data.generated_at));
      require(row.announced_at===null||stamp(row.announced_at));
      require(row.location===null||text(row.location,500));
      for(const name of ['locality','event_type','price_text'])require(row[name]===undefined||row[name]===null||text(row[name],200));
      require(row.is_free===undefined||row.is_free===null||typeof row.is_free==='boolean');
      require(row.preference_source_id===undefined||row.preference_source_id===null||text(row.preference_source_id,128));
      if(key==='items'){
        require(zone(row.timezone)&&day(row.start_date));
        require(row.end_date===null||(day(row.end_date)&&row.end_date>=row.start_date));
        require(row.status!=='postponed');
        require(object(row.date_evidence)&&['rss','jsonld','text','calendar'].includes(row.date_evidence.kind)&&text(row.date_evidence.value,1000)&&url(row.date_evidence.url));
      }else{
        require(row.start_date===null&&row.end_date===null&&row.date_evidence===null);
        require(row.timezone===null||zone(row.timezone));
        require(['date_unverified','timezone_missing','postponed'].includes(row.reason));
      }
    }
    const sourceIds=new Set();
    for(const source of data.sources){
      require(object(source)&&text(source.source_id,128)&&!sourceIds.has(source.source_id));sourceIds.add(source.source_id);
      require(text(source.source_name,1000)&&url(source.url)&&zone(source.timezone));
      require(stamp(source.checked_at)&&Date.parse(source.checked_at)<=Date.parse(data.generated_at));
      require(['ok','error'].includes(source.status)&&(source.status==='ok'?source.error===null:text(source.error,1000)));
    }
    return data;
  }
  const localDay=(timezone,now)=>{
    const parts=zones.get(timezone).formatToParts(now), part=kind=>parts.find(p=>p.type===kind).value;
    return `${part('year')}-${part('month')}-${part('day')}`;
  };
  const addDays=(value,count)=>{
    const date=new Date(value+'T00:00:00Z');date.setUTCDate(date.getUTCDate()+count);
    return date.toISOString().slice(0,10);
  };
  const dateLabel=value=>new Intl.DateTimeFormat('es',{timeZone:'UTC',day:'numeric',month:'long',year:'numeric'}).format(new Date(value+'T00:00:00Z'));
  function validatePreferences(value){
    if(!object(value)||Object.keys(value).sort().join(',')!=='saved,version,view'||value.version!==1||!['list','calendar'].includes(value.view)||!Array.isArray(value.saved)||value.saved.length>1000||
      !Array.from(value.saved).every(id=>text(id,128))||new Set(value.saved).size!==value.saved.length)throw new Error('Preferencias de agenda inválidas');
    return {version:1,saved:[...value.saved],view:value.view};
  }
  function exportPreferences(){return {version:1,saved:[...preferences.saved],view:preferences.view};}
  function restorePreferences(value){
    const next=validatePreferences(value);
    // Validate the complete value before writing; storage failure leaves memory intact.
    localStorage.setItem(preferencesKey,JSON.stringify(next));
    preferences=next;paint();return exportPreferences();
  }
  function clearPreferences(){
    localStorage.removeItem(preferencesKey);
    preferences={version:1,saved:[],view:'list'};onlySaved=false;paint();
  }
  try{const stored=storeGet(preferencesKey);if(stored)preferences=validatePreferences(JSON.parse(stored));}catch{/* Invalid local preferences do not invalidate event data. */}
  const button=(id,label)=>{const node=mk('button','',label);node.type='button';if(id)node.id=id;return node;};
  const tools=mk('div','agenda-tools');
  const views=mk('div','agenda-controls');views.setAttribute('role','group');views.setAttribute('aria-label','Vista de actividades');
  const viewList=button('agendaViewList','Lista'), viewCalendar=button('agendaViewCalendar','Calendario');
  for(const control of [viewList,viewCalendar])control.setAttribute('aria-controls','agendaCalendar agendaList');
  views.append(viewList,viewCalendar);
  const savedOnly=button('agendaSavedOnly','Guardadas vigentes (0)');savedOnly.setAttribute('aria-describedby','agendaSavedHelp');
  const exportButton=button('agendaExport','Exportar visibles (.ics)');exportButton.disabled=true;
  tools.append(views,savedOnly,exportButton);
  const filterBar=mk('div','agenda-filters');
  const searchLabel=mk('label','agenda-filter','Buscar en la agenda'), search=mk('input');
  search.id='agendaSearch';search.type='search';search.maxLength=200;search.placeholder='Título, lugar o fuente';searchLabel.append(search);filterBar.append(searchLabel);
  const selects={};
  for(const [key,id,label] of [['category','agendaCategory','Zona / carpeta'],['locality','agendaLocality','Comuna / ciudad'],['event_type','agendaType','Tipo'],['price','agendaPrice','Precio']]){
    const labelNode=mk('label','agenda-filter',label), select=mk('select');select.id=id;selects[key]=select;labelNode.append(select);filterBar.append(labelNode);
    select.addEventListener('change',()=>{filters[key]=select.value;paint();});
  }
  const reset=button('agendaResetFilters','Limpiar filtros');filterBar.append(reset);
  const savedHelp=mk('p','agenda-help','Guardar conserva sólo identificadores en este navegador. Guardadas muestra la agenda vigente de hasta 90 días según tus preferencias; no conserva actividades retiradas o vencidas.');savedHelp.id='agendaSavedHelp';
  const actionStatus=mk('p','agenda-help');actionStatus.id='agendaActionStatus';actionStatus.setAttribute('role','status');actionStatus.setAttribute('aria-live','polite');
  status.before(tools,filterBar,savedHelp,actionStatus);
  const calendar=mk('div','agenda-calendar');calendar.id='agendaCalendar';calendar.hidden=true;
  const monthHeading=mk('div','agenda-calendar-heading'), monthTitle=mk('h3');monthTitle.id='agendaCalendarTitle';monthTitle.setAttribute('aria-live','polite');
  const previousMonth=button('agendaCalendarPrev','Mes anterior'), nextMonth=button('agendaCalendarNext','Mes siguiente');
  previousMonth.setAttribute('aria-controls','agendaCalendarGrid');nextMonth.setAttribute('aria-controls','agendaCalendarGrid');
  monthHeading.append(previousMonth,monthTitle,nextMonth);
  const monthGrid=mk('table','agenda-calendar-grid');monthGrid.id='agendaCalendarGrid';monthGrid.setAttribute('aria-labelledby','agendaCalendarTitle');
  const week=mk('thead'), weekRow=mk('tr');
  for(const [short,long] of [['Lun','Lunes'],['Mar','Martes'],['Mié','Miércoles'],['Jue','Jueves'],['Vie','Viernes'],['Sáb','Sábado'],['Dom','Domingo']]){
    const cell=mk('th','',short);cell.scope='col';cell.setAttribute('aria-label',long);weekRow.append(cell);
  }
  week.append(weekRow);const monthBody=mk('tbody');monthGrid.append(week,monthBody);
  const dayHeading=mk('p','agenda-day-heading');dayHeading.id='agendaCalendarDayTitle';
  calendar.append(monthHeading,monthGrid,dayHeading);list.before(calendar);
  search.addEventListener('input',()=>{filters.query=search.value;paint();});
  reset.addEventListener('click',()=>{filters.query='';search.value='';for(const key of Object.keys(selects))filters[key]='';onlySaved=false;paint();});
  function setView(view){try{restorePreferences({...exportPreferences(),view});}catch{actionStatus.textContent='No se pudo guardar la vista en este navegador.';}}
  viewList.addEventListener('click',()=>setView('list'));
  viewCalendar.addEventListener('click',()=>setView('calendar'));
  savedOnly.addEventListener('click',()=>{onlySaved=!onlySaved;paint();});
  const shiftMonth=offset=>{const date=new Date(calendarMonth+'-01T00:00:00Z');date.setUTCMonth(date.getUTCMonth()+offset);calendarMonth=date.toISOString().slice(0,7);selectedDay=calendarMonth+'-01';paint();};
  previousMonth.addEventListener('click',()=>shiftMonth(-1));nextMonth.addEventListener('click',()=>shiftMonth(1));
  const priceKind=row=>row.is_free===true?'free':row.is_free===false?'paid':'unknown';
  const rowText=row=>stripAccents([row.title,row.source_name,row.location||'',row.locality||'',row.event_type||'',row.price_text||''].join(' '));
  function eligible(row){
    if(state.hiddenSources.has(row.source_id)||(row.preference_source_id&&state.hiddenSources.has(row.preference_source_id)))return false;
    if(window.RadarV12&&!window.RadarV12.dashboardMatch({categories:[row.category]},{useSavedCategories:true}))return false;
    const haystack=rowText(row);
    const query=stripAccents(state.search.trim());
    if(query&&!haystack.includes(query))return false;
    return !state.mutedKeywords.split(',').map(word=>stripAccents(word.trim())).filter(word=>word.length>1).slice(0,30).some(word=>haystack.includes(word));
  }
  function matchesFilters(row){
    if(filters.query&&!rowText(row).includes(stripAccents(filters.query.trim())))return false;
    for(const key of ['category','locality','event_type'])if(filters[key]&&filters[key]!== (row[key]?'value:'+row[key]:'unknown'))return false;
    return (!filters.price||priceKind(row)===filters.price)&&(!onlySaved||preferences.saved.includes(row.id));
  }
  function updateFilterOptions(rows){
    const update=(key,options)=>{
      const select=selects[key], signature=JSON.stringify(options);
      if(select.dataset.options!==signature){
        select.replaceChildren(...options.map(([value,label])=>{const option=mk('option','',label);option.value=value;return option;}));select.dataset.options=signature;
      }
      // A hidden source must not leave its metadata in option labels.
      if(!options.some(([value])=>value===filters[key]))filters[key]='';
      select.value=filters[key];
    };
    for(const key of ['category','locality','event_type']){
      const values=[...new Set(rows.map(row=>row[key]).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'es'));
      update(key,[['','Todas'],...values.map(value=>['value:'+value,key==='category'?categoryLabel(value):value]),...(rows.some(row=>!row[key])?[['unknown','Por confirmar']]:[])]);
    }
    const kinds=new Set(rows.map(priceKind));
    update('price',[['','Todos'],...([['free','Gratis'],['paid','De pago'],['unknown','Por confirmar']].filter(([kind])=>kinds.has(kind)))]);
    reset.disabled=!onlySaved&&!Object.values(filters).some(Boolean);
  }
  function toggleSaved(row){
    const saved=preferences.saved.includes(row.id)?preferences.saved.filter(id=>id!==row.id):[...preferences.saved,row.id];
    try{restorePreferences({...exportPreferences(),saved});actionStatus.textContent=saved.includes(row.id)?'Actividad guardada en este navegador.':'Actividad quitada de guardadas.';}
    catch{actionStatus.textContent=saved.length>1000?'Puedes guardar hasta 1000 actividades. Quita alguna antes de añadir otra.':'No se pudo guardar la actividad en este navegador.';}
  }
  async function share(row,item){
    const sourceURL=safeURL(row.url);
    if(navigator.share){
      try{await navigator.share({title:row.title,url:sourceURL});return;}catch(error){if(error.name==='AbortError')return;}
    }
    try{if(navigator.clipboard?.writeText){await navigator.clipboard.writeText(sourceURL);actionStatus.textContent='Enlace de la fuente copiado.';return;}}catch{/* Offer a selectable link when clipboard permissions are unavailable. */}
    let field=item.querySelector('.agenda-share-link');
    if(!field){field=mk('input','agenda-share-link');field.type='url';field.readOnly=true;field.value=sourceURL;field.setAttribute('aria-label','Enlace de la actividad para copiar');item.append(field);}
    field.focus();field.select();actionStatus.textContent='Copia el enlace de la fuente seleccionado.';
  }
  const icsText=value=>String(value).replace(/\\/g,'\\\\').replace(/\r\n|\r|\n/g,'\\n').replace(/;/g,'\\;').replace(/,/g,'\\,').replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g,'');
  function foldLine(value){
    const encoder=new TextEncoder();let line='',size=0;const parts=[];
    for(const character of value){const bytes=encoder.encode(character).length;if(size+bytes>75){parts.push(line);line=' ';size=1;}line+=character;size+=bytes;}
    parts.push(line);return parts.join('\r\n');
  }
  function exportCalendar(rows){
    const confirmed=rows.filter(row=>row.status==='scheduled'&&day(row.start_date)&&zone(row.timezone));
    if(!confirmed.length)return;
    const lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Radar-RSS//Agenda//ES','CALSCALE:GREGORIAN','METHOD:PUBLISH'];
    const generated=new Date(documentData.generated_at).toISOString().replace(/[-:]/g,'').replace(/\.\d+/,'');
    // Dates are deliberately all-day: source times are not part of this contract.
    for(const row of confirmed){
      lines.push('BEGIN:VEVENT','UID:'+encodeURIComponent(row.id)+'@agenda.radar-rss','DTSTAMP:'+generated,
        'DTSTART;VALUE=DATE:'+row.start_date.replace(/-/g,''),'DTEND;VALUE=DATE:'+addDays(row.end_date||row.start_date,1).replace(/-/g,''),
        'SUMMARY:'+icsText(row.title));
      if(row.location||row.locality)lines.push('LOCATION:'+icsText([row.location,row.locality].filter(Boolean).join(' · ')));
      lines.push('DESCRIPTION:'+icsText('Fuente: '+row.source_name+' · Zona horaria: '+row.timezone), 'URL:'+safeURL(row.url),'STATUS:CONFIRMED','END:VEVENT');
    }
    lines.push('END:VCALENDAR');
    const blob=new Blob([lines.map(foldLine).join('\r\n')+'\r\n'],{type:'text/calendar;charset=utf-8'}), href=URL.createObjectURL(blob), anchor=mk('a');
    anchor.href=href;anchor.download='radar-rss-agenda.ics';document.body.append(anchor);anchor.click();anchor.remove();setTimeout(()=>URL.revokeObjectURL(href),1000);
    actionStatus.textContent=`Exportadas ${confirmed.length} actividades con fecha confirmada. Verifica posibles cambios en la fuente.`;
  }
  exportButton.addEventListener('click',()=>exportCalendar(visibleRows));
  function eventRow(row,unconfirmed=false){
    const item=mk('li','agenda-item');item.dataset.eventId=row.id;
    if(unconfirmed){
      item.append(mk('p','agenda-date',row.status==='cancelled'?'Cancelada':row.status==='postponed'||row.reason==='postponed'?'Aplazada · nueva fecha por confirmar':'Fecha por confirmar'));
    }else{
      const dates=mk('p','agenda-date');
      const start=mk('time','',dateLabel(row.start_date));start.dateTime=row.start_date;dates.append(start);
      if(row.end_date&&row.end_date!==row.start_date){
        const end=mk('time','',dateLabel(row.end_date));end.dateTime=row.end_date;
        dates.append(document.createTextNode(' — '),end);
      }
      item.append(dates);
    }
    const heading=mk('h3','agenda-item-title'), anchor=mk('a','',row.title);
    anchor.href=safeURL(row.url);anchor.target='_blank';anchor.rel='noopener noreferrer external';anchor.referrerPolicy='no-referrer';
    heading.append(anchor);item.append(heading);
    item.append(mk('p','agenda-meta',`${row.source_name} · ${categoryLabel(row.category)}`));
    item.append(mk('p','agenda-place',(row.location||'Lugar por confirmar')+(row.timezone?' · Zona horaria: '+row.timezone:'')));
    const details=[row.locality||'Comuna / ciudad por confirmar',row.event_type||'Tipo por confirmar',row.is_free===true?'Gratis':row.is_free===false?row.price_text||'De pago · monto por confirmar':row.price_text||'Precio por confirmar'];
    item.append(mk('p','agenda-details',details.join(' · ')));
    if(row.announced_at){
      const announcement=mk('p','agenda-announced','Anunciado: '), time=mk('time','',new Intl.DateTimeFormat('es',{timeZone:row.timezone||'UTC',day:'numeric',month:'long',year:'numeric'}).format(new Date(row.announced_at)));
      time.dateTime=row.announced_at;announcement.append(time);item.append(announcement);
    }
    const actions=mk('div','agenda-item-actions'), save=button('',preferences.saved.includes(row.id)?'Guardada':'Guardar'), shareButton=button('','Compartir enlace');
    save.dataset.agendaSave='';save.setAttribute('aria-pressed',String(preferences.saved.includes(row.id)));save.setAttribute('aria-label','Guardar actividad: '+row.title);
    save.addEventListener('click',()=>toggleSaved(row));shareButton.dataset.agendaShare='';shareButton.setAttribute('aria-label','Compartir enlace: '+row.title);shareButton.addEventListener('click',()=>{void share(row,item);});
    actions.append(save,shareButton);
    if(!unconfirmed){const singleExport=button('','Descargar .ics');singleExport.dataset.agendaExport='';singleExport.setAttribute('aria-label','Descargar calendario: '+row.title);singleExport.addEventListener('click',()=>exportCalendar([row]));actions.append(singleExport);}
    item.append(actions);
    return item;
  }
  function reconcile(target,rows,unconfirmed=false){
    const previous=new Map([...target.children].map(node=>[node.dataset.eventId,node]));
    const active=target.contains(document.activeElement)?document.activeElement.closest('[data-event-id]')?.dataset.eventId:null;
    const activeControl=['agendaSave','agendaShare','agendaExport'].find(name=>document.activeElement?.dataset?.[name]!==undefined);
    const next=rows.map(row=>{
      const signature=JSON.stringify([row,preferences.saved.includes(row.id)]), old=previous.get(row.id);
      if(old&&renderedRows.get(old)===signature)return old;
      const node=eventRow(row,unconfirmed);renderedRows.set(node,signature);return node;
    });
    if(next.length===target.children.length&&next.every((node,index)=>node===target.children[index]))return;
    target.replaceChildren(...next);
    if(active){
      const replacement=next.find(node=>node.dataset.eventId===active)?.querySelector(activeControl?'[data-'+activeControl.replace(/[A-Z]/g,letter=>'-'+letter.toLowerCase())+']':'a');
      (replacement||savedOnly).focus({preventScroll:true});
    }
  }
  function paintCalendar(rows,todayByZone,now){
    const knownDays=[...todayByZone.values()], firstDay=knownDays.length?knownDays.sort()[0]:now.toISOString().slice(0,10), lastDay=addDays(knownDays.at(-1)||firstDay,horizon);
    if(!calendarMonth||calendarMonth<firstDay.slice(0,7)||calendarMonth>lastDay.slice(0,7))calendarMonth=firstDay.slice(0,7);
    if(!selectedDay||!selectedDay.startsWith(calendarMonth))selectedDay=calendarMonth===firstDay.slice(0,7)?firstDay:calendarMonth+'-01';
    monthTitle.textContent=new Intl.DateTimeFormat('es',{timeZone:'UTC',month:'long',year:'numeric'}).format(new Date(calendarMonth+'-01T00:00:00Z'));
    previousMonth.disabled=calendarMonth<=firstDay.slice(0,7);nextMonth.disabled=calendarMonth>=lastDay.slice(0,7);
    const monthStart=calendarMonth+'-01', next=new Date(monthStart+'T00:00:00Z');next.setUTCMonth(next.getUTCMonth()+1);
    const monthEnd=addDays(next.toISOString().slice(0,10),-1), counts=new Map();
    for(const row of rows){
      const localToday=todayByZone.get(row.timezone), start=[row.start_date,monthStart,localToday].sort().at(-1), end=[row.end_date||row.start_date,monthEnd,addDays(localToday,horizon)].sort()[0];
      for(let date=start;date<=end;date=addDays(date,1))counts.set(date,(counts.get(date)||0)+1);
    }
    const signature=JSON.stringify([calendarMonth,selectedDay,[...counts],firstDay,lastDay]);
    if(monthBody.dataset.signature!==signature){
      const focused=monthBody.contains(document.activeElement)?document.activeElement.dataset.agendaDate:null;
      const cells=[], offset=(new Date(monthStart+'T00:00:00Z').getUTCDay()+6)%7;
      for(let i=0;i<offset;i++)cells.push(mk('td','agenda-calendar-blank'));
      for(let date=monthStart;date<=monthEnd;date=addDays(date,1)){
        const cell=mk('td'), count=counts.get(date)||0, control=button('',String(Number(date.slice(8))));
        control.dataset.agendaDate=date;control.setAttribute('aria-label',`${dateLabel(date)}: ${count} ${count===1?'actividad':'actividades'}`);control.setAttribute('aria-pressed',String(date===selectedDay));
        if(date===now.toISOString().slice(0,10))control.setAttribute('aria-current','date');
        if(count){control.append(mk('span','agenda-calendar-count',String(count)));control.classList.add('has-events');}
        control.addEventListener('click',()=>{selectedDay=date;paint();});cell.append(control);cells.push(cell);
      }
      while(cells.length%7)cells.push(mk('td','agenda-calendar-blank'));
      const weeks=[];for(let i=0;i<cells.length;i+=7){const week=mk('tr');week.append(...cells.slice(i,i+7));weeks.push(week);}
      monthBody.replaceChildren(...weeks);monthBody.dataset.signature=signature;
      if(focused)[...monthBody.querySelectorAll('button')].find(node=>node.dataset.agendaDate===focused)?.focus({preventScroll:true});
    }
    dayHeading.textContent='Actividades del '+dateLabel(selectedDay);
    return rows.filter(row=>row.start_date<=selectedDay&&(row.end_date||row.start_date)>=selectedDay&&selectedDay>=todayByZone.get(row.timezone)&&selectedDay<=addDays(todayByZone.get(row.timezone),horizon));
  }
  function paint(){
    section.setAttribute('aria-busy',String(phase==='loading'));
    retry.hidden=phase!=='error';
    viewList.setAttribute('aria-pressed',String(preferences.view==='list'));viewCalendar.setAttribute('aria-pressed',String(preferences.view==='calendar'));
    savedOnly.setAttribute('aria-pressed',String(onlySaved));
    const sameGeneration=!state.generated||documentData?.generated_at===state.generated;
    if(phase!=='ready'&&!(phase==='loading'&&documentData&&sameGeneration)){
      list.replaceChildren();pendingList.replaceChildren();pending.hidden=true;
      visibleRows=[];exportButton.disabled=true;calendar.hidden=true;savedOnly.textContent='Guardadas vigentes (0)';
      updateFilterOptions([]);
      status.textContent=phase==='loading'?'Cargando actividades…':'No se pudo cargar la agenda. Vuelve a intentarlo.';
      return;
    }
    const now=new Date(), todayByZone=new Map();
    const today=row=>{
      if(!todayByZone.has(row.timezone))todayByZone.set(row.timezone,localDay(row.timezone,now));
      return todayByZone.get(row.timezone);
    };
    const current=documentData.items.filter(row=>eligible(row)&&row.status==='scheduled'&&(row.end_date||row.start_date)>=today(row)&&row.start_date<=addDays(today(row),90));
    const announcements=[...documentData.pending.filter(row=>Date.parse(row.last_seen_at)>=now.getTime()-90*86400000),
      ...documentData.items.filter(row=>row.status==='cancelled'&&(row.end_date||row.start_date)>=today(row)&&row.start_date<=addDays(today(row),horizon))].filter(eligible);
    updateFilterOptions([...current,...announcements]);
    savedOnly.textContent=`Guardadas vigentes (${[...current,...announcements].filter(row=>preferences.saved.includes(row.id)).length})`;
    const rows=current.filter(row=>row.start_date<=addDays(today(row),horizon)&&matchesFilters(row))
      .sort((a,b)=>a.start_date.localeCompare(b.start_date)||a.title.localeCompare(b.title,'es')||a.id.localeCompare(b.id));
    calendar.hidden=preferences.view!=='calendar';
    visibleRows=preferences.view==='calendar'?paintCalendar(rows,todayByZone,now):rows;
    list.setAttribute('aria-label',preferences.view==='calendar'?'Actividades confirmadas del '+dateLabel(selectedDay):'Actividades confirmadas');
    reconcile(list,visibleRows);
    const changes=announcements.filter(matchesFilters);reconcile(pendingList,changes,true);
    pending.hidden=!changes.length;
    $('agendaPendingTitle').textContent=`Fechas por confirmar y cambios (${changes.length})`;
    exportButton.disabled=!visibleRows.length;exportButton.textContent=`Exportar visibles (.ics)${visibleRows.length?' · '+visibleRows.length:''}`;
    status.textContent=phase==='loading'?'Actualizando actividades…':visibleRows.length?`${visibleRows.length} ${visibleRows.length===1?'actividad':'actividades'} · ${horizon===0?'Hoy':'Hasta '+horizon+' días'}`:'No hay actividades confirmadas para este período con tus preferencias.';
  }
  async function refresh(){
    const number=++requestNumber;
    requestedGeneration=state.generated||'';phase='loading';paint();
    try{
      const data=validate(await dataFetch('./data/events.json?check='+Date.now()));
      if(number!==requestNumber)return;
      if(state.generated&&data.generated_at!==state.generated)throw new Error('Generación de agenda diferente');
      requestedGeneration=state.generated||'';
      documentData=data;phase='ready';
    }catch{
      if(number!==requestNumber)return;
      documentData=null;phase='error';
    }
    paint();
  }
  function sync(){
    if(state.ready&&phase!=='loading'&&requestedGeneration!==(state.generated||''))void refresh();
    else paint();
  }
  for(const button of section.querySelectorAll('[data-agenda-days]'))button.addEventListener('click',()=>{
    horizon=Number(button.dataset.agendaDays);
    for(const control of section.querySelectorAll('[data-agenda-days]'))control.setAttribute('aria-pressed',String(control===button));
    paint();
  });
  retry.addEventListener('click',()=>{void refresh();});
  const renderBase=render;
  render=function(...args){const result=renderBase(...args);sync();return result;};
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)sync();});
  window.addEventListener('focus',sync);
  window.setInterval(()=>{if(!document.hidden)sync();},30000);
  window.RadarAgenda=Object.freeze({refresh,validatePreferences,exportPreferences,restorePreferences,clearPreferences});
  // Agenda can load even if an unrelated news resource prevents boot().
  void refresh();
})();
