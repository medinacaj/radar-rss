"""Conditional HTTP fetches keep feed identity and cached news; no network."""
from datetime import datetime, timezone
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import collect

class Response:
    def __init__(self,status=200,headers=None,body=b'<rss/>'):
        self.status_code=status;self.headers=headers or {};self.body=body;self.closed=False
    def raise_for_status(self):pass
    def iter_content(self,chunk_size):
        yield self.body
    def close(self):self.closed=True

class ConditionalFeedsTests(unittest.TestCase):
    def test_records_validators_after_full_200_and_uses_them_for_304(self):
        cache={}
        response=Response(headers={'ETag':'"abc"','Last-Modified':'Sun, 01 Nov 2026 10:00:00 GMT'})
        with patch.object(collect,'is_public_host',return_value=True),patch.object(collect.requests,'get',return_value=response):
            self.assertEqual(collect.get_feed('https://feed.test/rss',cache),b'<rss/>')
        self.assertEqual(cache['http_etag'],'"abc"')
        with patch.object(collect,'is_public_host',return_value=True),patch.object(collect.requests,'get',return_value=Response(304)) as get:
            self.assertIsNone(collect.get_feed('https://feed.test/rss',cache))
            self.assertEqual(get.call_args.kwargs['headers']['If-None-Match'],'"abc"')
            self.assertIn('If-Modified-Since',get.call_args.kwargs['headers'])
        self.assertTrue(response.closed)

    def test_redirect_does_not_forward_validators_and_new_url_does_not_reuse_them(self):
        cache={'http_url':'https://feed.test/rss','http_etag':'"private-tag"'}
        with patch.object(collect,'is_public_host',return_value=True),patch.object(collect.requests,'get',side_effect=[Response(302,{'Location':'https://other.test/rss'}),Response()]) as get:
            collect.get_feed('https://feed.test/rss',cache)
            self.assertNotIn('If-None-Match',get.call_args_list[1].kwargs['headers'])
        cache={'http_url':'https://old.test/rss','http_etag':'"private-tag"'}
        with patch.object(collect,'is_public_host',return_value=True),patch.object(collect.requests,'get',return_value=Response()) as get:
            collect.get_feed('https://new.test/rss',cache)
            self.assertNotIn('If-None-Match',get.call_args.kwargs['headers'])

    def test_304_keeps_articles_and_first_detection_with_current_generation(self):
        now=datetime(2026,11,1,12,tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);opml=base/'feeds.opml';out=base/'web'/'data';out.mkdir(parents=True)
            opml.write_text('<opml><body><outline text="04 - Chile"><outline text="Diario" xmlUrl="https://feed.test/rss"/></outline></body></opml>')
            feed=collect.parse_opml(opml)[0]
            story={'id':'kept','title':'Noticia de prueba','url':'https://feed.test/story','publisher':'Diario','source':'Diario','source_ids':[feed['id']],'categories':['04 - Chile'],'published_at':'2026-11-01T10:00:00Z','first_seen_at':'2026-11-01T10:02:00Z'}
            (out/'articles.json').write_text(json.dumps({'items':[story]}))
            (out/'status.json').write_text(json.dumps({'feeds':[{'id':feed['id'],'state':'ok','count':1,'last_published_at':story['published_at'],'http_url':feed['url'],'http_etag':'"abc"'}]}))
            with patch.object(collect,'NOW',return_value=now),patch.object(collect,'is_public_host',return_value=True),patch.object(collect.requests,'get',return_value=Response(304)):
                collect.collect(opml,out,45,1,12,conditional=True)
            articles=json.loads((out/'articles.json').read_text())
            self.assertEqual(articles['items'][0]['first_seen_at'],story['first_seen_at'])
            status=json.loads((out/'status.json').read_text())
            self.assertEqual(status['checked_at'],collect.iso(now))
            self.assertEqual(status['feeds'][0]['state'],'ok')
            self.assertTrue(status['feeds'][0]['http_not_modified'])

    def test_invalid_200_does_not_commit_validators_or_turn_a_later_304_into_success(self):
        source={'id':'test','name':'Diario','category':'04 - Chile','url':'https://feed.test/rss'}
        now=datetime(2026,11,1,12,tzinfo=timezone.utc)
        with patch.object(collect,'is_public_host',return_value=True),patch.object(collect.requests,'get',return_value=Response(headers={'ETag':'"broken"'},body=b'not RSS')):
            items,status=collect.get_one(source,now,12,{})
            self.assertEqual(status['state'],'error')
            self.assertNotIn('http_etag',status)
        with patch.object(collect,'is_public_host',return_value=True),patch.object(collect.requests,'get',return_value=Response(304)) as get:
            items,status=collect.get_one(source,now,12,status)
            self.assertNotIn('If-None-Match',get.call_args.kwargs['headers'])
            self.assertEqual(status['state'],'error')
            self.assertIsNone(status['last_success_at'])

    def test_missing_prior_articles_forces_unconditional_download(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);opml=base/'feeds.opml';out=base/'web'/'data';out.mkdir(parents=True)
            opml.write_text('<opml><body><outline text="04 - Chile"><outline text="Diario" xmlUrl="https://feed.test/rss"/></outline></body></opml>')
            feed=collect.parse_opml(opml)[0]
            (out/'status.json').write_text(json.dumps({'feeds':[{'id':feed['id'],'http_url':feed['url'],'http_etag':'"abc"'}]}))
            with patch.object(collect,'is_public_host',return_value=True),patch.object(collect.requests,'get',return_value=Response(body=b'<rss><channel/></rss>')) as get:
                collect.collect(opml,out,45,1,12,conditional=True)
                self.assertNotIn('If-None-Match',get.call_args.kwargs['headers'])
