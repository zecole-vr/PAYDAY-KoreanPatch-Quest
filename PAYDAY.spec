from pathlib import Path
root=Path(SPECPATH)
a=Analysis([str(root/'launcher.py')],pathex=[str(root)],binaries=[],datas=[(str(root/'bundle'),'bundle')],hiddenimports=['webview.platforms.edgechromium','webview.platforms.winforms','clr_loader'],hookspath=[],hooksconfig={},runtime_hooks=[],excludes=['PyQt5','PyQt6','PySide2','PySide6','gi','cefpython3'],noarchive=False,optimize=0)
a.binaries=[x for x in a.binaries if not x[0].lower().startswith('api-ms-win-') and x[0].lower()!='ucrtbase.dll']
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,a.binaries,a.datas,[],name='PAYDAY_Quest_Windows_v0.1.4',debug=False,bootloader_ignore_signals=False,strip=False,upx=False,runtime_tmpdir=None,console=False,disable_windowed_traceback=False,version=str(root/'version-info.txt'))
