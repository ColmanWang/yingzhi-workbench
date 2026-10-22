import json
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import urllib.error
import urllib.request
from pathlib import Path

from douyin_favorites_knowledge.workbench.app import Workbench
from douyin_favorites_knowledge.workbench.server import make_server


class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.knowledge = self.root / 'knowledge'
        self.cards = self.root / 'cards'
        self.knowledge.mkdir(); self.cards.mkdir()
        self.app = Workbench(self.root / 'data', self.knowledge, self.cards, start_worker=False)

    def tearDown(self):
        self.app.close(); self.temp.cleanup()

    def test_import_notes_and_source_isolation(self):
        for source in ('like', 'collection'):
            (self.knowledge / f'{source}-123456.md').write_text(f'---\nsource: {source}\nauthor: "Author"\nsource_url: "https://www.douyin.com/video/123456"\ntranscript_status: success\n---\n\n# Title\n\n### 转录\n\nHello world\n\n## Source\n', encoding='utf-8')
        self.app.import_notes()
        items = self.app.items()
        self.assertEqual(len(items), 2)
        self.assertEqual({i['id'] for i in items}, {'like-123456', 'collection-123456'})
        self.assertTrue(all(i['transcript'] == 'Hello world' for i in items))
        self.assertNotIn('play_url', json.dumps(items))

    def test_cards_match_notes_and_reject_symlinks(self):
        (self.cards / 'like-123456.html').write_text('<h1>Test</h1>')
        (self.cards / 'like-123456.json').write_text(json.dumps({'title':'Title','author':'Author','source_url':'https://www.douyin.com/video/123456'}))
        (self.cards / 'evil.html').symlink_to(self.root / 'private.html')
        cards = self.app.cards()
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]['item_id'], 'like-123456')
        self.assertEqual(cards[0]['html_url'], '/files/cards/like-123456.html')

    def test_malformed_card_metadata_does_not_break_library(self):
        for index,value in enumerate(([],None,'string')):
            (self.cards/f'like-12345{index}.html').write_text('<h1>Card</h1>')
            (self.cards/f'like-12345{index}.json').write_text(json.dumps(value))
        self.assertEqual(len(self.app.cards()),3)

    def test_duplicate_selection_has_consistent_total(self):
        self.app.collector=lambda **kw:[{'aweme_id':'123456','description':'Title'}]
        j=self.app.submit({'kind':'collect','source':'like'});self.app.run_job(j['id'])
        j=self.app.submit({'kind':'transcribe','source':'like','ids':['like-123456','like-123456']})
        self.assertEqual(j['total'],1)

    def test_collect_preserves_existing_title_and_hides_machine_fallback(self):
        note=self.knowledge/'like-123456.md'
        note.write_text('---\nsource: like\ntranscript_status: success\n---\n\n# 已整理的知识标题\n\n### 转录\n\nWords')
        self.app.import_notes()
        self.app.collector=lambda **kw:[{'aweme_id':'123456','description':'','title':'Douyin favorite 123456'}, {'aweme_id':'123457','description':'','title':'Douyin favorite 123457'}]
        job=self.app.submit({'kind':'collect','source':'like'});self.app.run_job(job['id'])
        self.assertEqual(self.app.item('like-123456')['title'],'已整理的知识标题')
        self.assertEqual(self.app.item('like-123457')['title'],'未命名视频')
        self.app.collector=lambda **kw:[{'aweme_id':'123456','description':'原视频较长的描述','title':'原视频较长的描述'}]
        job=self.app.submit({'kind':'collect','source':'like'});self.app.run_job(job['id'])
        self.assertEqual(self.app.item('like-123456')['title'],'已整理的知识标题')
        current=self.app.item('like-123456')
        self.app.store.upsert({**current,'title':'Douyin favorite 123456'},preserve=False)
        self.app.import_notes()
        self.assertEqual(self.app.item('like-123456')['title'],'已整理的知识标题')
        self.assertEqual(self.app.item('like-123456')['status'],'success')

    def test_queue_validation_busy_and_failure_are_safe(self):
        with self.assertRaises(ValueError): self.app.submit({'kind':'collect','source':'other'})
        with self.assertRaises(ValueError): self.app.submit({'kind':[],'source':'like'})
        with self.assertRaises(ValueError): self.app.submit({'kind':'collect','source':{}})
        with self.assertRaises(ValueError): self.app.submit({'kind':'collect','source':'like','limit':True})
        job = self.app.submit({'kind':'collect','source':'like','limit':3})
        with self.assertRaises(RuntimeError): self.app.submit({'kind':'login','source':'like'})
        self.app.collector = lambda **kw: (_ for _ in ()).throw(ValueError('/private/secret cookie=sessionid'))
        self.app.run_job(job['id'])
        failed = self.app.jobs()[0]
        self.assertEqual(failed['status'], 'failed')
        self.assertNotIn('/private', json.dumps(failed))
        self.assertNotIn('cookie', json.dumps(failed))

    def test_collect_and_transcribe(self):
        self.app.collector = lambda **kw: [{'aweme_id':'123456','description':'Title','author':'Author','play_url':'https://signed.invalid/secret','media_kind':'video'}]
        j = self.app.submit({'kind':'collect','source':'like','limit':3}); self.app.run_job(j['id'])
        self.assertEqual(self.app.items()[0]['status'], 'pending')
        self.app.transcriber = lambda item, context: {'transcript_status':'success','transcript':'Actual words'}
        j = self.app.submit({'kind':'transcribe','source':'like','ids':['like-123456']}); self.app.run_job(j['id'])
        self.assertEqual(self.app.items()[0]['transcript'], 'Actual words')
        self.assertEqual(self.app.items()[0]['status'], 'success')
        self.assertNotIn('signed.invalid', json.dumps(self.app.items()))
        self.assertTrue((self.knowledge / '工作台转写' / 'like-123456.md').exists())

    def test_restart_marks_incomplete_jobs(self):
        self.app.submit({'kind':'login','source':'like'})
        self.app.close()
        other = Workbench(self.root / 'data', self.knowledge, self.cards, start_worker=False)
        self.assertEqual(other.jobs()[0]['status'], 'interrupted'); other.close()

    def test_second_instance_cannot_interrupt_active_job(self):
        self.app.submit({'kind':'login','source':'like'})
        with self.assertRaises(RuntimeError):
            Workbench(self.root/'data', self.knowledge, self.cards, start_worker=False)
        self.assertEqual(self.app.jobs()[0]['status'], 'queued')

    def test_retranscribe_preserves_success(self):
        self.app.collector = lambda **kw: [{'aweme_id':'123456','description':'Title','play_url':'https://signed.invalid/secret'}]
        j=self.app.submit({'kind':'collect','source':'like'});self.app.run_job(j['id'])
        self.app.transcriber=lambda *a: {'transcript_status':'success','transcript':'Words'}
        j=self.app.submit({'kind':'transcribe','source':'like','ids':['like-123456']});self.app.run_job(j['id'])
        self.app.transcriber=lambda *a: (_ for _ in ()).throw(RuntimeError('must not run'))
        j=self.app.submit({'kind':'transcribe','source':'like','ids':['like-123456']});self.app.run_job(j['id'])
        self.assertEqual(self.app.items()[0]['transcript'],'Words')

    def test_transcription_requires_owned_items(self):
        with self.assertRaises(ValueError): self.app.submit({'kind':'transcribe','source':'like','ids':['collection-123456']})


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); root=Path(self.temp.name)
        self.root=root
        (root/'static').mkdir()
        (root/'static'/'index.html').write_text('<html>Workbench</html>')
        self.app=Workbench(root/'data', root/'notes', root/'cards', start_worker=False)
        self.server=make_server(self.app, root/'static', port=0)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True); self.thread.start()
        self.base=f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.app.close(); self.temp.cleanup()

    def request(self,path,body=None,headers=None):
        data=json.dumps(body).encode() if body is not None else None
        req=urllib.request.Request(self.base+path,data=data,headers={'Content-Type':'application/json',**(headers or {})})
        try:
            with urllib.request.urlopen(req) as r:return r.status,json.load(r)
        except urllib.error.HTTPError as e:return e.code,json.load(e)

    def test_bootstrap_and_csrf(self):
        code,payload=self.request('/api/bootstrap'); self.assertEqual(code,200)
        data=payload['data']; self.assertIn('cards',data); self.assertFalse(data['settings']['analysis_enabled'])
        code,_=self.request('/api/jobs',{'kind':'login','source':'like'}); self.assertEqual(code,403)
        token=data['csrf_token']
        code,_=self.request('/api/jobs',{'kind':'login','source':'like'},{'X-CSRF-Token':token,'Origin':'https://evil.invalid'});self.assertEqual(code,403)
        code,_=self.request('/api/jobs',{'kind':'login','source':'like'},{'X-CSRF-Token':token,'Origin':self.base});self.assertEqual(code,202)

    def test_host_and_path_traversal(self):
        code,_=self.request('/api/bootstrap',headers={'Host':'evil.invalid'});self.assertEqual(code,403)
        code,_=self.request('/files/cards/%2e%2e%2fconfig.json');self.assertEqual(code,404)
        code,_=self.request('/api/items?source=evil');self.assertEqual(code,400)


    def test_read_routes_and_missing_records(self):
        for endpoint in ('/api/items','/api/jobs','/api/cards'):
            code,payload=self.request(endpoint);self.assertEqual(code,200);self.assertEqual(payload['data'],[])
        for endpoint in ('/api/items/like-123456','/api/unknown','/files/unknown','/missing.html'):
            code,_=self.request(endpoint);self.assertEqual(code,404)
        with urllib.request.urlopen(self.base+'/') as r:
            self.assertIn(b'Workbench',r.read())
            self.assertIn("script-src 'self'",r.headers['Content-Security-Policy'])
        card=self.root/'cards'/'like-123456.html';card.write_text('<h1>Safe</h1>')
        with urllib.request.urlopen(self.base+'/files/cards/like-123456.html') as r:
            self.assertIn('sandbox',r.headers['Content-Security-Policy'])
        (self.root/'cards'/'evil.html').symlink_to(self.root/'static'/'index.html')
        code,_=self.request('/files/cards/evil.html');self.assertEqual(code,404)

    def test_invalid_posts_busy_and_payload_errors(self):
        _,payload=self.request('/api/bootstrap');token=payload['data']['csrf_token']
        headers={'X-CSRF-Token':token}
        code,_=self.request('/api/jobs',{'kind':'unknown','source':'like'},headers);self.assertEqual(code,400)
        code,_=self.request('/api/missing',{},headers);self.assertEqual(code,404)
        code,_=self.request('/api/jobs',{'kind':'login','source':'like'},headers);self.assertEqual(code,202)
        code,_=self.request('/api/jobs',{'kind':'collect','source':'like'},headers);self.assertEqual(code,409)
        req=urllib.request.Request(self.base+'/api/jobs',data=b'bad json',headers={**headers,'Content-Type':'application/json'})
        with self.assertRaises(urllib.error.HTTPError) as ctx:urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code,400)
        req=urllib.request.Request(self.base+'/api/jobs',data=b'{}',headers={**headers,'Content-Type':'text/plain'})
        with self.assertRaises(urllib.error.HTTPError) as ctx:urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code,415)
        req=urllib.request.Request(self.base+'/api/jobs',data=b'',headers={**headers,'Content-Type':'application/json'})
        with self.assertRaises(urllib.error.HTTPError) as ctx:urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code,413)


class WorkerTests(unittest.TestCase):
    def test_background_login(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);app=Workbench(root/'data',root/'notes',root/'cards')
            app.login=lambda **kw: {'status':'authenticated'}
            app.submit({'kind':'login','source':'like'})
            for _ in range(50):
                if app.jobs()[0]['status']=='completed':break
                time.sleep(.01)
            self.assertEqual(app.jobs()[0]['status'],'completed');app.close()
            app._thread.join(1)

    def test_cli_lifecycle(self):
        from douyin_favorites_knowledge.workbench.__main__ import main
        fake=SimpleNamespace(server_port=8765,serve_forever=lambda: (_ for _ in ()).throw(KeyboardInterrupt()),server_close=lambda:None)
        args=['workbench','--data-dir','data','--knowledge-dir','notes','--cards-dir','cards','--static-dir','static','--open-browser']
        with patch('sys.argv',args),patch('douyin_favorites_knowledge.workbench.__main__.Workbench') as app,patch('douyin_favorites_knowledge.workbench.__main__.make_server',return_value=fake),patch('webbrowser.open') as browser:
            main();app.return_value.close.assert_called_once();browser.assert_called_once()

if __name__=='__main__':unittest.main()
