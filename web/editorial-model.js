"use strict";
/* Small, deterministic editorial selections. Publisher text is never rewritten. */
(() => {
  const DAY = 86400000;
  const fold = value => String(value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
  const headline = value => (fold(value).replace(/\s+y mas\s*[.!]?$/,'').match(/[a-z]+|[+\-−]?\d+(?:[.,:/-]\d+)*|[%$€£]/g) || []).join(' ');
  const types = Object.freeze({news:'news', noticia:'news', noticias:'news',
    opinion:'opinion', analysis:'analysis', analisis:'analysis',
    press_release:'press_release', 'press release':'press_release', comunicado:'press_release',
    'comunicado de prensa':'press_release'});
  function contentType(item) { const key = fold(item?.content_type); return Object.hasOwn(types,key) ? types[key] : 'unknown'; }
  function instant(item) {
    const stamp = Date.parse(item?.published_at || item?.first_seen_at || '');
    return Number.isFinite(stamp) ? stamp : null;
  }
  function originalURL(value) {
    try {
      const url = new URL(value);
      if (!['http:', 'https:'].includes(url.protocol)) return '';
      url.hash = '';
      for (const key of [...url.searchParams.keys()]) {
        if (/^utm_/i.test(key) || /^(fbclid|gclid)$/i.test(key)) url.searchParams.delete(key);
      }
      return url.href;
    } catch { return ''; }
  }
  const array = value => Array.isArray(value) ? value : [];
  function outlet(item) { return fold(item.publisher || item.source); }
  function variants(item) {
    return [{id:item.id, url:item.url, title:item.title, publisher:item.publisher || item.source,
      source:item.source, source_id:array(item.source_ids)[0], category:array(item.categories)[0],
      published_at:item.published_at, first_seen_at:item.first_seen_at,
      ...(item.content_type ? {content_type:item.content_type, content_type_label:item.content_type_label} : {})},
    ...array(item.also_in).filter(x => x && typeof x === 'object')];
  }
  function coverage(item) {
    const publishers = new Set(variants(item).map(outlet).filter(Boolean));
    const explicit = Number.isInteger(item.coverage) && item.coverage > 0 ? item.coverage : 1;
    return Math.max(explicit, publishers.size, 1);
  }
  function filterSources(items, hiddenSources = [], catalog = [], mutedWords = []) {
    const hidden = new Set(hiddenSources), blocked = array(mutedWords).map(fold).filter(Boolean);
    if (!hidden.size && !blocked.length) return array(items).slice();
    const sources = new Map(array(catalog).map(source => [source.id,source]));
    const allowed = variant => variant.source_id && !hidden.has(variant.source_id) && !blocked.some(word =>
      fold([variant.title,variant.summary,variant.publisher,variant.source].join(' ')).includes(word));
    const selected = [];
    for (const item of array(items)) {
      const entries = variants(item);
      // Collector and saved snapshots preserve source_ids[0] as the credited lead.
      entries[0].summary = item.summary; entries[0].image = item.image;
      const visible = entries.filter(allowed), lead = visible[0];
      if (!lead) continue; // Surviving feed IDs alone never justify guessed text.
      if (visible.length === entries.length && !array(item.source_ids).some(id => hidden.has(id))) {
        selected.push(item); continue;
      }
      const source = sources.get(lead.source_id), replaced = lead !== entries[0];
      const excluded = new Set(entries.filter(variant => !allowed(variant)).map(variant => variant.source_id));
      const ids = [lead.source_id,...array(item.source_ids).filter(id => !hidden.has(id) && !excluded.has(id))];
      const copy = {...item, source_ids:[...new Set(ids)],
        editorial_member_ids:[...new Set([item.id,...visible.map(variant => variant.id)].filter(Boolean))],
        categories:[...new Set(visible.map(variant => variant.category || sources.get(variant.source_id)?.category).filter(Boolean))],
        also_in:visible.slice(1).map(variant => ({...variant}))};
      if (replaced) {
        Object.assign(copy,{title:lead.title,url:lead.url,publisher:lead.publisher,
          source:lead.source || source?.name || lead.publisher,
          published_at:lead.published_at || null, first_seen_at:lead.first_seen_at || null,
          summary:lead.summary || '', image:lead.image || null, is_radar:Boolean(source?.is_radar)});
        delete copy.content_type; delete copy.content_type_label;
        if (lead.content_type) { copy.content_type = lead.content_type; copy.content_type_label = lead.content_type_label; }
      }
      copy.coverage = Math.max(1,new Set(visible.map(outlet).filter(Boolean)).size);
      selected.push(copy);
    }
    return selected;
  }
  function groupStories(items) {
    const groups = [], byTitle = new Map(), byURL = new Map();
    for (const item of array(items)) {
      if (!item || typeof item !== 'object') continue;
      const text = headline(item.title), stamp = instant(item), url = originalURL(item.url);
      // Full-title equality keeps numbers, dates, places and negation significant.
      // Short/generic headlines and unknown dates never justify a title merge.
      const key = text.split(' ').length >= 7 ? text : '';
      const candidates = new Set([...(key ? byTitle.get(key) || [] : []), ...(url ? byURL.get(url) || [] : [])]);
      let match = -1;
      for (const index of candidates) {
        const lead = groups[index], date = instant(lead);
        if (stamp === null || date === null || Math.abs(stamp - date) > DAY) continue;
        const sameURL = url && variants(lead).some(alt => originalURL(alt.url) === url);
        const independent = outlet(item) && outlet(lead) && outlet(item) !== outlet(lead) &&
          !array(item.source_ids).some(id => array(lead.source_ids).includes(id));
        const syndicated = (item.is_radar || lead.is_radar) && outlet(item) && outlet(item) === outlet(lead) &&
          !array(item.source_ids).some(id => array(lead.source_ids).includes(id));
        if (sameURL || (independent || syndicated) && key && headline(lead.title) === key) { match = index; break; }
      }
      if (match < 0) {
        const index = groups.length;
        groups.push(item);
        if (key) byTitle.set(key, [...byTitle.get(key) || [], index]);
        for (const variant of variants(item)) {
          const identity = originalURL(variant.url);
          if (identity) byURL.set(identity, [...byURL.get(identity) || [], index]);
        }
        continue;
      }
      const lead = groups[match], all = [...variants(lead), ...variants(item)], seen = new Set();
      const alternatives = [];
      for (const variant of all) {
        const identity = originalURL(variant.url);
        if (!identity || seen.has(identity)) continue;
        seen.add(identity);
        if (identity !== originalURL(lead.url)) alternatives.push({...variant});
        byURL.set(identity, [...new Set([...(byURL.get(identity) || []), match])]);
      }
      const merged = {...lead,
        editorial_member_ids:[...new Set([lead.id,item.id,...array(lead.editorial_member_ids),...array(item.editorial_member_ids),
          ...all.map(variant => variant.id)].filter(Boolean))],
        source_ids:[...new Set([...array(lead.source_ids), ...array(item.source_ids)])],
        categories:[...new Set([...array(lead.categories), ...array(item.categories)])],
        also_in:alternatives};
      merged.coverage = Math.max(coverage(merged), coverage(lead), coverage(item));
      groups[match] = merged;
    }
    return groups;
  }
  function recent(items, now) {
    const time = now instanceof Date ? now.getTime() : Number(now);
    if (!Number.isFinite(time)) return [];
    const dated = groupStories(items).filter(item => {
      const stamp = instant(item);
      return stamp !== null && stamp <= time && time - stamp <= 2 * DAY;
    });
    const today = dated.filter(item => time - instant(item) <= DAY);
    // Preserve the existing briefing's 24/48-hour scope without padding stale news.
    return (today.length >= 7 ? today : dated).sort((a,b) => coverage(b) - coverage(a) || instant(b) - instant(a));
  }
  function diverse(items, limit) {
    const selected = [], used = new Set();
    for (const item of items) {
      const category = array(item.categories)[0] || '';
      if (used.has(category)) continue;
      selected.push(item); used.add(category);
      if (selected.length >= limit) return selected;
    }
    for (const item of items) {
      if (selected.includes(item)) continue;
      selected.push(item);
      if (selected.length >= limit) break;
    }
    return selected;
  }
  function selectDigest(items, now = Date.now(), limit = 7) {
    const count = Number.isFinite(Number(limit)) ? Math.max(0, Math.min(7, Math.floor(Number(limit)))) : 7;
    return count ? diverse(recent(items, now), count) : [];
  }
  function selectLocal(items, categories, now = Date.now()) {
    const interests = categories === undefined ? null : new Set(array(categories));
    const pool = array(items).filter(item => array(item?.categories).some(category =>
      /^0[478]\s*-/.test(category) && (!interests || interests.has(category))));
    return diverse(recent(pool, now), 3);
  }
  window.RadarEditorial = Object.freeze({groupStories, contentType, selectDigest, selectLocal, filterSources});
})();
