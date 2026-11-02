"use strict";
/* Catalogue/OPML utilities shared by the browser and offline Node tests. No I/O. */
(function(root){
  function feedKey(raw){
    if(typeof raw!=='string')return '';
    try{
      const url=new URL(raw.trim());
      if(!['https:','http:'].includes(url.protocol)||url.username||url.password)return '';
      url.hash='';return url.href;
    }catch{return '';}
  }
  const fold=value=>String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('es');
  const sourceKind=source=>source.is_radar===true||/^https?:\/\/news\.google\.com\//i.test(source.url||'')?'radar':'direct';
  const healthState=health=>['ok','error','empty','stale'].includes(health?.state)?health.state:'unknown';
  const statusLabels={ok:'Lectura correcta',error:'No disponible',empty:'Sin noticias',stale:'Sin novedades',unknown:'Sin diagnóstico'};
  function filterSources(sources,options={}){
    const {query='',visibility='all',status='all',type='all',folder='',hiddenIds=new Set(),healthById=new Map(),foldersById=new Map()}=options;
    const needle=fold(query.trim());
    return sources.filter(source=>{
      const hidden=hiddenIds.has(source.id),names=foldersById.get(source.id)||[];
      if(visibility==='visible'&&hidden||visibility==='hidden'&&!hidden)return false;
      if(status!=='all'&&healthState(healthById.get(source.id))!==status)return false;
      if(type!=='all'&&sourceKind(source)!==type)return false;
      if(folder&&!names.includes(folder))return false;
      return !needle||fold([source.name,source.category,source.url,source.website,...names].join(' ')).includes(needle);
    });
  }
  const escapeXML=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));
  function buildOPML(groups,sources,hiddenIds=new Set()){
    const byId=new Map(sources.map(source=>[source.id,source]));
    const assigned=new Set(groups.flatMap(group=>group.ids));
    const allGroups=[...groups,{name:'Sin carpeta',ids:sources.filter(s=>!assigned.has(s.id)).map(s=>s.id)}];
    const lines=['<?xml version="1.0" encoding="UTF-8"?>','<opml version="2.0"><head><title>Mis fuentes Radar RSS</title></head><body>'];
    for(const group of allGroups){
      const feeds=[...new Set(group.ids)].map(id=>byId.get(id)).filter(source=>source&&!hiddenIds.has(source.id)&&feedKey(source.url));
      if(!feeds.length)continue;
      lines.push(`<outline text="${escapeXML(group.name)}" title="${escapeXML(group.name)}">`);
      for(const source of feeds)lines.push(`<outline type="rss" text="${escapeXML(source.name)}" title="${escapeXML(source.name)}" xmlUrl="${escapeXML(feedKey(source.url))}" htmlUrl="${escapeXML(feedKey(source.website))}"/>`);
      lines.push('</outline>');
    }
    return [...lines,'</body></opml>'].join('\n');
  }
  function readOPML(text){
    if(typeof text!=='string'||text.length>1_000_000)throw Error('El OPML supera 1 MB.');
    if(/<!\s*(DOCTYPE|ENTITY)\b/i.test(text))throw Error('El OPML no admite DTD ni entidades.');
    const doc=new DOMParser().parseFromString(text,'application/xml');
    if(doc.querySelector('parsererror')||doc.documentElement?.tagName.toLowerCase()!=='opml')throw Error('XML/OPML inválido.');
    const body=[...doc.documentElement.children].find(node=>node.tagName.toLowerCase()==='body');
    if(!body)throw Error('Falta el cuerpo OPML.');
    const outlines=[...body.querySelectorAll('outline')];
    if(outlines.length>2000)throw Error('Demasiados elementos OPML.');
    const records=[];
    for(const node of outlines){
      const url=node.getAttribute('xmlUrl');
      if(url===null)continue;
      const names=[];
      for(let parent=node.parentElement;parent&&parent!==body;parent=parent.parentElement){
        if(parent.tagName==='outline'&&!parent.hasAttribute('xmlUrl')){
          const name=(parent.getAttribute('text')||parent.getAttribute('title')||'').trim().replace(/\s+/g,' ');
          if(name)names.unshift(name);
        }
      }
      const folder=names.join(' / ')||'Importadas';
      if(folder.length>45||folder==='__proto__')throw Error('Los nombres de carpeta deben tener como máximo 45 caracteres.');
      records.push({name:(node.getAttribute('title')||node.getAttribute('text')||url).slice(0,300),url:url.trim(),folder});
      if(records.length>1000)throw Error('Máximo de 1000 entradas por importación.');
    }
    if(!records.length)throw Error('El archivo no contiene fuentes RSS.');
    return records;
  }
  function matchOPML(records,sources){
    const catalog=new Map();
    for(const source of sources){const key=feedKey(source.url);if(key&&!catalog.has(key))catalog.set(key,source);}
    const matched=[],unknown=[],seenURLs=new Set(),seenMemberships=new Set(),known=new Set();
    let duplicates=0;
    for(const record of records){
      const key=feedKey(record.url);
      if(key&&seenURLs.has(key))duplicates++;
      if(key)seenURLs.add(key);
      const source=key?catalog.get(key):null;
      if(!source){unknown.push({...record,reason:key?'No está en el catálogo público':'URL no admitida'});continue;}
      const membership=JSON.stringify([source.id,record.folder]);
      known.add(source.id);
      if(seenMemberships.has(membership))continue;
      seenMemberships.add(membership);matched.push({id:source.id,folder:record.folder});
    }
    return {total:records.length,knownCount:known.size,duplicates,matched,unknown};
  }
  function buildCSV(rows){
    const cell=value=>{
      let text=String(value??'');
      if(/^[\s]*[=+\-@]|^[\t\r\n]/.test(text))text="'"+text;
      return '"'+text.replace(/"/g,'""')+'"';
    };
    const lines=[['ID','Nombre','URL RSS','Sitio web','Carpetas personales','Tipo','Visibilidad','Estado del último chequeo','Motivo de importación']];
    for(const row of rows)lines.push([row.id,row.name,row.rss,row.website,row.folders,row.type,row.visible?'Visible':'Oculta',statusLabels[row.status]||statusLabels.unknown,row.reason]);
    return '\uFEFF'+lines.map(line=>line.map(cell).join(',')).join('\r\n');
  }
  const api=Object.freeze({feedKey,sourceKind,healthState,statusLabels,filterSources,buildOPML,readOPML,matchOPML,buildCSV});
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  else root.RadarSourceTools=api;
})(typeof globalThis!=='undefined'?globalThis:this);
