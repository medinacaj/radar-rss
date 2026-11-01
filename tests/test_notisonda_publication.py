"""Public HTTP boundaries follow the renamed site; all network is replaced offline."""
from contextlib import redirect_stdout
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import check_public_health
import recover_history
import recover_events
from insights import write_feeds

class NotisondaPublicationTests(unittest.TestCase):
    def test_health_requests_current_pages_path(self):
        urls=[]
        def fetch(request,timeout):
            urls.append(request.full_url)
            return io.BytesIO(b'{"version":2,"total_articles":5000}')
        with patch.object(check_public_health,'urlopen',fetch):
            result=check_public_health.read_json('meta.json')
        self.assertEqual(urls,['https://medinacaj.github.io/radar-rss/data/meta.json'])
        self.assertEqual(result['total_articles'],5000)

    def test_news_recovery_downloads_both_documents_from_current_path(self):
        urls=[]
        docs={'articles.json':{'generated_at':'2026-10-28T19:00:00Z','items':[{'id':str(i)} for i in range(50)]},
              'status.json':{'checked_at':'2026-10-28T19:00:00Z','feeds':[{'id':'retained'}]}}
        def fetch(request,timeout):
            urls.append(request.full_url)
            return io.BytesIO(json.dumps(docs[request.full_url.rsplit('/',1)[-1]]).encode())
        with tempfile.TemporaryDirectory() as directory,patch.object(recover_history,'urlopen',fetch),redirect_stdout(io.StringIO()):
            recover_history.restore(Path(directory))
            self.assertEqual(json.loads((Path(directory)/'articles.json').read_text()),docs['articles.json'])
        self.assertEqual(urls,['https://medinacaj.github.io/radar-rss/data/articles.json','https://medinacaj.github.io/radar-rss/data/status.json'])

    def test_agenda_download_uses_current_path(self):
        urls=[]
        def fetch(request,timeout):
            urls.append(request.full_url)
            return io.BytesIO(b'{"version":1,"items":[],"pending":[]}')
        with patch.object(recover_events,'urlopen',fetch):
            result=recover_events.download('events.json')
        self.assertEqual(urls,['https://medinacaj.github.io/radar-rss/data/events.json'])
        self.assertEqual(result['pending'],[])

    def test_generated_rss_uses_new_identity_and_preserves_story_identity_and_attribution(self):
        now=datetime(2026,10,28,19,tzinfo=timezone.utc)
        category='01 - Ciencia'
        article={'id':'story-1','title':'Un avance científico','url':'https://publisher.example/story',
                 'publisher':'MEDIO — Medio original','summary':'Extracto del medio.',
                 'published_at':now.isoformat(),'coverage':3,'categories':[category],'source_ids':['original']}
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)
            write_feeds(folder,[article],[{'id':'original','category':category}],now)
            for name,title,link in [('mas-cubierto.xml','Radar-RSS · Lo más cubierto','https://medinacaj.github.io/radar-rss/'),
                                    ('ciencia.xml','Radar-RSS · Ciencia','https://medinacaj.github.io/radar-rss/#categoria/01%20-%20Ciencia')]:
                channel=ET.parse(folder/name).getroot().find('channel')
                self.assertEqual(channel.findtext('title'),title)
                self.assertEqual(channel.findtext('link'),link)
                item=channel.find('item')
                self.assertEqual(item.findtext('guid'),'radar-story-1')
                self.assertEqual(item.findtext('link'),'https://publisher.example/story')
                self.assertEqual(item.findtext('source'),'Medio original')
                self.assertEqual(item.find('source').get('url'),'https://medinacaj.github.io/radar-rss/')

    @unittest.skipUnless(shutil.which('node'),'Node no disponible')
    def test_cache_migration_behavior(self):
        result=subprocess.run(['node','tests/test_cache_migration.cjs'],cwd=ROOT,capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
