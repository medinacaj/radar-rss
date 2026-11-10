"""Research survives both the age window and a busy news archive (no network)."""
import contextlib
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import collect

NOW=datetime(2026,11,10,15,tzinfo=timezone.utc)
RESEARCH='11 - Investigación y Gestión'
NEWS='01 - Inteligencia Artificial'
OPML='''<opml><body>
<outline text="01 - Inteligencia Artificial"><outline title="MEDIO — Noticias" xmlUrl="https://news.example/rss"/></outline>
<outline text="11 - Investigación y Gestión"><outline title="MEDIO — Revista Uno" xmlUrl="https://research.example/rss"/><outline title="MEDIO — Revista Dos" xmlUrl="https://second.example/rss"/></outline>
</body></opml>'''


def story(source,identity,days=0,**fields):
    stamp=collect.iso(NOW-timedelta(days=days))
    return dict(id=identity,title='Estudio '+identity,url='https://publisher.example/'+identity,
                published_at=stamp,first_seen_at=stamp,source=source['name'],publisher=source['name'],
                source_ids=[source['id']],categories=[source['category']],summary='Extracto del editor',
                image=None,is_radar=False,**fields)


def collect_documents(fresh,cached=None,days=45,failed=False):
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);opml=root/'feeds.opml';opml.write_text(OPML)
        out=root/'data';sources=collect.parse_opml(opml)
        if cached:collect.write_json(out/'articles.json',{'items':cached(sources)})
        def fetch(source,now,limit):
            items=fresh(source) if not failed else []
            return items,dict(id=source['id'],name=source['name'],category=source['category'],
                              state='error' if failed else 'ok' if items else 'empty',count=len(items),
                              last_success_at=None if failed else collect.iso(now),last_published_at=None,error=None)
        with patch.object(collect,'NOW',return_value=NOW),patch.object(collect,'get_one',side_effect=fetch),contextlib.redirect_stdout(io.StringIO()):
            result=collect.collect(opml,out,days=days,workers=1,max_per_feed=50)
        return {p.name:json.loads(p.read_text()) for p in out.glob('*.json')},result


class ResearchRetentionTests(unittest.TestCase):
    def test_research_uses_two_years_and_news_keeps_45_days(self):
        def fresh(source):
            if source['url']=='https://research.example/rss':
                return [story(source,'paper-50',50),story(source,'paper-730',730),story(source,'paper-731',731)]
            if source['category']==NEWS:return [story(source,'news-44',44),story(source,'news-46',46)]
            return []
        docs,result=collect_documents(fresh)
        items=docs['articles.json']['items'];self.assertEqual({x['id'] for x in items},{'paper-50','paper-730','news-44'})
        self.assertEqual(next(x for x in items if x['id']=='paper-730')['published_at'],collect.iso(NOW-timedelta(days=730)))
        self.assertEqual(result['research_articles'],2)

    def test_custom_news_window_does_not_expire_research(self):
        docs,_=collect_documents(lambda source:[story(source,'paper',400)] if source['url']=='https://research.example/rss' else [story(source,'old-news',8)] if source['category']==NEWS else [],days=7)
        self.assertEqual([x['id'] for x in docs['articles.json']['items']],['paper'])

    def test_cached_categories_cannot_grant_retention_without_a_current_source(self):
        def cached(sources):
            normal=story(sources[0],'forged',300);normal['categories']=[RESEARCH]
            retired=story(sources[1],'retired',300);retired['source_ids']=['removed']
            return [normal,retired,story(sources[1],'valid-cache',300),story(sources[1],'expired-cache',731)]
        docs,_=collect_documents(lambda _:[],cached,failed=True)
        self.assertEqual([x['id'] for x in docs['articles.json']['items']],['valid-cache'])

    def test_research_survives_candidate_and_final_caps_and_stays_chronological(self):
        def fresh(source):
            if source['category']==NEWS:
                return [story(source,f'news-{i}',i/100000) for i in range(7600)]
            if source['url']=='https://research.example/rss':
                return [story(source,f'paper-{i}',200+i/1000) for i in range(240)]
            return []
        docs,result=collect_documents(fresh)
        items=docs['articles.json']['items'];papers=[x for x in items if RESEARCH in x['categories']]
        self.assertEqual(len(items),5000);self.assertEqual(len(papers),200);self.assertEqual(result['research_articles'],200)
        self.assertEqual({x['id'] for x in papers},{f'paper-{i}' for i in range(200)})
        dates=[x['published_at'] for x in items];self.assertEqual(dates,sorted(dates,reverse=True))
        meta=docs['meta.json'];joined=docs['latest.json']['items']+[x for name in meta['archive_files'] for x in docs[name]['items']]
        self.assertEqual(joined,items);self.assertEqual(meta['total_articles'],5000)
        self.assertEqual(len(docs['latest.json']['items']),300);self.assertEqual(len(meta['archive_files']),16)

    def test_small_research_pool_does_not_leave_empty_capacity(self):
        docs,_=collect_documents(lambda source:[story(source,f'news-{i}') for i in range(5010)] if source['category']==NEWS else [story(source,'paper',200)] if source['url']=='https://research.example/rss' else [])
        items=docs['articles.json']['items'];self.assertEqual(len(items),5000);self.assertEqual(items[-1]['id'],'paper')

    def test_grouped_papers_preserve_both_publishers_and_refresh_from_cache(self):
        title='La investigación analiza nuevos procesos productivos para mejorar las empresas'
        def fresh(source):
            if source['category']==RESEARCH:
                item=story(source,source['id'],200);item['title']=title;return [item]
            return []
        docs,_=collect_documents(fresh);items=docs['articles.json']['items']
        self.assertEqual(len(items),1);self.assertEqual(items[0]['coverage'],2);self.assertEqual(len(items[0]['also_in']),1)
        again,_=collect_documents(lambda _:[],lambda _:deepcopy(items),failed=True)
        self.assertEqual(again['articles.json']['items'][0]['published_at'],items[0]['published_at'])
        self.assertEqual(again['articles.json']['items'][0]['source_ids'],items[0]['source_ids'])

if __name__=='__main__':unittest.main()
