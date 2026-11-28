#!/usr/bin/env python3
"""Bounded agenda collection from explicitly registered RSS publishers."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests
import collect
from events import extract_event, iso, merge_events, parse_timestamp, validate_document

FEED_BYTE_LIMIT=8_000_000
MAX_FEED_ENTRIES=50
MAX_HTML_PAGES=12


def load_sources(catalog, config):
    settings=json.loads(Path(config).read_text())
    if not isinstance(settings,dict) or settings.get('version')!=1 or not isinstance(settings.get('sources'),list):
        raise ValueError('Invalid agenda source configuration')
    feeds={row['url']:row for row in collect.parse_opml(catalog)}
    selected=[];seen=set()
    for setting in settings['sources']:
        if not isinstance(setting,dict):raise ValueError('Invalid agenda source')
        url=setting.get('url');tz=setting.get('timezone')
        if url not in feeds or url in seen or feeds[url]['is_radar'] or urlsplit(url).scheme!='https':
            raise ValueError('Agenda feed must be a unique direct HTTPS catalog source')
        try:ZoneInfo(tz)
        except (ValueError,TypeError,ZoneInfoNotFoundError) as exc:raise ValueError('Explicit IANA timezone required') from exc
        selected.append({**feeds[url],'timezone':tz});seen.add(url)
    if not selected:raise ValueError('Agenda requires configured sources')
    return selected


def fetch_feed(url):
    parsed=urlsplit(url)
    if parsed.scheme!='https' or parsed.username or parsed.password or parsed.port not in (None,443) or not parsed.hostname or not collect.is_public_host(parsed.hostname):
        raise ValueError('RSS host is not public HTTPS')
    response=requests.get(url,headers=collect.HEADERS,stream=True,timeout=(5,14),allow_redirects=False)
    try:
        if response.status_code!=200:raise ValueError('RSS HTTP '+str(response.status_code))
        blocks=[];total=0
        for part in response.iter_content(chunk_size=32768):
            total+=len(part)
            if total>FEED_BYTE_LIMIT:raise ValueError('RSS document too large')
            blocks.append(part)
        return b''.join(blocks)
    finally:response.close()


def fetch_event_page(url,source):
    host=collect.page_image_host(url)
    allowed={collect.page_image_host(value) for value in (source.get('url',''),source.get('website',''))}
    if not host or host not in allowed:return None
    try:
        parsed=urlsplit(url)
        if parsed.scheme!='https' or parsed.port not in (None,443):return None
        if not collect.is_public_host(host) or not collect.page_image_allowed(url,host) or not collect.is_public_host(host):return None
        response=collect.read_bounded_response(url,accept='text/html, application/xhtml+xml',limit=500_000)
        if response and response[0] in ('text/html','application/xhtml+xml'):return response[1]
    except (requests.RequestException,ValueError,OSError):return None
    return None


def collect_document(sources,previous,now,direct_sources=()):
    if previous is not None:validate_document(previous)
    incoming=[];states=[];pages=0;diagnostics={}
    for source in sources:
        state={'source_id':source['id'],'source_name':source['name'],'url':source['url'],
               'timezone':source['timezone'],'checked_at':iso(now),'status':'ok','error':None}
        try:
            parsed=collect.feedparser.parse(fetch_feed(source['url']))
            entries=parsed.get('entries',[])
            if parsed.get('bozo') and not entries:raise ValueError('Invalid RSS document')
            for entry in entries[:MAX_FEED_ENTRIES]:
                item=extract_event(entry,source,now,diagnostics=diagnostics)
                if item is None:continue
                # Extra page lookup only for activity candidates, never general news.
                # A publisher may remove only the JSON-LD startDate when
                # cancelling, while its cached RSS still contains the old date.
                if pages<MAX_HTML_PAGES:
                    pages+=1
                    html=fetch_event_page(item['url'],source)
                    if html:item=extract_event(entry,source,now,html=html) or item
                incoming.append(item)
        except (requests.RequestException,ValueError,TypeError,OSError,KeyError) as exc:
            state['status']='error';state['error']=type(exc).__name__+': '+str(exc)[:300]
        states.append(state)
    if diagnostics:
        # Log only: why activity announcements stay pending (never published).
        print('Agenda, fechas en texto: '+', '.join(f'{reason}={count}' for reason,count in sorted(diagnostics.items())),file=sys.stderr)
    if direct_sources:
        import event_sources
        rss_ids={source['id'] for source in sources}
        if any(source['id'] in rss_ids for source in direct_sources):raise ValueError('Duplicate RSS/direct agenda source ID')
        direct_items,direct_states=event_sources.collect_sources(direct_sources,now)
        incoming.extend(direct_items);states.extend(direct_states)
    return merge_events(previous,incoming,states,now)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog',default='sources/feeds.opml')
    parser.add_argument('--config',default='sources/events.json')
    parser.add_argument('--out',default='web/data/events.json')
    parser.add_argument('--direct-config',default=None,help='Opt in to bounded official HTML/JSON-LD/ICS calendars')
    generation=parser.add_mutually_exclusive_group()
    generation.add_argument('--generation')
    generation.add_argument('--generation-from',help='Read generated_at from news metadata')
    args=parser.parse_args(argv)
    now=datetime.now(timezone.utc)
    if args.generation:now=parse_timestamp(args.generation)
    elif args.generation_from:
        now=parse_timestamp(json.loads(Path(args.generation_from).read_text())['generated_at'])
    output=Path(args.out)
    previous=None
    if output.exists():
        try:previous=validate_document(json.loads(output.read_text()))
        except (ValueError,TypeError,OSError) as exc:raise ValueError('Existing agenda is corrupt; refusing to overwrite') from exc
    direct_sources=[]
    if args.direct_config:
        import event_sources
        direct_sources=event_sources.load_sources(args.direct_config,args.catalog)
    doc=collect_document(load_sources(args.catalog,args.config),previous,now,direct_sources=direct_sources)
    output.parent.mkdir(parents=True,exist_ok=True)
    temporary=output.with_name(output.name+'.tmp')
    temporary.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')
    temporary.replace(output)
    return 0


if __name__=='__main__':raise SystemExit(main())
