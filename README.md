# 🧬 BIO Catalyst — 국내·미국 상장 바이오 투자 이벤트 캘린더 (프로토타입)

공개 API와 큐레이션을 결합해 국내/미국 상장 바이오 기업의 **예정 카탈리스트**(임상 readout·규제 결정·기술이전·학회·실적)를
모바일 우선 화면에서 **리스트(피드) 중심**으로 보여주는 프로토타입입니다.

> 이 서비스의 본질은 "투자 아이디어 탐색"입니다. 따라서 단순 일정 나열이 아니라
> **예정된 카탈리스트**를 모으는 데 초점을 둡니다.
> 서버 없이 동작하며, 데이터는 1회 수집해 정적 파일(`data/events.json`, `web/data.js`)로 저장합니다.

## 🌐 Live Demo

**https://w-x-z.github.io/BIO-Calendar/**

`main` 브랜치에 push하면 GitHub Actions가 `web/` 폴더를 GitHub Pages로 자동 배포합니다.

## 📁 구조

```
BIO-Calendar/
├── README.md
├── docs/api-research.md       # 공개 API/데이터 소스 조사
├── scripts/collect_data.py    # 카탈리스트 중심 데이터 수집(ClinicalTrials.gov + 큐레이션)
├── data/events.json           # 수집·정규화된 통합 이벤트
└── web/                       # 모바일 웹 (서버리스)
    ├── index.html             # 피드 우선 + 캘린더 보조
    ├── styles.css             # modern UI (다크 헤더, Inter, 카드 피드)
    ├── app.js
    └── data.js                # events.json embed (file://에서도 동작)
```

## 🔌 데이터 소스 & 카탈리스트 처리 (자세히는 `docs/api-research.md`)

| 유형 | 소스 | 비고 |
|------|------|------|
| 임상 readout | **ClinicalTrials.gov API v2** (인증 불필요) | Phase 2/3 중 향후·최근 `PrimaryCompletionDate` 건만 수집 |
| 규제(PDUFA/허가)·딜(L/O)·학회·실적 | **큐레이션** (공개 IR/뉴스/리포트, 추정) | 무료 단일 API 부재 → 직접 큐레이션 |
| (운영 권장) 국내 공시·실적 | DART 오픈API (API Key) | 프로토타입 미사용 |

### ⚠️ 왜 큐레이션이 핵심인가 (예: 코오롱티슈진 TG-C)
- ClinicalTrials.gov는 **"1차지표 데이터 수집 완료 예정일"** 만 제공할 뿐,
  **"2026년 7월 톱라인 결과 발표"** 같은 IR성 카탈리스트는 제공하지 않습니다.
  (실제 TG-C 3상의 `PrimaryCompletionDate`는 2024-07로 과거 표기)
- 따라서 정확한 날짜가 없어도 **"2026년 하반기/3분기"** 수준의 예정 이벤트를 큐레이션으로 수집합니다.
- 데이터 모델에 `datePrecision`(day/month/quarter/half), `isCatalyst`, `importance` 필드를 두어
  모호한 시점도 표현하고, UI에서 정확 일정은 `D-day`, 추정 일정은 `≈ 예상`으로 구분합니다.

## 🚀 실행

```bash
# 1) 데이터 수집(선택 — 이미 수집본 포함, 인터넷 필요·외부 라이브러리 불필요)
python3 scripts/collect_data.py

# 2) 웹 실행
cd web && python3 -m http.server 8123
# http://localhost:8123 접속 (개발자도구 모바일 모드 권장)
```
> `web/data.js`에 데이터를 embed 했으므로 `web/index.html`을 파일로 직접 열어도 동작합니다.

## ✨ 기능
- **📋 피드(기본)**: 다가오는 카탈리스트를 월별 그룹으로 정렬. `D-day`/`≈ 예상` 배지, 카탈리스트 강조 카드
- **🔥 주목 카탈리스트 레일**: 중요도 높은 임박 이벤트 가로 스크롤
- **필터**: 국가(전체/국내/미국) · 유형(임상/규제/딜·L/O/학회/실적) · `⭐ 카탈리스트만` 토글
- **📅 캘린더(보조)**: 월별 달력 + 유형별 색상 점, 날짜별 일정
- **상세 시트**: 대상물질·적응증·임상단계·상태·출처 링크

## 🧭 한계 & 다음 단계
- 큐레이션 이벤트의 날짜는 **추정치**이며 실제 발표와 다를 수 있습니다(프로토타입).
- 운영 전환 시: DART(국내 공시·실적) + 상용 카탈리스트 API(PDUFA) + 학회 일정 수집기 연동,
  수집 스케줄러 + API 서버 + D-day 알림(푸시), 종목 즐겨찾기/검색 추가 권장.
