# 설치기 빌드와 배포

기준: Python 3.10.11 x64, requirements-build.txt의 실제 빌드 버전.
기존 검증 런처를 재사용한 Python + pywebview + PyInstaller 단일 EXE입니다.
번역 패치 버전, 설치 도구 버전/빌드 ID, 지원 게임 버전은 bundle/manifest.json과 launcher_config.json에서 구분합니다.
게임·엔진·저장 위치를 바꾸려면 실제 구현과 검증 기록도 같이 갱신하세요.

1. Python 가상 환경을 만들고 `pip install -r requirements-build.txt`를 실행합니다.
2. 현재 릴리스 EXE에서 `python tools/extract_payload.py <EXE 경로>`로 검증된 data 두 파일을 가져옵니다.
   전체 원본 게임을 저장소에 넣지 마세요. 번역 내용을 변경할 때는 유지보수 원본 프로젝트에서 새 변경 데이터를 생성해야 합니다.
3. `python test_engine.py`, `python test_launcher.py`를 실행합니다.
4. `pyinstaller --noconfirm --distpath dist --workpath build PAYDAY.spec`로 빌드합니다.
5. EXE `--self-check`로 실제 창과 내장 데이터 검사를 수행합니다. 결과는 앱 데이터의 logs/self-check.json입니다.
6. 새 버전·파일명·리소스 버전·릴리스 태그·체크섬·자산 선택식을 함께 갱신하고 실제 기기 설치/복구를 검증합니다.

같은 게임 결과 파일을 만드는 재현은 해시로 검증합니다. EXE는 빌드 시각·도구 환경에 따라 바이트가 달라질 수 있습니다.

현재 기본값
- 패치: 0.1.4 / 설치 도구: 0.1.4 / 빌드: 20261107.11
- 태그: v0.1.4 / 자산: PAYDAY_Quest_Windows_v0.1.4.exe 및 같은 이름의 .sha256
- 게임: Quest 3, com.fasttravelgames.calippo, 빌드 131115
- 백업·설치 기록: LOCALAPPDATA/ZECOLE/PAYDAY_Aces_High/Quest/<serial>/131115
- 원래 시험 설치기의 경로/기기 원본 suffix와 호환. 알 수 없는 기록·파일은 자동 삭제 금지.

기준 템플릿
- 저장소: https://github.com/zecole-vr/IntoTheRadius2-Quest-KoreanPatch
- 릴리스: v1.2.5, 태그 커밋 9245d8022655eaa1eba420cfd16facdc7a89e419
- 직접 재사용한 로컬 스냅샷 파일 해시는 template-provenance.json 참조.
  원격 태그의 모든 소스와 로컬 파일이 같다고 추정하지 않습니다.
- 공통 개선: OS 잠금으로 중단 후 잠금 회수, 교체 기록과 검증 기반 복구,
  USB/무선 중복 기기 정리, 복구 버튼이 의도하지 않은 재설치로 이어지지 않도록 처리.
- 이 변경으로 이미 배포한 다른 게임 설치기는 수정하지 않았습니다.

이번 업데이트는 PAYDAY Quest v0.1.3의 배포 설치기와 공통 UI를 재사용했습니다.
게임 버전 검사·파일명·새 원본 해시·백업 suffix를 빌드 131115에 맞추고, 기존 빌드의 PC 백업 폴더를 보존합니다.
