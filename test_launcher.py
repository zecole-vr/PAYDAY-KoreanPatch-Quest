import json,unittest,urllib.error,copy
from pathlib import Path
from unittest.mock import patch
import launcher
class Response:
 def __init__(self,d):self.d=d
 def __enter__(self):return self
 def __exit__(self,*a):pass
 def read(self,n):return json.dumps(self.d).encode()
class LatestTests(unittest.TestCase):
 def setUp(self):self.api=launcher.Api();self.repo=self.api.config['repository']
 def rel(self,v,platform='Quest_Windows',pre=False,checksum=True):
  name=f'PAYDAY_{platform}_v{v}.exe';return {'tag_name':'v'+v,'prerelease':pre,'draft':False,'html_url':self.repo+'/releases/tag/v'+v,'assets':[{'name':name,'browser_download_url':self.repo+'/releases/download/v'+v+'/'+name}]+([{'name':name+'.sha256'}] if checksum else [])}
 def check(self,data):
  with patch.object(launcher.urllib.request,'urlopen',return_value=Response(data)):self.api._latest()
  return self.api.get_state()
 def test_semantic_latest(self):
  s=self.check([self.rel('0.9.0'),self.rel('0.10.0')]);self.assertEqual(s['latest'],'v0.10.0');self.assertTrue(s['newer_release'])
 def test_exclude_prerelease_wrong_platform_missing_checksum(self):
  s=self.check([self.rel('0.1.4'),self.rel('9.0.0',pre=True),self.rel('8.0.0',platform='Steam_Windows'),self.rel('7.0.0',checksum=False)]);self.assertEqual(s['latest'],'v0.1.4')
 def test_empty_not_error(self):self.assertEqual(self.check([])['latest'],'공개 배포본 없음')
 def test_failed_then_retry(self):
  with patch.object(launcher.urllib.request,'urlopen',side_effect=urllib.error.URLError('offline')):self.api._latest()
  s=self.api.get_state();self.assertEqual(s['latest'],'버전 확인 실패');self.assertFalse(s['newer_release']);self.assertEqual(self.check([self.rel('0.1.4')])['latest'],'v0.1.4')
 def test_no_downgrade(self):self.assertFalse(self.check([self.rel('0.1.2')])['newer_release'])
 def test_foreign_url_rejected(self):
  r=self.rel('99.0.0');r['assets'][0]['browser_download_url']='https://example.com/a.exe';self.assertEqual(self.check([r])['latest'],'공개 배포본 없음')
 def test_duplicate_ui_request(self):
  with self.api.guard:self.api.state['busy']=True
  with patch.object(launcher.threading,'Thread') as t:self.api.refresh();t.assert_not_called()
if __name__=='__main__':unittest.main(verbosity=2)
