#!/usr/bin/env python3
"""Pure, conservative event extraction and local-date agenda retention (v1).

Publication timestamps never stand in for an event date. No HTML is executed.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from html.parser import HTMLParser
import json
import re
from urllib.parse import urljoin
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from collect import entry_date, iso, safe_web_url, strip_tracking

HORIZON_DAYS = 90
MAX_ITEMS = 20_000
MAX_DOCUMENT_BYTES = 8_000_000
ACTIVITY = re.compile(r'\b(?:concierto|festival|feria|taller|seminario|charla|exposici[oó]n|exhibici[oó]n|encuentro|congreso|recital|funci[oó]n|obra de teatro|presentaci[oó]n|conversatorio|ciclo|jornada|estreno|marat[oó]n|corrida|visita guiada)\b',re.I)
REALIZATION = re.compile(r'(?:se\s+(?:realizar[aá]|celebrar[aá]|desarrollar[aá]|efectuar[aá])|tendr[aá]\s+lugar|se\s+llevar[aá]\s+a\s+cabo|(?:programad[oa]|agendad[oa])\s+para|(?:se\s+presentar[aá]|se\s+inaugurar[aá])|(?:este|el)\s+pr[oó]ximo)',re.I)
MONTHS = {name:i+1 for i,name in enumerate(('enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'))}
TEXT_DATE = re.compile(r'\b(?:(\d{4}-\d{2}-\d{2})|(\d{1,2})\s+de\s+('+ '|'.join(MONTHS)+r')\s+(?:de[l]?\s+)?(\d{4})|(\d{1,2})[/-](\d{1,2})[/-](\d{4})|(\d{1,2})\s+de\s+('+ '|'.join(MONTHS)+r')(?!\s+(?:de[l]?\s+)?\d))\b',re.I)
# A day and month without a year are completed only from the announcement's own
# local date: the next occurrence on or after it, and at most this many days later.
YEARLESS_WINDOW_DAYS = 90
EVENT_TYPES = {'Event','BusinessEvent','ChildrensEvent','ComedyEvent','CourseInstance','DanceEvent','DeliveryEvent','EducationEvent','EventSeries','ExhibitionEvent','Festival','FoodEvent','Hackathon','LiteraryEvent','MusicEvent','PublicationEvent','SaleEvent','ScreeningEvent','SocialEvent','SportsEvent','TheaterEvent','VisualArtsEvent'}
EVENT_LABELS = {'MusicEvent':'Música','TheaterEvent':'Teatro','DanceEvent':'Danza',
    'SportsEvent':'Deporte','ExhibitionEvent':'Exposición','VisualArtsEvent':'Artes visuales',
    'LiteraryEvent':'Literatura','ScreeningEvent':'Cine','Festival':'Festival',
    'EducationEvent':'Educación','CourseInstance':'Curso','BusinessEvent':'Encuentro empresarial',
    'ChildrensEvent':'Actividad infantil','ComedyEvent':'Comedia','FoodEvent':'Gastronomía',
    'SocialEvent':'Encuentro social','Hackathon':'Hackatón','SaleEvent':'Feria',
    'Event':'Actividad','EventSeries':'Ciclo'}
OPTIONAL_DETAILS = ('locality','event_type','price_text','is_free','preference_source_id')


def _detail_text(value):
    if not isinstance(value,str):return None
    return ' '.join(_html(value).text).strip()[:200] or None


def structured_details(obj):
    """Public facts with explicit structured evidence; titles never set price/place."""
    result={key:None for key in OPTIONAL_DETAILS if key!='preference_source_id'}
    result['_price_observed']='offers' in obj or 'isAccessibleForFree' in obj
    location=obj.get('location')
    if isinstance(location,dict):
        address=location.get('address')
        if isinstance(address,dict):result['locality']=_detail_text(address.get('addressLocality'))
    kinds=obj.get('@type',[])
    if isinstance(kinds,str):kinds=[kinds]
    if isinstance(kinds,list):
        labels=[EVENT_LABELS.get(kind.rsplit('/',1)[-1].rsplit('#',1)[-1]) for kind in kinds if isinstance(kind,str)]
        result['event_type']=next((label for label in labels if label and label!='Actividad'),None) or next((label for label in labels if label),None)
    explicit_free=obj.get('isAccessibleForFree')
    if type(explicit_free) is bool:result['is_free']=explicit_free
    offers=obj.get('offers',[])
    if isinstance(offers,dict):offers=[offers]
    if not isinstance(offers,list):return result
    prices=[];complete=bool(offers) and len(offers)<=30;labels=[]
    for offer in offers[:30]:
        if not isinstance(offer,dict):complete=False;continue
        value=offer.get('price',offer.get('lowPrice'))
        try:
            if type(value) not in (str,int,float):raise InvalidOperation
            price=Decimal(str(value))
            if not price.is_finite() or price<0:raise InvalidOperation
            prices.append(price)
            currency=_detail_text(offer.get('priceCurrency'))
            labels.append(str(value)+((' '+currency) if currency else ''))
        except (InvalidOperation,ValueError):complete=False
    if labels:result['price_text']=' / '.join(dict.fromkeys(labels))[:200]
    if prices:
        any_free=any(price==0 for price in prices);any_paid=any(price>0 for price in prices)
        if (any_free and any_paid) or (explicit_free is True and any_paid) or (explicit_free is False and any_free):
            result['is_free']=None
        elif type(explicit_free) is not bool and complete:
            result['is_free']=all(price==0 for price in prices)
    return result


def parse_timestamp(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})',value):
        raise ValueError('Invalid timestamp')
    try:
        stamp=datetime.fromisoformat(value.replace('Z','+00:00'))
        return stamp.astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise ValueError('Invalid timestamp') from exc


def local_date(value, zone):
    """Only complete ISO dates/datetimes, converted to the configured place."""
    if not isinstance(value,str):
        raise ValueError('Invalid event date')
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):
        return date.fromisoformat(value).isoformat()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?',value):
        raise ValueError('Event date needs an explicit year')
    dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    if dt.tzinfo:
        dt=dt.astimezone(zone)
    return dt.date().isoformat()


class EventHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.json_blocks=[]
        self.text=[]
        self.current=None
        self.ignore=0

    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):
            self.ignore+=1
        if tag=='script' and dict(attrs).get('type','').lower().split(';')[0].strip()=='application/ld+json':
            self.current=[]

    def handle_endtag(self,tag):
        if tag=='script' and self.current is not None:
            self.json_blocks.append(''.join(self.current));self.current=None
        if tag in ('script','style') and self.ignore:
            self.ignore-=1

    def handle_data(self,data):
        if self.current is not None:
            self.current.append(data)
        elif not self.ignore:
            self.text.append(data)


def _html(value):
    parser=EventHTML()
    parser.feed(str(value or '')[:500_000])
    return parser


def _jsonld_events(value, depth=0):
    if depth>12:
        return
    if isinstance(value,list):
        for part in value:
            yield from _jsonld_events(part,depth+1)
    elif isinstance(value,dict):
        kinds=value.get('@type',[])
        if isinstance(kinds,str):kinds=[kinds]
        if isinstance(kinds,list) and any(isinstance(k,str) and k.rsplit('/',1)[-1] in ('NewsArticle','Article','BlogPosting') for k in kinds):
            return
        if isinstance(kinds,list) and any(isinstance(k,str) and k.rsplit('/',1)[-1].rsplit('#',1)[-1] in EVENT_TYPES for k in kinds):
            yield value
        # Only explicit graph/mainEntity containers; never promote a NewsArticle.
        for key in ('@graph','mainEntity'):
            yield from _jsonld_events(value.get(key),depth+1)
        if 'ItemList' in kinds:yield from _jsonld_events(value.get('itemListElement'),depth+1)
        if 'ListItem' in kinds:yield from _jsonld_events(value.get('item'),depth+1)


def _related_event(obj, title, url):
    identities=[]
    for key in ('url','@id','mainEntityOfPage'):
        value=obj.get(key)
        if isinstance(value,dict):value=value.get('@id') or value.get('url')
        if value is not None:
            if not isinstance(value,str) or not value.strip():return False
            value=urljoin(url,value)
            if not safe_web_url(value):return False
            identities.append(strip_tracking(value))
    # An explicit identity on another URL cannot be rescued by a matching name.
    if identities:return all(identity==url for identity in identities)
    name=obj.get('name')
    if not isinstance(name,str):return False
    normalize=lambda value:re.sub(r'\W+',' ',value.casefold()).strip()
    name=normalize(name);title=normalize(title)
    meaningful=set(name.split())-{'el','la','los','las','de','del','en','y','para','un','una','al','con'}
    return len(meaningful)>=2 and (name in title or title in name)


def _status(text):
    if re.search(r'\b(?:cancelad[oa]|cancelled|canceled|EventCancelled|suspendid[oa])\b',text,re.I):return 'cancelled'
    if re.search(r'\b(?:aplazad[oa]|pospuest[oa]|postergad[oa]|EventPostponed|postponed)\b',text,re.I):return 'postponed'
    return 'scheduled'


def _yearless(day,month,anchor):
    """Next occurrence of day/month on or after anchor, within the window."""
    for year in (anchor.year,anchor.year+1):
        try:candidate=date(year,month,day)
        except ValueError:continue
        if candidate>=anchor:
            return candidate if (candidate-anchor).days<=YEARLESS_WINDOW_DAYS else None
    return None


def _text_date(text,zone,anchor=None,trace=None):
    """Return (date, rejected, year_inferred), distinguishing contradiction from omission.

    anchor is the local date of the announcement; without it a day and month
    without a year stays unverified. trace, when a list, receives the reason
    each date candidate was discarded (diagnostics only; never changes the result).
    """
    dates=[];inferred=False
    note=trace.append if trace is not None else (lambda reason:None)
    for match in TEXT_DATE.finditer(text):
        # Date must directly follow a future realization clause in its sentence.
        prefix=re.split(r'[.!?;\n]',text[:match.start()])[-1][-200:]
        clauses=list(REALIZATION.finditer(prefix))
        if not clauses:note('fecha_sin_clausula');continue
        clause=clauses[-1]
        # The date must be the immediate complement of the realization clause,
        # rather than a later announcement, registration or ticket-sale date.
        if not re.fullmatch(r'(?:\s+(?:el|d[ií]a|este|pr[oó]ximo|lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo))*\s*',prefix[clause.end():],re.I):note('fecha_no_inmediata');continue
        if re.search(r'\b(?:inscripci[oó]n|inscripciones|anuncio|publicaci[oó]n|entradas|reservas|postulaci[oó]n|venta)\b',prefix[:clause.start()],re.I):note('contexto_inscripcion');continue
        if re.search(r'\b(?:no|nunca|jam[aá]s|tampoco)\s*$',prefix[:clause.start()],re.I):note('negacion');return None,True,False
        suffix=re.split(r'[.!?;\n]',text[match.end():],maxsplit=1)[0]
        alternative=TEXT_DATE.search(suffix)
        if alternative and re.search(r'\b(?:o|u)\b',suffix[:alternative.start()],re.I):note('alternativa');return None,True,False
        if match[8]:
            if anchor is None:note('sin_ano_sin_ancla');continue
            candidate=_yearless(int(match[8]),MONTHS[match[9].lower()],anchor)
            if candidate is None:note('sin_ano_fuera_de_margen');continue
            dates.append(candidate.isoformat());inferred=True
            continue
        try:
            if match[1]:value=match[1]
            elif match[2]:value=f'{int(match[4]):04}-{MONTHS[match[3].lower()]:02}-{int(match[2]):02}'
            else:value=f'{int(match[7]):04}-{int(match[6]):02}-{int(match[5]):02}'
            dates.append(local_date(value,zone))
        except (ValueError,TypeError):return None,True,False
    if len(set(dates))==1:return dates[0],False,inferred
    if len(set(dates))>1:note('fechas_contradictorias')
    return None,len(set(dates))>1,False


# Furthest guard reached wins, so the log points at the deciding obstacle.
_DIAGNOSIS_ORDER=('fecha_sin_clausula','fecha_no_inmediata','contexto_inscripcion','sin_ano_sin_ancla','sin_ano_fuera_de_margen','alternativa','negacion','fechas_contradictorias')


def _diagnosis(trace,start,year_inferred):
    """Single label for why an activity announcement's text did or did not confirm a date."""
    if start:return 'confirmada_ano_deducido' if year_inferred else 'confirmada_texto'
    seen=[reason for reason in _DIAGNOSIS_ORDER if reason in trace]
    return seen[-1] if seen else 'sin_fecha_en_texto'


def extract_event(entry, source, now, html='', diagnostics=None):
    """Return confirmed/pending event or None for generic news/unsafe entries.

    source is a catalog row enriched with an explicit IANA timezone. Pending
    has null dates, reason=date_unverified/timezone_missing/postponed and the
    same identity as the eventual dated item.
    """
    if not isinstance(entry,dict):return None
    title=' '.join(_html(entry.get('title','')).text).strip()[:500]
    link=entry.get('link','')
    url=safe_web_url(link) if isinstance(link,str) else None
    if not title or not url:return None
    url=strip_tracking(url)
    body=' '.join(_html(entry.get('summary') or entry.get('description') or '').text)
    for content in entry.get('content',[]) or []:
        if isinstance(content,dict):body+=' '+' '.join(_html(content.get('value','')).text)
    page=_html(html)
    # Page text may contain calendars, sidebars or unrelated widget activities.
    # Only RSS announcement text is eligible for conservative textual dates.
    text=' '.join([title,body])[:500_000]
    objects=[]
    for block in page.json_blocks:
        try:objects.extend(obj for obj in _jsonld_events(json.loads(block)) if _related_event(obj,title,url))
        except (ValueError,TypeError,RecursionError):continue
    explicit=entry.get('ev_startdate') or entry.get('event_startdate')
    if not ACTIVITY.search(title) and not explicit and not objects:return None
    item={'id':sha256((source['id']+'\n'+url).encode()).hexdigest()[:24],
          'title':title,'url':url,'source_id':source['id'],'source_name':source['name'],
          'category':source['category'],'timezone':source.get('timezone') or None,
          'start_date':None,'end_date':None,'status':_status(title+' '+body),
          'status_explicit':False,
          'location':None,'announced_at':iso(entry_date(entry)),
          'first_seen_at':iso(now),'last_seen_at':iso(now),'date_evidence':None,
          'reason':'date_unverified'}
    item.update({key:None for key in OPTIONAL_DETAILS})
    parent=source.get('preference_source_id')
    if isinstance(parent,str) and 0<len(parent)<=128:item['preference_source_id']=parent
    if len(objects)==1:item.update(structured_details(objects[0]))
    # Status updates need not repeat an old activity date. Contradictory
    # structured/text evidence keeps the more restrictive state.
    priority={'scheduled':0,'postponed':1,'cancelled':2}
    for obj in objects:
        structured_status=_status(str(obj.get('eventStatus') or ''))
        if priority[structured_status]>priority[item['status']]:
            item['status']=structured_status
    rescheduled=any(str(obj.get('eventStatus') or '').rsplit('/',1)[-1]=='EventRescheduled' for obj in objects)
    try:zone=ZoneInfo(source.get('timezone',''))
    except (ValueError,TypeError,ZoneInfoNotFoundError):
        item['timezone']=None;item['reason']='timezone_missing';return item
    announced=entry_date(entry)
    # The announcement anchors a yearless date; a timestamp in the future is not trusted.
    anchor=min(announced,now).astimezone(zone).date() if announced else None
    trace=[] if diagnostics is not None else None
    text_start,text_rejected,year_inferred=_text_date(text,zone,anchor,trace) if ACTIVITY.search(title) else (None,False,False)
    if diagnostics is not None and ACTIVITY.search(title) and not (explicit or objects):
        # Counts only announcements whose date could come from the text alone.
        label=_diagnosis(trace,text_start,year_inferred)
        diagnostics[label]=diagnostics.get(label,0)+1
    if text_rejected:
        # This is not an incomplete repeat: merge must not restore a date
        # expressly negated or offered as an alternative by this update.
        item['_date_rejected']=True
        if item['status']=='postponed':item['reason']='postponed'
        return item
    start,end,kind,raw=None,None,None,None
    if rescheduled:
        # An explicit reschedule supersedes the original date still in RSS.
        # Several related objects or no replacement date cannot reactivate it.
        if len(objects)!=1 or not objects[0].get('startDate'):
            if item['status']!='cancelled':item['status']='postponed';item['reason']='postponed'
            return item
        obj=objects[0];start=obj['startDate'];end=obj.get('endDate');kind='jsonld';raw=str(start)
        location=obj.get('location')
        if isinstance(location,str):item['location']=location.strip()[:500] or None
        elif isinstance(location,dict) and isinstance(location.get('name'),str):item['location']=location['name'].strip()[:500] or None
    elif explicit:
        start=explicit;end=entry.get('ev_enddate') or entry.get('event_enddate');kind='rss';raw=str(explicit)
    elif objects:
        # More than one distinct Event on an article is ambiguous; no arbitrary pick.
        dated=[obj for obj in objects if obj.get('startDate')]
        if len(dated)==1:
            obj=dated[0];start=obj['startDate'];end=obj.get('endDate');kind='jsonld';raw=str(start)
            location=obj.get('location')
            if isinstance(location,str):item['location']=location.strip()[:500] or None
            elif isinstance(location,dict) and isinstance(location.get('name'),str):item['location']=location['name'].strip()[:500] or None
    if not start and ACTIVITY.search(title):
        start=text_start;kind='text';raw=start
    text_rescheduled=bool(re.search(r'\b(?:nueva fecha|reprogramad[oa])\b',text,re.I))
    if item['status']=='postponed' and kind=='text' and start and text_rescheduled and not any(_status(str(obj.get('eventStatus') or ''))!='scheduled' for obj in objects):
        item['status']='scheduled'
    if item['status']=='postponed':
        # EventPostponed's startDate describes the old date, not a new schedule.
        item['reason']='postponed';return item
    try:
        if not start:return item
        item['start_date']=local_date(start,zone)
        item['end_date']=local_date(end,zone) if end else None
        if item['end_date'] and item['end_date']<item['start_date']:raise ValueError('Reversed range')
        item['date_evidence']={'kind':kind,'value':raw[:1000],'url':url}
        if kind=='text' and year_inferred:item['date_evidence']['year_inferred']=True
        item['status_explicit']=item['status']=='scheduled' and (rescheduled or text_rescheduled)
        item.pop('reason',None)
    except (ValueError,TypeError,OverflowError):
        item['start_date']=None;item['end_date']=None
        if rescheduled and item['status']!='cancelled':
            item['status']='postponed';item['reason']='postponed'
    return item


def is_upcoming(item, now, horizon_days=HORIZON_DAYS):
    if item.get('status')!='scheduled' or not item.get('start_date') or not item.get('timezone'):return False
    try:
        today=now.astimezone(ZoneInfo(item['timezone'])).date()
        start=date.fromisoformat(item['start_date']);end=date.fromisoformat(item.get('end_date') or item['start_date'])
        return end>=today and start<=today+timedelta(days=horizon_days)
    except (ValueError,TypeError,ZoneInfoNotFoundError):return False


def _active(item,now):
    if item.get('start_date'):
        today=now.astimezone(ZoneInfo(item['timezone'])).date()
        return date.fromisoformat(item.get('end_date') or item['start_date'])>=today
    # Undated announcements have bounded retention, independent of publication.
    return parse_timestamp(item['last_seen_at'])>=now-timedelta(days=90)


def merge_events(previous, incoming, source_states, now, *, authoritative_details=False):
    """Keep active cache even when sources fail; update source+URL identities.

    items also retains dated future events beyond the display horizon, so a
    temporary omission cannot erase them. Consumers call is_upcoming/filter.
    """
    if previous is not None:validate_document(previous)
    cache={item['id']:dict(item) for item in (previous or {}).get('items',[])+(previous or {}).get('pending',[])}
    for item in incoming:
        item=dict(item)
        # A calendar UID survives URL/title/date changes. Absorb the URL-based
        # representation of the same official detail when formats overlap or
        # one feed becomes unavailable; distinct UIDs remain distinct.
        aliases=[old for old in cache.values() if old['id']!=item['id']
                 and old['source_id']==item['source_id'] and old['url']==item['url']
                 and bool(old.get('calendar_uid'))!=bool(item.get('calendar_uid'))]
        if len(aliases)==1:
            alias=aliases[0]
            if item.get('calendar_uid'):cache.pop(alias['id'])
            else:
                item['id']=alias['id'];item['calendar_uid']=alias['calendar_uid']
            old=cache.get(item['id']) or alias
        else:old=cache.get(item['id'])
        title_missing=item.pop('_title_missing',False) is True
        url_missing=item.pop('_calendar_url_missing',False) is True
        price_observed=item.pop('_price_observed',False) is True
        if title_missing:
            if not old:continue
            item['title']=old['title']
        if url_missing and old:item['url']=old['url']
        date_rejected=item.pop('_date_rejected',False) is True
        if old:
            item['first_seen_at']=old['first_seen_at']
            if not item.get('announced_at'):item['announced_at']=old.get('announced_at')
            for key in OPTIONAL_DETAILS+('calendar_uid',):
                if authoritative_details and key in OPTIONAL_DETAILS and key in item:continue
                if price_observed and key in ('is_free','price_text'):continue
                if item.get(key) is None and key in old:item[key]=old[key]
            changed_date=bool(old.get('start_date') and item.get('start_date') and old['start_date']!=item['start_date'] and (item.get('date_evidence') or {}).get('kind') in ('rss','jsonld','calendar'))
            reactivated=bool(item.get('start_date') and (item.get('status_explicit') is True or changed_date))
            if date_rejected:
                # Preserve known restrictions, without rescuing a rejected date.
                if old['status'] in ('cancelled','postponed') and item['status']=='scheduled':
                    item['status']=old['status']
                    if old['status']=='postponed':item['reason']='postponed'
            elif old['status'] in ('cancelled','postponed') and item['status']=='scheduled' and not reactivated:
                # Downloading the original dated announcement again is not a
                # reactivation. An undated postponed item requires an explicit
                # reschedule because its old date is deliberately no longer active.
                for key in ('status','start_date','end_date','date_evidence','timezone'):
                    item[key]=old[key]
                item['status_explicit']=False
                if 'reason' in old:item['reason']=old['reason']
                else:item.pop('reason',None)
            # A cancellation with no repeated date preserves its verified activity date.
            elif item['status']=='cancelled' and not item.get('start_date') and old.get('start_date'):
                for key in ('start_date','end_date','date_evidence','timezone'):item[key]=old[key]
                item.pop('reason',None)
            # An incomplete repeat cannot silently erase a verified future date.
            elif not item.get('start_date') and item['status']=='scheduled' and old.get('start_date'):
                for key in ('start_date','end_date','date_evidence','timezone','status'):item[key]=old[key]
                item.pop('reason',None)
        cache[item['id']]=item
    active=[item for item in cache.values() if _active(item,now)]
    result={'version':1,'generated_at':iso(now),'horizon_days':HORIZON_DAYS,
            'items':sorted([i for i in active if i.get('start_date')],key=lambda i:(i['start_date'],i['id'])),
            'pending':sorted([i for i in active if not i.get('start_date')],key=lambda i:i['id']),
            'sources':source_states}
    validate_document(result)
    return result


def validate_document(doc):
    """Validate an entire events-v1 payload or raise ValueError, never truncate."""
    def fail(message):raise ValueError('Invalid events document: '+message)
    def string(value,limit=1000):return isinstance(value,str) and bool(value.strip()) and len(value)<=limit
    def stamp(value):
        try:parse_timestamp(value);return True
        except (ValueError,TypeError,OverflowError):return False
    def day(value):
        try:return bool(isinstance(value,str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}',value) and date.fromisoformat(value))
        except ValueError:return False
    def zone(value):
        try:return bool(isinstance(value,str) and ZoneInfo(value))
        except (ValueError,ZoneInfoNotFoundError):return False
    if not isinstance(doc,dict) or type(doc.get('version')) is not int or doc['version']!=1:fail('version')
    if type(doc.get('horizon_days')) is not int or doc['horizon_days']!=90:fail('horizon_days')
    if not stamp(doc.get('generated_at')):fail('generated_at')
    if not all(isinstance(doc.get(key),list) for key in ('items','pending','sources')):fail('collections')
    if len(doc['items'])+len(doc['pending'])>MAX_ITEMS or len(doc['sources'])>1000:fail('collection size')
    ids=set()
    for key in ('items','pending'):
        for item in doc[key]:
            if not isinstance(item,dict):fail('item')
            if not {'timezone','start_date','end_date','date_evidence'}.issubset(item):fail('missing date fields')
            for name,limit in (('id',128),('title',500),('url',4000),('source_id',128),('source_name',500),('category',500)):
                if not string(item.get(name),limit):fail(name)
            if item['id'] in ids:fail('duplicate id')
            ids.add(item['id'])
            if not safe_web_url(item['url']):fail('url')
            if item.get('status') not in ('scheduled','cancelled','postponed'):fail('status')
            if 'status_explicit' in item and type(item['status_explicit']) is not bool:fail('status_explicit')
            if not stamp(item.get('first_seen_at')) or not stamp(item.get('last_seen_at')):fail('seen timestamp')
            if parse_timestamp(item['first_seen_at'])>parse_timestamp(item['last_seen_at']) or parse_timestamp(item['last_seen_at'])>parse_timestamp(doc['generated_at']):fail('seen order')
            if 'announced_at' not in item or (item['announced_at'] is not None and not stamp(item['announced_at'])):fail('announced_at')
            if 'location' not in item or (item['location'] is not None and not string(item['location'],500)):fail('location')
            for name,limit in (('locality',200),('event_type',200),('price_text',200),('preference_source_id',128),('calendar_uid',1000)):
                if name in item and item[name] is not None and not string(item[name],limit):fail(name)
            if 'is_free' in item and item['is_free'] is not None and type(item['is_free']) is not bool:fail('is_free')
            if key=='items':
                if not zone(item.get('timezone')) or not day(item.get('start_date')):fail('confirmed date/timezone')
                if item.get('end_date') is not None and (not day(item['end_date']) or item['end_date']<item['start_date']):fail('end_date')
                if item['status']=='postponed':fail('postponed date')
                evidence=item.get('date_evidence')
                if not isinstance(evidence,dict) or evidence.get('kind') not in ('rss','jsonld','text','calendar') or not string(evidence.get('value'),1000) or not string(evidence.get('url'),4000) or not safe_web_url(evidence['url']):fail('date_evidence')
                if 'year_inferred' in evidence and (evidence['year_inferred'] is not True or evidence['kind']!='text'):fail('year_inferred')
            else:
                if item.get('start_date') is not None or item.get('end_date') is not None:fail('pending dates')
                if item.get('reason') not in ('date_unverified','timezone_missing','postponed'):fail('pending reason')
                if item.get('timezone') is not None and not zone(item['timezone']):fail('pending timezone')
                if item.get('date_evidence') is not None:fail('pending evidence')
    source_ids=set()
    for source in doc['sources']:
        if not isinstance(source,dict) or not string(source.get('source_id'),128) or source.get('status') not in ('ok','error'):fail('source status')
        if not {'source_name','url','timezone','checked_at','error'}.issubset(source):fail('source fields')
        if source['source_id'] in source_ids:fail('duplicate source')
        source_ids.add(source['source_id'])
        for key in ('source_name','url','timezone','checked_at','error'):
            value=source[key]
            if key=='error' and value is None:continue
            if key=='checked_at' and not stamp(value):fail('source checked_at')
            elif key=='timezone' and not zone(value):fail('source timezone')
            elif key=='url' and (not string(value,4000) or not safe_web_url(value)):fail('source url')
            elif key not in ('checked_at','timezone','url') and not string(value,1000):fail('source '+key)
        if parse_timestamp(source['checked_at'])>parse_timestamp(doc['generated_at']):fail('source timestamp')
        if (source['status']=='ok') != (source['error'] is None):fail('source error state')
    try:
        if len((json.dumps(doc,ensure_ascii=False,allow_nan=False,indent=2)+'\n').encode())>MAX_DOCUMENT_BYTES:fail('document size')
    except (TypeError,ValueError,OverflowError,RecursionError) as exc:
        raise ValueError('Invalid events document serialization') from exc
    return doc
