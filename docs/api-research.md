# 바이오 일정 캘린더 — 공개 API / 데이터 소스 조사

국내/미국 상장 바이오 기업의 "일정"을 만들기 위한 주요 이벤트 유형과,
각 유형별로 사용할 수 있는 공개 API / 엔드포인트를 정리한다.

## 1. 캘린더에 담을 이벤트 유형

| 유형 | 설명 | 대표 데이터 소스 |
|------|------|------------------|
| 임상 (clinical) | 임상시험 시작/1차 완료(=결과 발표 시점 추정)/종료 | ClinicalTrials.gov, 식약처 임상정보 |
| 규제 (regulatory) | FDA PDUFA(허가 결정 예정일), 승인, 자문위(AdCom), 식약처 허가 | openFDA, FDA 보도자료, 식약처 |
| 학회 (conference) | JPM Healthcare, ASCO, ESMO, AACR, ASH 등 발표 | 각 학회 공식 일정(수기 큐레이션) |
| 실적 (earnings) | 분기 실적발표 | SEC EDGAR(8-K/10-Q), DART, IR 캘린더 |
| 공시 (disclosure) | 정기/수시 공시, 주총 | DART(국내), SEC EDGAR(미국) |

---

## 2. 핵심 공개 API (인증 불필요 — 본 프로토타입에서 실제 수집에 사용)

### 2.1 ClinicalTrials.gov API v2  ✅ 사용
- 엔드포인트: `https://clinicaltrials.gov/api/v2/studies`
- 인증: **불필요** (무료, rate limit 관대)
- 주요 파라미터
  - `query.spons=<스폰서명>` : 제약/바이오 회사명으로 검색
  - `fields=NCTId,BriefTitle,LeadSponsorName,OverallStatus,Phase,PrimaryCompletionDate,StudyFirstPostDate,Conditions`
  - `pageSize`, `pageToken`
- 캘린더 활용: `PrimaryCompletionDate`(1차 평가지표 완료일) → **임상 결과(top-line) 발표 시점 추정**으로 사용.
- 예시
  ```
  GET https://clinicaltrials.gov/api/v2/studies?query.spons=Celltrion&pageSize=50&fields=NCTId,BriefTitle,OverallStatus,Phase,PrimaryCompletionDate,LeadSponsorName,Conditions
  ```

### 2.2 openFDA  ✅ (참고용)
- 엔드포인트: `https://api.fda.gov/drug/drugsfda.json`, `.../drug/label.json`
- 인증: 불필요(키 없이 사용 가능, 키 발급 시 rate limit 상향)
- 활용: 과거 승인 이력/제출(submission) 정보. 단, **미래 PDUFA 예정일은 제공하지 않음** → 미래 규제 일정은 별도 큐레이션 필요.

### 2.3 SEC EDGAR  ✅ (참고용)
- 엔드포인트: `https://data.sec.gov/submissions/CIK<10자리>.json`
- 인증: 불필요. 단 `User-Agent` 헤더 필수.
- 활용: 미국 상장사 공시(10-Q/8-K) 제출일 → 실적/공시 이벤트. 미래 실적 예정일은 추정 필요.

---

## 3. 인증/키가 필요한 소스 (프로토타입에서는 미사용, 운영 시 권장)

### 3.1 DART 오픈API (국내 전자공시) — 운영 단계 필수
- 엔드포인트: `https://opendart.fss.or.kr/api/list.json`
- 인증: **API Key 필요**(무료 발급, open.fss.or.kr)
- 활용: 국내 상장사 정기/수시 공시, 주총, IR 일정. 국내 "공시·실적" 캘린더의 핵심.

### 3.2 식약처(MFDS) 의약품안전나라 / 공공데이터포털
- 임상시험 승인 현황, 의약품 허가 정보 API (data.go.kr, 인증키 필요)
- 활용: 국내 임상/허가 일정.

### 3.3 KIND (한국거래소 기업공시채널)
- IR 일정, 실적발표 예고. 공식 오픈API는 제한적 → 크롤링/수기 보완.

---

## 4. 미래 일정(PDUFA·학회·실적 예정일) 처리 방침

- 미래의 **PDUFA 날짜, 학회 발표, 실적 예정일**은 단일 무료 공개 API로 일괄 제공되지 않는다.
  (BioPharmaCatalyst, Biotechgate 등 상용/유료 또는 IR 페이지 분산)
- 따라서 본 프로토타입에서는:
  - **임상 일정**: ClinicalTrials.gov에서 *실제 수집*.
  - **규제(PDUFA)·학회·실적**: 공개 보도자료/IR 기준의 **큐레이션 샘플**로 보완(스크립트 내 표기).
- 운영 전환 시: DART(국내 공시·실적) + 상용 카탈리스트 API(PDUFA) + 학회 공식 일정 수집기를 추가.

---

## 5. 본 프로토타입 데이터 파이프라인 요약

```
ClinicalTrials.gov API v2  ──┐
openFDA (참고)              ──┤→ scripts/collect_data.py → data/events.json → web/ (모바일 캘린더)
큐레이션(규제/학회/실적)    ──┘
```
