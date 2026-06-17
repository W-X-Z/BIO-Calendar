# 🧬 BIO Catalyst — 국내·미국 상장 바이오 임상 일정 (프로토타입)

**ClinicalTrials.gov API v2**에서 수집한 Phase 2/3 임상시험의 **Primary Completion Date**(1차 평가지표 완료 예정일)를
모바일 우선 화면에서 리스트(피드)로 보여주는 프로토타입입니다.

> 모든 데이터는 ClinicalTrials.gov API에서 직접 수집하며, 출처 링크(NCT 페이지)에서 원문을 확인할 수 있습니다.
> Primary Completion Date는 **결과 발표일이 아닙니다.**

## 🌐 Live Demo

**https://w-x-z.github.io/BIO-Calendar/**

`main` 브랜치 push 시 GitHub Actions가 `web/`을 GitHub Pages로 자동 배포합니다.

## 📁 구조

```
BIO-Calendar/
├── scripts/collect_data.py    # ClinicalTrials.gov API 수집
├── data/events.json           # 수집 결과
└── web/                       # 모바일 웹 (서버리스)
```

## 🔌 데이터 소스

| 항목 | 내용 |
|------|------|
| API | [ClinicalTrials.gov API v2](https://clinicaltrials.gov/data-api/api) (인증 불필요) |
| 대상 | 국내 15 + 미국 6 상장 바이오 기업 (스폰서명 검색) |
| 필터 | Phase 2/3, 향후 Primary Completion Date, 중단/철회 제외 |
| 출처 URL | `https://clinicaltrials.gov/study/{NCTId}` |

## 🚀 실행

```bash
# 데이터 수집 (인터넷 필요)
python3 scripts/collect_data.py

# 로컬 확인
cd web && python3 -m http.server 8123
```

## ✨ 기능

- **피드**: 종목명·티커 + 1차완료 예정일, 월별 그룹
- **필터**: 국가(전체/국내/미국) · 단계(전체/3상/2상)
- **캘린더**: 월별 달력 + 날짜별 임상 목록
- **상세 시트**: NCT ID, 적응증, 상태, ClinicalTrials.gov 원문 링크

## 🧭 한계 & 다음 단계

- IR성 카탈리스트(PDUFA, 학회 발표, 실적 등)는 API로 제공되지 않아 **미포함**
- 운영 시 DART(국내 공시), SEC EDGAR, 보도자료 기반 카탈리스트 레이어 추가 가능
