import json,hashlib,tempfile,unittest,copy,sys
from pathlib import Path
from unittest.mock import patch
import quest_patch as e
sha=lambda b:hashlib.sha256(b).hexdigest()
class Device:
 def __init__(self,m):
  self.m=m;self.main,self.back=e.paths(m);self.files={self.main:b'ORIGINAL', '/data/base.apk':b'APK'};self.running=False;self.version=131115;self.model='Quest 3';self.fail=None;self.mutations=[];self.serial='TEST';self.start_after_push=False
 def exists(self,p):return p in self.files
 def hash(self,p,missing_ok=False):
  if p not in self.files:
   if missing_ok:return None
   raise e.PatchError('missing')
  return sha(self.files[p])
 def run(self,*args,**kwargs):
  if args[0]=='push':
   self.files[args[2]]=Path(args[1]).read_bytes();self.mutations.append(('push',args[2]))
   if self.start_after_push:self.running=True
  elif args[0]=='pull':Path(args[2]).write_bytes(self.files[args[1]])
  else:raise AssertionError(args)
  return '',0
 def shell(self,*args,**kwargs):
  if args[0]=='getprop':return self.model,0
  if args[0]=='dumpsys':return 'versionCode='+str(self.version),0
  if args[0]=='pm':return 'package:/data/base.apk',0
  if args[0]=='pidof':return ('123' if self.running else ''),0
  if args[0]=='df':return 'Filesystem 1K-blocks Used Available Use% Mounted\nx 99999999 0 99999999 0 /sdcard',0
  if args[0] in ('mv','cp','rm'):
   if self.fail and self.fail(args):self.fail=None;raise ConnectionError('injected disconnect')
   self.mutations.append(args)
   if args[0]=='rm':del self.files[args[1]]
   else:
    assert args[2] not in self.files,('refusing overwrite',args)
    self.files[args[2]]=self.files[args[1]]
    if args[0]=='mv':del self.files[args[1]]
   return '',0
  raise AssertionError(args)
class EngineTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.r=Path(self.tmp.name);self.w=self.r/'state';self.w.mkdir();self.b=self.r/'bundle';(self.b/'data').mkdir(parents=True)
  payload=b'PATCHED!';(self.b/'data/payload.bin').write_bytes(payload);recipe=b'{"format":1,"operations":[["data",0,8]]}';(self.b/'data/recipe.json').write_bytes(recipe)
  self.m=dict(format=1,game='PAYDAY',package='com.fasttravelgames.calippo',main_name='main.131115.com.fasttravelgames.calippo.obb',backup_suffix='.zecole-original-131115',main_bytes=8,source_sha256=sha(b'ORIGINAL'),target_sha256=sha(payload),source_apk_sha256=sha(b'APK'),supported_models=['Quest 3'],version_code=131115,platform='quest-standalone',release='0.1.4',tool_build='test',recipe_sha256=sha(recipe),payload_sha256=sha(payload),compatible_previous={sha(b'PREVIOUS'):'0.1.2'})
  (self.b/'manifest.json').write_text(json.dumps(self.m));self.d=Device(self.m);self.old_say=e.say;e.say=lambda x:None
 def tearDown(self):e.say=self.old_say;self.tmp.cleanup()
 def install(self):e.install(self.d,self.m,self.w,self.b)
 def test_clean_install_reinstall_restore(self):
  self.install();self.assertEqual(self.d.files[self.d.main],b'PATCHED!');self.assertEqual(self.d.files[self.d.back],b'ORIGINAL');self.assertEqual((self.w/'original.obb').read_bytes(),b'ORIGINAL')
  count=len(self.d.mutations);self.install();self.assertEqual(len(self.d.mutations),count)
  e.restore(self.d,self.m,self.w);self.assertEqual(self.d.files[self.d.main],b'ORIGINAL');self.assertEqual(self.d.files[self.d.back],b'ORIGINAL');self.assertEqual(json.loads((self.w/'installation.json').read_text())['state'],'restored')
 def test_update_keeps_original(self):
  self.d.files[self.d.main]=b'PREVIOUS';self.d.files[self.d.back]=b'ORIGINAL';self.install();self.assertEqual(self.d.files[self.d.back],b'ORIGINAL');self.assertFalse(any('retired' in x for x in self.d.files))
 def test_unknown_files_untouched(self):
  self.d.files[self.d.main]=b'UNKNOWN!'
  with self.assertRaises(e.PatchError):self.install()
  self.assertFalse(self.d.mutations)
 def test_wrong_version(self):
  self.d.version=999
  with self.assertRaises(e.PatchError):self.install()
  self.assertFalse(self.d.mutations)
 def test_wrong_apk(self):
  self.d.files['/data/base.apk']=b'OTHER'
  with self.assertRaises(e.PatchError):self.install()
  self.assertFalse(self.d.mutations)
 def test_running_initial(self):
  self.d.running=True
  with self.assertRaises(e.PatchError):self.install()
  self.assertFalse(self.d.mutations)
 def test_running_before_swap_then_recover(self):
  self.d.start_after_push=True
  with self.assertRaises(e.PatchError):self.install()
  self.assertEqual(self.d.files[self.d.main],b'ORIGINAL');self.d.running=False;self.d.start_after_push=False;self.install();self.assertEqual(self.d.files[self.d.main],b'PATCHED!')
 def test_disconnect_between_renames_rolls_back(self):
  self.d.fail=lambda a:a[0]=='mv' and 'pending-' in a[1]
  with self.assertRaises(ConnectionError):self.install()
  self.assertEqual(self.d.files[self.d.main],b'ORIGINAL');self.assertEqual(json.loads((self.w/'transaction.json').read_text())['phase'],'rolled_back')
 def test_corrupt_payload(self):
  (self.b/'data/payload.bin').write_bytes(b'BAD')
  with self.assertRaises(e.PatchError):self.install()
  self.assertFalse(self.d.mutations)
 def test_invalid_backup_kept(self):
  (self.w/'original.obb').write_bytes(b'OTHER')
  with self.assertRaises(e.PatchError):self.install()
  self.assertEqual((self.w/'original.obb').read_bytes(),b'OTHER');self.assertFalse(self.d.mutations)
 def test_reconstruct_matching_patch_missing_receipt(self):
  self.d.files[self.d.main]=b'PATCHED!';self.d.files[self.d.back]=b'ORIGINAL';self.install();self.assertEqual((self.w/'original.obb').read_bytes(),b'ORIGINAL');self.assertTrue((self.w/'installation.json').exists())
 def test_engine_lock(self):
  with e.operation_lock(self.w):
   with self.assertRaises(e.PatchError):
    with e.operation_lock(self.w):pass
  with e.operation_lock(self.w):pass
 def test_low_disk(self):
  with patch.object(e.shutil,'disk_usage',return_value=type('D',(),{'free':0})()):
   with self.assertRaises(e.PatchError):self.install()
  self.assertFalse(self.d.mutations)
 def test_process_crash_recovery(self):
  token='123456789abc';pending=self.d.main+'.zecole-pending-'+token
  j=dict(id=token,phase='swapping',main=self.d.main,backup=self.d.back,pending=pending,retired=self.d.back,before_sha256=self.m['source_sha256'],after_sha256=self.m['target_sha256'],source_sha256=self.m['source_sha256'])
  e.atomic_json(self.w/'transaction.json',j);self.d.files[self.d.back]=self.d.files.pop(self.d.main);self.d.files[pending]=b'PATCHED!';e.recover(self.d,self.m,self.w);self.assertEqual(self.d.files[self.d.main],b'ORIGINAL')
 def test_unknown_recovery_file_preserved(self):
  token='123456789abc';j=dict(id=token,phase='swapping',main=self.d.main,backup=self.d.back,pending=self.d.main+'.zecole-pending-'+token,retired=self.d.back,before_sha256=self.m['source_sha256'],after_sha256=self.m['target_sha256'],source_sha256=self.m['source_sha256']);e.atomic_json(self.w/'transaction.json',j);self.d.files[self.d.main]=b'ALIEN';self.d.files[self.d.back]=b'ORIGINAL'
  with self.assertRaises(e.PatchError):e.recover(self.d,self.m,self.w)
  self.assertEqual(self.d.files[self.d.main],b'ALIEN')
 def test_complete_before_receipt_crash(self):
  token='123456789abc';j=dict(id=token,phase='swapping',main=self.d.main,backup=self.d.back,pending=self.d.main+'.zecole-pending-'+token,retired=self.d.back,before_sha256=self.m['source_sha256'],after_sha256=self.m['target_sha256'],source_sha256=self.m['source_sha256']);e.atomic_json(self.w/'transaction.json',j);self.d.files[self.d.main]=b'PATCHED!';self.d.files[self.d.back]=b'ORIGINAL';e.recover(self.d,self.m,self.w);self.assertEqual(json.loads((self.w/'installation.json').read_text())['state'],'installed')
if __name__=='__main__':unittest.main(verbosity=2)
