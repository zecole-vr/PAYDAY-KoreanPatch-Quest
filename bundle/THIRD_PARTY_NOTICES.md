# 출처 및 라이선스

제작자: [제콜 (ZECOLE)](https://www.youtube.com/@zecole)
이 프로젝트의 한국어 번역은 보유 게임의 영어 문구를 바탕으로 본 작업에서 작성·검수했습니다.
외부 한글패치 번역문을 사용했다거나 권리자로부터 공식 재배포 허락을 받았다고 주장하지 않습니다.
PAYDAY: Aces High 및 원본 게임 자산·영상·스크립트의 권리는 각 권리자에게 있습니다.
이 배포판은 비공식 커뮤니티 패치입니다. 게임 원본 APK/OBB 전체를 포함하지 않으며
정확히 일치하는 사용자 보유 원본에서 변경 데이터를 적용합니다.
패치 데이터에 포함되는 변경 자산 부분에는 게임 권리가 유지됩니다.

## 글꼴
Pretendard Medium 1.3.9 — https://github.com/orioncactus/pretendard/releases/tag/v1.3.9
Copyright (c) 2021, Kil Hyung-jin. SIL Open Font License 1.1.
원본 OTF SHA-256: d39e50e4bb52b4993b6a4eeb821a171254745bd824446af01e1f616b89fface0
게임용 폰트 컨테이너·텍스처 아틀라스 및 영상 자막으로 변환하여 사용합니다.
런처 자체는 Windows의 Segoe UI / 맑은 고딕을 사용하며 이 시스템 폰트 파일은 재배포하지 않습니다.
전문: licenses/Pretendard-OFL.txt.

## ICU
게임 ICU 64.2 통화 데이터의 KRW 표시 자릿수만 수정했습니다.
https://github.com/unicode-org/icu/tree/release-64-2
전문: licenses/ICU-LICENSE.txt. APK·실제 결제 처리는 수정하지 않았습니다.

## 설치기 구성 요소
기준 공통 런처: IntoTheRadius2-Quest-KoreanPatch 릴리스 1.2.5.
PAYDAY 배포판 v0.1.3의 검증된 설치기와 UI를 재사용했습니다.
실제 참조 경로·파일 해시·릴리스 태그는 유지보수 기록을 참조해 주세요.
설치기 코드에만 MIT 적용: licenses/INSTALLER-MIT.txt.
이 코드 라이선스를 번역문·게임 자산·폰트·패치 데이터 전체에 적용하지 않습니다.

Python, PyInstaller, pywebview, Python.NET, clr_loader, cffi, pycparser, bottle,
proxy_tools, typing_extensions, packaging, setuptools 및 포함 vendor 구성 요소의
고지·라이선스는 licenses 하위에 동봉합니다. 실제 빌드 버전은 dependencies.json에 기록합니다.
Microsoft WebView2 SDK: licenses/WebView2-LICENSE.txt 및 WebView2-NOTICE.txt.
WebView2 Runtime과 .NET Framework는 Windows에 설치된 것을 사용하며 재배포하지 않습니다.
This product includes software developed by the OpenSSL Project for use in the OpenSSL Toolkit.
This product includes cryptographic software written by Eric Young and software written by Tim Hudson.

## 연결 도구
Google Android SDK Platform Tools 37.0.0은 첫 사용 시 공식 서버에서 내려받습니다.
https://dl.google.com/android/repository/platform-tools_r37.0.0-win.zip
SHA-256: 4fe305812db074cea32903a489d061eb4454cbc90a49e8fea677f4b7af764918
약관: https://developer.android.com/studio/terms
사용 동의를 받은 후 무결성을 확인하며, 다운로드한 도구의 NOTICE.txt를 함께 보존합니다.

## 배너
[공식 Steam 상점](https://store.steampowered.com/app/3456660/PAYDAY_Aces_High/)의 배경 이미지.
PAYDAY / Fast Travel Games / 해당 권리자의 게임 홍보 이미지이며 별도 권리 양도를 주장하지 않습니다.
이미지는 게임 식별을 위한 배너에만 사용하고, 제목·버전·버튼·플랫폼 표시는 실제 UI 요소입니다.
