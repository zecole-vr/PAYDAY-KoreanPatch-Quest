"""Anonymous public-release check. Never reads GitHub credentials."""
from pathlib import Path
import argparse,hashlib,json,urllib.request,subprocess,os,time
REPO='zecole-vr/PAYDAY-KoreanPatch-Quest'
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=Path('public-check'));p.add_argument('--run',action='store_true');args=p.parse_args()
info=json.loads((Path(__file__).resolve().parents[1]/'release-info.json').read_text(encoding='utf8'));tag='v'+info['release']
def get(url):return urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'ZECOLE-Public-Verification'}),timeout=30)
with get('https://api.github.com/repos/'+REPO+'/releases/tags/'+tag) as f:release=json.load(f)
assert not release['draft'] and not release['prerelease']
assets={a['name']:a for a in release['assets']};name=info['asset'];expected_prefix='https://github.com/'+REPO+'/releases/download/'+tag+'/'
for n in [name,name+'.sha256']:assert assets[n]['browser_download_url'].startswith(expected_prefix)
with get(assets[name+'.sha256']['browser_download_url']) as f:checksum=f.read(4096).decode().split()[0]
assert checksum==info['sha256'];args.output.mkdir(parents=True,exist_ok=True);exe=args.output/name
if exe.exists():raise SystemExit('Output EXE already exists; choose another --output directory')
h=hashlib.sha256();count=0
with get(assets[name]['browser_download_url']) as f,exe.open('xb') as out:
 while True:
  b=f.read(1024*1024)
  if not b:break
  count+=len(b)
  if count>info['bytes']:raise RuntimeError('Unexpected download size')
  h.update(b);out.write(b)
assert count==info['bytes'] and h.hexdigest()==checksum
report={'anonymous_download':True,'sha256':h.hexdigest(),'bytes':count,'executed':False}
if args.run:
 report_path=Path(os.environ['LOCALAPPDATA'])/'ZECOLE/PAYDAY_Aces_High/Quest/logs/self-check.json';started=time.time()
 subprocess.run([str(exe.resolve()),'--self-check','--verify-public-release'],check=True,timeout=150)
 assert report_path.stat().st_mtime>=started
 result=json.loads(report_path.read_text(encoding='utf8'));assert result['status']=='PASS_REAL_WEBVIEW_UI' and result['standalone']
 report['executed']=True;report['launcher_latest']=result['state']['latest']
(args.output/'public-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
