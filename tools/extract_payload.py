from pathlib import Path
import hashlib,json,sys
from PyInstaller.archive.readers import CArchiveReader
root=Path(__file__).resolve().parents[1]
if len(sys.argv)!=2:raise SystemExit('Usage: python tools/extract_payload.py <released EXE>')
exe=Path(sys.argv[1]);info=json.loads((root/'release-info.json').read_text(encoding='utf8'))
with exe.open('rb') as f:
 h=hashlib.sha256()
 for b in iter(lambda:f.read(8<<20),b''):h.update(b)
if h.hexdigest()!=info['sha256']:raise SystemExit('EXE checksum mismatch; no files extracted')
archive=CArchiveReader(exe);names={n.replace('\\','/'):n for n in archive.toc};m=json.loads((root/'bundle/manifest.json').read_text(encoding='utf8'))
out=root/'bundle/data';out.mkdir(parents=True,exist_ok=True)
for name,key in [('recipe.json','recipe_sha256'),('payload.bin','payload_sha256')]:
 data=archive.extract(names['bundle/data/'+name]);expected=m[key]
 if hashlib.sha256(data).hexdigest()!=expected:raise SystemExit('Embedded payload mismatch')
 target=out/name
 if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()!=expected:raise SystemExit('Existing file differs; refusing overwrite')
 target.write_bytes(data)
 print('Verified '+name)
