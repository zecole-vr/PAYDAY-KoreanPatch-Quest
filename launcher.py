"""Reusable HTML launcher, local patch engine, no remote code execution."""
from pathlib import Path
import argparse, copy, datetime, json, os, re, shutil, sys, threading, traceback, urllib.request, urllib.error, webbrowser
from packaging.version import Version, InvalidVersion
import quest_patch as engine
ROOT=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))/'bundle'
STORAGE=engine.STORAGE

class Api:
    def __init__(self,root=ROOT):
        self.root=Path(root);self.storage=STORAGE
        self.storage.mkdir(parents=True,exist_ok=True)
        self.config=json.loads((self.root/'launcher_config.json').read_text(encoding='utf-8-sig'))
        self.manifest,_=engine.load_release(self.root)
        if self.config['platform_id']!=self.manifest['platform'] or self.config['package']!=self.manifest['package']:raise engine.PatchError('런처와 패치의 대상 플랫폼이 다릅니다.')
        if self.config['supported_game']!=self.manifest['version_name'] or self.config['version_code']!=self.manifest['version_code']:raise engine.PatchError('런처와 패치의 지원 게임 버전이 다릅니다.')
        if self.config['installer_host']!=self.manifest['installer_host'] or self.config['installer_version']!=self.manifest['installer_version'] or self.config['tool_build']!=self.manifest['tool_build']:raise engine.PatchError('설치기 버전 정보가 일치하지 않습니다.')
        self.guard=threading.Lock();self.serial=None;self.adb_path=None;self.latest_url=None
        self.state=dict(busy=False,current='Quest를 연결해 주세요',current_note='USB 연결 후 헤드셋에서 디버깅을 허용해 주세요.',tag='연결 필요',tone='neutral',latest='확인 중…',latest_note='공개된 Quest 안정 버전을 확인합니다.',latest_tone='neutral',message='USB로 Quest를 연결해 주세요.',can_install=False,can_restore=False,devices=[],needs_terms=False,config=self.config,release=self.manifest['release'],backup_path=str(self.storage))
        self.logpath=None
    def get_state(self):
        with self.guard:return copy.deepcopy(self.state)
    def _set(self,**items):
        with self.guard:self.state.update(items)
    def _say(self,message):
        text=str(message)
        match=re.search(r'패치 생성 (\d+)%',text)
        self._set(message=text,percent=int(match.group(1)) if match else None)
        if self.logpath:
            with self.logpath.open('a',encoding='utf-8') as f:f.write(datetime.datetime.now().isoformat()+' '+text+'\n')
    def _find_adb(self):
        cached=self.storage/'.tools/platform-tools-37.0.0/download-receipt.json'
        if cached.is_file():return engine.prepare_adb(self.storage)
        paths=[shutil.which('adb'),str(Path(os.getenv('APPDATA',''))/'SideQuest/platform-tools/adb.exe'),str(Path(os.getenv('LOCALAPPDATA',''))/'Android/Sdk/platform-tools/adb.exe')]
        return next((x for x in paths if x and Path(x).is_file()),None)
    def _latest(self):
        c=self.config;self.latest_url=None;self._set(newer_release=False,latest_version=None)
        try:
            releases=[]
            for page in range(1,6):
                url=f'https://api.github.com/repos/{c["owner"]}/{c["repo"]}/releases?per_page=100&page={page}'
                req=urllib.request.Request(url,headers={'Accept':'application/vnd.github+json','User-Agent':'Zecole-QuestPatch'})
                with urllib.request.urlopen(req,timeout=12) as response:
                    part=json.loads(response.read(4*1024*1024))
                if not isinstance(part,list):raise ValueError('Unexpected releases response')
                releases+=part
                if len(part)<100:break
            candidates=[]
            for rel in releases:
                if rel.get('draft') or rel.get('prerelease'):continue
                try:v=Version(rel['tag_name'].removeprefix('v'))
                except (InvalidVersion,KeyError):continue
                if v.is_prerelease or v.is_devrelease:continue
                assets={a['name']:a for a in rel.get('assets',[])}
                for name,asset in assets.items():
                    match=re.fullmatch(c['release_asset_regex'],name)
                    if not match or Version(match.group(1))!=v or name+'.sha256' not in assets:continue
                    if not asset.get('browser_download_url','').startswith(c['repository']+'/releases/download/'):continue
                    candidates.append((v,name.endswith('.exe'),rel))
            if not candidates:
                self._set(latest='공개 배포본 없음',latest_note='배포 가능한 Quest 안정 버전이 아직 없습니다.',latest_tone='neutral');return
            version,_,rel=max(candidates,key=lambda x:(x[0],x[1]));self.latest_url=rel['html_url'] if rel.get('html_url','').startswith(c['repository']+'/releases/') else None
            newer=version>Version(self.manifest['release'])
            self._set(latest='v'+str(version),latest_note='새 설치본을 받아 업데이트해 주세요.' if newer else 'GitHub의 공개 안정 버전입니다.',latest_tone='warning' if newer else 'good',newer_release=newer,latest_version=str(version))
        except Exception as exc:
            self._set(latest='버전 확인 실패',latest_note='비공개 저장소 또는 연결 오류입니다. 다시 확인해 주세요.',latest_tone='warning',newer_release=False)
            if self.logpath:self._say('GitHub 버전 확인 실패: '+type(exc).__name__)
    def _scan(self):
        self._set(can_install=False,can_restore=False,devices=[],needs_terms=False)
        self.adb_path=self._find_adb()
        if not self.adb_path:
            self._set(current='연결 도구 준비 필요',current_note='처음 한 번 약관 동의 후 ADB를 자동으로 준비합니다.',tag='준비 필요',tone='neutral',needs_terms=True,can_install=True,install_label='연결 도구 준비',message='별도로 Python이나 ADB를 설치할 필요가 없습니다.');return
        adb=engine.Adb(self.adb_path);text,_=adb.run('devices')
        entries=[line.split() for line in text.splitlines() if line.strip() and not line.startswith(('List ','*'))]
        devices=[x[0] for x in entries if len(x)>=2 and x[1]=='device']
        physical={}
        for candidate in sorted(devices,key=lambda s:(':' in s,s)):
            if not re.fullmatch(r'[A-Za-z0-9_.:-]+',candidate):continue
            probe=engine.Adb(self.adb_path,candidate)
            identity=probe.shell('getprop','ro.serialno',check=False)[0].strip() or candidate
            physical.setdefault(identity,candidate)
        devices=list(physical.values())
        self._set(devices=devices)
        if not devices:
            unauthorized=any(len(x)>1 and x[1]=='unauthorized' for x in entries)
            self._set(current='USB 디버깅을 허용해 주세요' if unauthorized else 'Quest를 연결해 주세요',current_note='헤드셋 안의 USB 디버깅 허용 창을 확인해 주세요.' if unauthorized else '연결 후 오른쪽의 다시 확인을 눌러 주세요.',tag='인증 필요' if unauthorized else '연결 필요',tone='neutral',message='기기를 확인할 때까지 게임 파일을 변경하지 않습니다.');return
        if len(devices)>1 and self.serial not in devices:
            self._set(current='Quest를 선택해 주세요',current_note='여러 기기가 연결되어 있습니다.',tag='선택 필요',tone='neutral',message='설치할 기기를 선택해 주세요.');return
        if len(devices)==1:self.serial=devices[0]
        if not re.fullmatch(r'[A-Za-z0-9_.:-]+',self.serial):raise engine.PatchError('지원하지 않는 기기 식별자입니다.')
        adb.serial=self.serial;m=self.manifest;engine.version_check(adb,m)
        main,backup=engine.paths(m)
        self._say('기기의 패치 파일을 확인합니다…')
        current=adb.hash(main,missing_ok=True);original=adb.hash(backup,missing_ok=True)
        journal=self._work()/'transaction.json'
        if journal.exists():
            transaction=json.loads(journal.read_text(encoding='utf8'))
            if transaction.get('phase') not in ('complete','rolled_back','abandoned'):
                running=bool(adb.shell('pidof',m['package'],check=False)[0].strip())
                self._set(current='중단된 작업 확인',current_note='설치 기록과 실제 파일을 검증하여 복구합니다.',tag='복구 필요',tone='warning',can_install=not running,can_restore=False,install_label='중단된 작업 복구',message='게임을 종료해 주세요.' if running else '복구 버튼을 누르면 확인 가능한 상태에서만 복구합니다.')
                return
        if current not in engine.known_hashes(m):
            self._set(current='설치 상태 확인 필요',current_note='지원하지 않는 파일이므로 자동으로 변경하지 않습니다.',tag='확인 필요',tone='warning',message='다른 수정본 또는 게임 업데이트 여부를 확인해 주세요.');return
        if original not in (None,m['source_sha256']) or (current!=m['source_sha256'] and original is None):
            self._set(current='원본 백업 확인 필요',current_note='유효한 원본 백업을 확인하지 못했습니다.',tag='확인 필요',tone='warning',message='백업을 확인하기 전에는 설치·복구할 수 없습니다.');return
        work=self._work();receipt=work/'installation.json';record={}
        if receipt.is_file():
            try:record=json.loads(receipt.read_text(encoding='utf-8'))
            except (ValueError,OSError):pass
        matching=record.get('installed_sha256')==current and (record.get('version_code',record.get('game_version_code'))==m['version_code'])
        if current==m['source_sha256']:
            self._set(current='미설치',current_note=f'게임 빌드 {m["version_code"]} · 원본 파일 확인 완료',tag='미설치',tone='neutral',install_label='한글패치 설치')
        elif current==m['target_sha256']:
            self._set(current='v'+((record.get('patch_version') or m['release']) if matching else m['release']),current_note='설치 기록과 파일 확인 완료' if matching else '패치 파일 확인 완료 · 설치 기록 재확인 가능',tag='파일 확인 완료',tone='good',install_label='설치 확인 / 재설치')
        else:
            label=m['compatible_previous'][current]
            self._set(current=('v'+label if label[0].isdigit() else '자막 시험판'),current_note='이 설치본으로 업데이트할 수 있습니다.',tag='업데이트 필요',tone='warning',install_label='한글패치 업데이트')
        latest=self.get_state().get('latest_version')
        if current==m['target_sha256'] and latest:
            if Version(latest)>Version(m['release']):self._set(tag='업데이트 필요',tone='warning')
            elif Version(latest)==Version(m['release']):self._set(tag='최신 버전',tone='good')
        running=bool(adb.shell('pidof',m['package'],check=False)[0].strip())
        self._set(can_install=not running,can_restore=not running and current!=m['source_sha256'],message='게임을 완전히 종료한 뒤 다시 확인해 주세요.' if running else 'Quest 연결 완료 · 설치 중에는 케이블을 분리하지 마세요.')
    def _work(self):return self.storage/re.sub(r'[^A-Za-z0-9_.-]','_',self.serial)/str(self.manifest['version_code'])
    def _worker(self,action,terms=False):
        engine.say=self._say
        logdir=self.storage/'logs';logdir.mkdir(exist_ok=True)
        self.logpath=logdir/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'-'+action+'.log')
        self._say({'refresh':'버전과 연결 상태를 확인합니다…','install':'설치를 준비합니다…','restore':'원본 복구를 준비합니다…'}[action])
        try:
            if action=='refresh':
                self._latest();self._scan()
            else:
                with engine.operation_lock(self.storage):
                    if not self.adb_path:
                        if not terms:raise engine.PatchError('ADB 다운로드 약관 동의가 필요합니다.')
                        self.adb_path=engine.prepare_adb(self.storage,accept_terms=True)
                    self._scan()
                    if not self.serial:return
                    adb=engine.Adb(self.adb_path,self.serial);work=self._work()
                    with engine.operation_lock(work):
                        journal=work/'transaction.json'
                        recovery_only=journal.exists() and json.loads(journal.read_text(encoding='utf8')).get('phase') not in ('complete','rolled_back','abandoned')
                        engine.recover(adb,self.manifest,work)
                        self._scan()
                        if recovery_only:
                            self._set(message='중단된 작업 복구 완료 · 현재 상태를 확인해 주세요.')
                            with self.logpath.open('a',encoding='utf8') as f:f.write('recovery verified complete\n')
                            return
                        flag='can_install' if action=='install' else 'can_restore'
                        if not self.get_state().get(flag):return
                        self.manifest,_=engine.load_release(self.root)
                        if action=='install':engine.install(adb,self.manifest,work,self.root)
                        else:engine.restore(adb,self.manifest,work)
                self._scan();self._set(message='설치 완료 · 게임에서 확인해 주세요.' if action=='install' else '원본 복구 완료 · 세이브 진행 상황은 유지됩니다.')
            with self.logpath.open('a',encoding='utf8') as f:f.write('작업 성공 완료: '+action+'\n')
        except Exception as exc:
            with self.logpath.open('a',encoding='utf-8') as f:f.write(traceback.format_exc())
            self._set(message=str(exc),can_install=False,can_restore=False,current='상태 확인 필요',tag='확인 필요',tone='warning')
        finally:self._set(busy=False,percent=None)
    def _launch(self,action,terms=False):
        with self.guard:
            if self.state['busy']:return copy.deepcopy(self.state)
            self.state.update(busy=True,percent=None,message='확인 중입니다…')
        threading.Thread(target=self._worker,args=(action,terms),daemon=True).start();return self.get_state()
    def refresh(self):return self._launch('refresh')
    def select_device(self,serial):
        if serial not in self.get_state().get('devices',[]) or self.get_state()['busy']:return self.get_state()
        self.serial=serial;return self.refresh()
    def start(self,action,terms=False):
        if action not in ('install','restore'):raise ValueError('Unsupported action')
        if not self.get_state().get('can_install' if action=='install' else 'can_restore'):return self.get_state()
        return self._launch(action,terms is True)
    def open_link(self,key):
        if key not in ('youtube','repository','issues','adb_terms','latest','backup','licenses'):raise ValueError('Unsupported link')
        if key=='backup':
            folder=self.storage;folder.mkdir(exist_ok=True);os.startfile(str(folder));return None
        if key=='licenses':
            folder=self.storage/'documentation'/self.manifest['release'];folder.mkdir(parents=True,exist_ok=True)
            shutil.copytree(self.root/'licenses',folder/'licenses',dirs_exist_ok=True)
            for name in ('THIRD_PARTY_NOTICES.md','README.txt'):shutil.copy2(self.root/name,folder/name)
            os.startfile(str(folder));return None
        url=self.latest_url if key=='latest' else self.config[key]
        if url:webbrowser.open(url)
        return None

def main():
    import webview
    api=Api();c=api.config
    # Serve only UI files; backups and patch payload are outside this root.
    window=webview.create_window(c['game']+' | 제콜 한글패치',url=str(ROOT/'ui/index.html'),js_api=api,width=c['window']['width'],height=c['window']['height'],min_size=(680,580),background_color='#222325')
    window.events.closing+=lambda:not api.get_state()['busy']
    if '--self-check' in sys.argv:
        def check():
            import time
            report={}
            try:
                window.events.loaded.wait(30)
                deadline=time.monotonic()+55
                while time.monotonic()<deadline:
                    ready=window.evaluate_js("typeof api!=='undefined' && api!==null")
                    if ready and not api.get_state()['busy']:break
                    time.sleep(.25)
                assert ready and not api.get_state()['busy'],'UI initialization timed out'
                window.evaluate_js('render('+json.dumps(api.get_state(),ensure_ascii=True)+')')
                time.sleep(.2)
                dom=window.evaluate_js("({width:innerWidth,height:innerHeight,overflow:document.documentElement.scrollWidth>innerWidth,title:document.getElementById('game').textContent,buttons:[...document.querySelectorAll('.actions button')].map(x=>x.textContent.trim())})")
                assert not dom['overflow']
                if '--verify-public-release' in sys.argv:
                    assert api.state['latest']=='v'+api.manifest['release'], api.state
                    assert not api.state['newer_release'], api.state
                    assert api.state['latest_tone']=='good', api.state
                    assert window.evaluate_js("document.getElementById('latest').textContent")==api.state['latest']
                    assert window.evaluate_js("document.getElementById('edition').textContent")=='Windows 설치기'
                window.evaluate_js("document.getElementById('help').click()")
                assert window.evaluate_js("document.getElementById('dialog').open")
                help_text=window.evaluate_js("document.getElementById('dialog-text').textContent")
                assert str(api.storage) in help_text,'Displayed backup path differs from storage path'
                assert '같은 폴더' not in help_text
                assert f'지원 게임: Quest 단독판 {api.manifest["version_name"]} ({api.manifest["version_code"]})' in help_text,'Help game version differs from payload'
                assert window.evaluate_js("document.getElementById('support').textContent")==f'지원 게임 {api.manifest["version_name"]} · 빌드 {api.manifest["version_code"]} · Quest 단독판'
                logdir=STORAGE/'logs';logdir.mkdir(exist_ok=True)
                from webview.platforms.winforms import BrowserView
                from Microsoft.Web.WebView2.Core import CoreWebView2CapturePreviewImageFormat
                from System.IO import FileStream,FileMode,FileAccess
                from System import Action
                control=BrowserView.instances[window.uid].browser.webview
                stream=FileStream(str(logdir/'launcher-help.png'),FileMode.Create,FileAccess.Write)
                pending=[]
                control.Invoke(Action(lambda:pending.append(control.CoreWebView2.CapturePreviewAsync(CoreWebView2CapturePreviewImageFormat.Png,stream))))
                pending[0].Wait(10000);stream.Dispose()
                window.evaluate_js("document.getElementById('dialog').close()")
                time.sleep(.2)
                stream=FileStream(str(logdir/'launcher-main.png'),FileMode.Create,FileAccess.Write)
                pending=[]
                control.Invoke(Action(lambda:pending.append(control.CoreWebView2.CapturePreviewAsync(CoreWebView2CapturePreviewImageFormat.Png,stream))))
                pending[0].Wait(10000);stream.Dispose()
                assert not STORAGE.resolve().is_relative_to(ROOT.resolve())
                assert (ROOT/'data/payload.bin').is_file()
                report={'status':'PASS_REAL_WEBVIEW_UI','standalone':bool(getattr(sys,'frozen',False)),'persistent_storage':str(STORAGE),'bundled_payload_verified':True,'help_text':help_text,'displayed_backup_path_verified':True,'dom':dom,'state':api.get_state(),'device_modified':False}
            except Exception:
                report={'status':'FAIL','error':traceback.format_exc()}
            finally:
                logdir=STORAGE/'logs';logdir.mkdir(exist_ok=True)
                (logdir/'self-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
                window.destroy()
        webview.start(check,gui='edgechromium',debug=False)
    else:
        webview.start(gui='edgechromium',debug=False)
if __name__=='__main__':
    try:main()
    except Exception as exc:
        STORAGE.mkdir(parents=True,exist_ok=True)
        log=STORAGE/'launcher-error.log';log.write_text(traceback.format_exc(),encoding='utf-8')
        import ctypes
        ctypes.windll.user32.MessageBoxW(0,'실행하지 못했습니다. Microsoft Edge WebView2 Runtime 설치 여부를 확인해 주세요.\n상세: '+str(log)+'\n'+str(exc),'제콜 한글패치',16)
