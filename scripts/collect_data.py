#!/usr/bin/env python3
"""
바이오 일정 캘린더 - 카탈리스트(투자 이벤트) 중심 데이터 수집 스크립트

설계 의도
---------
이 서비스의 핵심은 "투자 아이디어를 얻을 수 있는 예정 이벤트(카탈리스트)" 수집이다.
따라서 데이터를 두 갈래로 모은다.

(A) ClinicalTrials.gov API v2 (인증 불필요)
    - Phase 2/3 위주의 임상시험 중 '향후/최근' 1차완료 예정 건을 수집.
    - PrimaryCompletionDate(YYYY-MM)를 임상 데이터 readout '추정 시점'으로 사용.
    - 단, 이 값은 "결과 발표일"이 아니라 "1차지표 데이터 수집 완료 예정일"이라는 한계가 있음.

(B) 큐레이션 카탈리스트 (공개 IR/뉴스/리포트 기준, 추정 일정)
    - "코오롱티슈진 TG-C 미국 3상 결과 발표"처럼 회사가 예고한 핵심 이벤트.
    - 무료 단일 API로 제공되지 않으므로 직접 큐레이션. 날짜는 일/월/분기/반기 단위 허용.

이벤트 스키마
-------------
{
  id, date(정렬용 YYYY-MM-DD), dateDisplay, datePrecision(day|month|quarter|half|year),
  company, ticker, country, market,
  type(clinical|regulatory|conference|earnings|deal),
  phase?, status?, drug?, indication?,
  isCatalyst(bool), importance(high|medium|low),
  title, description, source, sourceUrl
}
"""

import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime

CTGOV_BASE = "https://clinicaltrials.gov/api/v2/studies"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
WEB_DIR = os.path.join(ROOT, "web")

# 임상 데이터 readout 추정치를 이 날짜 이후 건만 수집(과거 잡음 제거)
CLINICAL_CUTOFF = "2025-07"

COMPANIES = [
    # ----- 국내(KR) -----
    {"spons": "Celltrion",                 "name": "셀트리온",        "ticker": "068270", "country": "KR", "market": "KOSPI"},
    {"spons": "Samsung Bioepis",           "name": "삼성바이오에피스", "ticker": "207940", "country": "KR", "market": "KOSPI"},
    {"spons": "SK Life Science",           "name": "SK바이오팜",      "ticker": "326030", "country": "KR", "market": "KOSPI"},
    {"spons": "Hanmi Pharmaceutical",      "name": "한미약품",        "ticker": "128940", "country": "KR", "market": "KOSPI"},
    {"spons": "Yuhan Corporation",         "name": "유한양행",        "ticker": "000100", "country": "KR", "market": "KOSPI"},
    {"spons": "Daewoong Pharmaceutical",   "name": "대웅제약",        "ticker": "069620", "country": "KR", "market": "KOSPI"},
    {"spons": "Alteogen",                  "name": "알테오젠",        "ticker": "196170", "country": "KR", "market": "KOSDAQ"},
    {"spons": "LigaChem Biosciences",      "name": "리가켐바이오",     "ticker": "141080", "country": "KR", "market": "KOSDAQ"},
    {"spons": "ABL Bio",                   "name": "에이비엘바이오",   "ticker": "298380", "country": "KR", "market": "KOSDAQ"},
    {"spons": "HLB",                       "name": "HLB",            "ticker": "028300", "country": "KR", "market": "KOSDAQ"},
    {"spons": "Kolon TissueGene",          "name": "코오롱티슈진",     "ticker": "950160", "country": "KR", "market": "KOSDAQ"},
    {"spons": "Bridge Biotherapeutics",    "name": "브릿지바이오",     "ticker": "288330", "country": "KR", "market": "KOSDAQ"},
    {"spons": "GI Innovation",             "name": "지아이이노베이션", "ticker": "358570", "country": "KR", "market": "KOSDAQ"},
    {"spons": "Genexine",                  "name": "제넥신",          "ticker": "095700", "country": "KR", "market": "KOSDAQ"},
    {"spons": "Mezzion Pharma",            "name": "메지온",          "ticker": "140410", "country": "KR", "market": "KOSDAQ"},
    # ----- 미국(US) -----
    {"spons": "ModernaTX",                 "name": "Moderna",        "ticker": "MRNA",   "country": "US", "market": "NASDAQ"},
    {"spons": "Vertex Pharmaceuticals",    "name": "Vertex",         "ticker": "VRTX",   "country": "US", "market": "NASDAQ"},
    {"spons": "Regeneron Pharmaceuticals", "name": "Regeneron",      "ticker": "REGN",   "country": "US", "market": "NASDAQ"},
    {"spons": "Alnylam Pharmaceuticals",   "name": "Alnylam",        "ticker": "ALNY",   "country": "US", "market": "NASDAQ"},
    {"spons": "Sarepta Therapeutics",      "name": "Sarepta",        "ticker": "SRPT",   "country": "US", "market": "NASDAQ"},
    {"spons": "BioNTech SE",               "name": "BioNTech",       "ticker": "BNTX",   "country": "US", "market": "NASDAQ"},
]

PHASE_KR = {
    "EARLY_PHASE1": "초기 1상", "PHASE1": "1상", "PHASE1/PHASE2": "1/2상",
    "PHASE2": "2상", "PHASE2/PHASE3": "2/3상", "PHASE3": "3상", "PHASE4": "4상",
    "NA": "기타",
}
STATUS_KR = {
    "RECRUITING": "모집중", "ACTIVE_NOT_RECRUITING": "진행중(모집종료)",
    "COMPLETED": "완료", "NOT_YET_RECRUITING": "모집예정",
    "ENROLLING_BY_INVITATION": "초청모집", "TERMINATED": "중단",
    "SUSPENDED": "중지", "WITHDRAWN": "철회", "UNKNOWN": "미상",
}
# 임상 카탈리스트로 의미있는 단계만 수집(2/3상 위주)
KEEP_PHASES = {"PHASE2", "PHASE2/PHASE3", "PHASE3"}


def fetch_studies(spons, page_size=100):
    params = {
        "query.spons": spons,
        "pageSize": str(page_size),
        "fields": ",".join([
            "NCTId", "BriefTitle", "OverallStatus", "Phase",
            "PrimaryCompletionDate", "LeadSponsorName", "Condition",
        ]),
    }
    url = CTGOV_BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "bio-calendar-prototype/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def month_display(raw):
    """'2026-07' -> ('2026-07-01','2026년 7월','month'), '2026-07-15' -> (...,'2026-07-15','day')"""
    parts = raw.split("-")
    if len(parts) >= 3:
        return f"{parts[0]}-{parts[1]}-{parts[2]}", f"{parts[0]}-{parts[1]}-{parts[2]}", "day"
    if len(parts) == 2:
        return f"{parts[0]}-{parts[1]}-01", f"{parts[0]}년 {int(parts[1])}월", "month"
    return f"{parts[0]}-01-01", f"{parts[0]}년", "year"


def study_to_event(study, meta):
    ps = study.get("protocolSection", {})
    ident = ps.get("identificationModule", {})
    status = ps.get("statusModule", {})
    design = ps.get("designModule", {})
    cond = ps.get("conditionsModule", {})

    nct = ident.get("nctId")
    raw = status.get("primaryCompletionDateStruct", {}).get("date")
    if not nct or not raw:
        return None

    phases = design.get("phases", []) or ["NA"]
    phase = phases[0]
    if phase not in KEEP_PHASES:
        return None

    sort_date, disp, prec = month_display(raw)
    if sort_date[:7] < CLINICAL_CUTOFF:
        return None  # 과거 잡음 제거

    overall = status.get("overallStatus", "UNKNOWN")
    if overall in ("TERMINATED", "WITHDRAWN", "SUSPENDED"):
        return None

    conditions = cond.get("conditions", []) or []
    indication = conditions[0] if conditions else ""
    phase_kr = PHASE_KR.get(phase, phase)
    is_p3 = phase in ("PHASE3", "PHASE2/PHASE3")

    # 제목은 '이벤트' 중심(회사명은 종목 필드로 별도 강조 표기)
    if indication:
        title = f"{indication} {phase_kr} 데이터 readout 예상"
    else:
        title = f"{phase_kr} 임상 데이터 readout 예상"

    return {
        "id": f"ct-{nct}",
        "date": sort_date,
        "dateDisplay": disp,
        "datePrecision": prec,
        "company": meta["name"],
        "ticker": meta["ticker"],
        "country": meta["country"],
        "market": meta["market"],
        "type": "clinical",
        "phase": phase_kr,
        "status": STATUS_KR.get(overall, overall),
        "indication": indication,
        "isCatalyst": is_p3,
        "importance": "high" if is_p3 else "medium",
        "title": title,
        "description": ident.get("briefTitle", ""),
        "source": "ClinicalTrials.gov (1차완료 예정일 기준 추정)",
        "sourceUrl": f"https://clinicaltrials.gov/study/{nct}",
    }


def collect_clinical():
    events, seen = [], set()
    for meta in COMPANIES:
        try:
            data = fetch_studies(meta["spons"])
        except Exception as e:
            print(f"  ! {meta['spons']} 수집 실패: {e}")
            continue
        n = 0
        for s in data.get("studies", []):
            ev = study_to_event(s, meta)
            if ev and ev["id"] not in seen:
                seen.add(ev["id"]); events.append(ev); n += 1
        print(f"  - {meta['spons']:30s} 임상 카탈리스트 {n}건")
        time.sleep(0.25)
    return events


def C(id, date, disp, prec, company, ticker, country, market, type_, title, desc,
      importance="high", drug="", indication="", source="큐레이션(공개 IR/뉴스 기준·추정)", url="#",
      is_catalyst=True, phase="", status=""):
    return {
        "id": id, "date": date, "dateDisplay": disp, "datePrecision": prec,
        "company": company, "ticker": ticker, "country": country, "market": market,
        "type": type_, "phase": phase, "status": status, "drug": drug, "indication": indication,
        "isCatalyst": is_catalyst, "importance": importance,
        "title": title, "description": desc, "source": source, "sourceUrl": url,
    }


def curated_events():
    """공개 IR/뉴스/리포트 기준으로 큐레이션한 주요 카탈리스트(추정 일정·샘플)."""
    return [
        # ===== 국내 핵심 카탈리스트 =====
        C("cat-kolon-tgc", "2026-07-01", "2026년 7월", "month", "코오롱티슈진", "950160", "KR", "KOSDAQ",
          "clinical", "TG-C(인보사) 미국 임상 3상 톱라인 결과 발표 예상",
          "골관절염 세포·유전자치료제 TG-C의 미국 FDA 임상 3상 주요 결과(톱라인) 발표 예정. 성공 시 글로벌 상업화·기술이전 모멘텀.",
          drug="TG-C (Invossa)", indication="무릎 골관절염", phase="3상", importance="high",
          url="https://clinicaltrials.gov/study/NCT03203330"),
        C("cat-hlb-rivo", "2026-09-01", "2026년 3분기", "quarter", "HLB", "028300", "KR", "KOSDAQ",
          "regulatory", "리보세라닙+캄렐리주맙 간암 1차 FDA 재심사 결정 예상",
          "간암 1차 치료제 병용요법의 FDA 재심사(Resubmission) 허가 여부 결정 예정. 허가 시 첫 국산 항암제 FDA 승인.",
          drug="리보세라닙", indication="간세포암(HCC)", importance="high",
          url="https://www.hlb.co.kr"),
        C("cat-yuhan-lazcluze", "2026-08-01", "2026년 하반기", "half", "유한양행", "000100", "KR", "KOSPI",
          "regulatory", "렉라자(레이저티닙) 유럽 EMA 승인 및 글로벌 매출 마일스톤 예상",
          "J&J 리브리반트 병용(MARIPOSA) 기반 글로벌 확대. 마일스톤·로열티 유입 모멘텀.",
          drug="레이저티닙", indication="비소세포폐암(EGFR)", importance="high",
          url="https://www.yuhan.co.kr"),
        C("cat-alteogen-sc", "2026-10-01", "2026년 4분기", "quarter", "알테오젠", "196170", "KR", "KOSDAQ",
          "deal", "ALT-B4 기반 키트루다 SC 글로벌 출시·마일스톤 예상",
          "MSD 키트루다 피하주사(SC) 제형 출시 진전에 따른 마일스톤·로열티. 추가 빅파마 기술이전 가능성.",
          drug="ALT-B4 (히알루로니다제)", indication="제형 플랫폼", importance="high",
          url="https://www.alteogen.com"),
        C("cat-abl-301", "2026-12-01", "2026년 하반기", "half", "에이비엘바이오", "298380", "KR", "KOSDAQ",
          "clinical", "ABL301(파킨슨, 사노피 기술이전) 임상 1상 진전 데이터 예상",
          "그랩바디-B(BBB 셔틀) 적용 파킨슨 치료제. 사노피 글로벌 개발 단계 진입에 따른 마일스톤.",
          drug="ABL301", indication="파킨슨병", importance="medium",
          url="https://www.ablbio.com"),
        C("cat-ligachem-adc", "2026-11-01", "2026년 하반기", "half", "리가켐바이오", "141080", "KR", "KOSDAQ",
          "deal", "ADC 파이프라인 추가 글로벌 기술이전 기대",
          "LCB14(Trop2 ADC) 등 ADC 플랫폼 기반 추가 빅파마 L/O 및 마일스톤 유입 가능성.",
          drug="LCB ADC 플랫폼", indication="고형암(ADC)", importance="medium",
          url="https://www.ligachem.com"),
        C("cat-bridge-877", "2026-12-01", "2026년 하반기", "half", "브릿지바이오", "288330", "KR", "KOSDAQ",
          "clinical", "BBT-877(특발성폐섬유증) 임상 2상 톱라인 결과 예상",
          "autotaxin 저해제 IPF 치료제 2상 주요 결과. 성공 시 기술이전 재추진 기대.",
          drug="BBT-877", indication="특발성폐섬유증(IPF)", importance="high",
          url="https://www.bridgebiotherapeutics.com"),
        C("cat-mezzion-udena", "2026-09-01", "2026년 하반기", "half", "메지온", "140410", "KR", "KOSDAQ",
          "regulatory", "유데나필(폰탄수술 환자) FDA 허가 재추진 진행",
          "폰탄 수술 선천성 심장질환 환자 대상 치료제 FDA 재추진 관련 업데이트.",
          drug="유데나필", indication="단심실(폰탄)", importance="medium",
          url="https://www.mezzion.co.kr"),
        C("cat-sk-ceno", "2026-07-31", "2026-07-31", "day", "SK바이오팜", "326030", "KR", "KOSPI",
          "earnings", "SK바이오팜 2026 2분기 실적·세노바메이트 매출 가이던스 예상",
          "엑스코프리(세노바메이트) 미국 처방 성장세 및 흑자 지속 여부 확인.",
          drug="세노바메이트", indication="뇌전증", importance="medium", is_catalyst=False,
          url="https://www.skbp.com"),
        C("cat-celltrion-zymfentra", "2026-10-01", "2026년 4분기", "quarter", "셀트리온", "068270", "KR", "KOSPI",
          "regulatory", "짐펜트라(미국) 처방 확대 및 신규 바이오시밀러 허가 예상",
          "짐펜트라 미국 시장 침투 및 후속 바이오시밀러 FDA 허가 모멘텀.",
          indication="자가면역/바이오시밀러", importance="medium",
          url="https://www.celltrion.com"),
        C("cat-samsung-bio", "2026-08-01", "2026년 하반기", "half", "삼성바이오로직스", "207940", "KR", "KOSPI",
          "deal", "5공장 본격 가동 및 대형 CDMO 수주 모멘텀 예상",
          "세계 최대 생산능력 기반 신규 수주·증설 발표 가능성.",
          indication="CDMO", importance="medium", is_catalyst=False,
          url="https://www.samsungbiologics.com"),

        # ===== 미국 핵심 카탈리스트 =====
        C("cat-vrtx-pain", "2026-08-15", "2026-08-15", "day", "Vertex", "VRTX", "US", "NASDAQ",
          "regulatory", "수제트리진(통증) 적응증 확대 PDUFA 결정 예상",
          "비마약성 진통제 JOURNAVX(suzetrigine) 추가 적응증 허가 결정. 블록버스터 잠재력.",
          drug="suzetrigine", indication="급성·신경병성 통증", importance="high",
          url="https://www.vrtx.com"),
        C("cat-srpt-gtx", "2026-09-01", "2026년 하반기", "half", "Sarepta", "SRPT", "US", "NASDAQ",
          "clinical", "차세대 DMD 유전자치료제 임상 데이터 업데이트 예상",
          "엘레비디스 후속 및 안전성 이슈 관련 업데이트. 변동성 큰 카탈리스트.",
          indication="뒤셴근이영양증(DMD)", importance="high",
          url="https://www.sarepta.com"),
        C("cat-mrna-combo", "2026-10-01", "2026년 4분기", "quarter", "Moderna", "MRNA", "US", "NASDAQ",
          "clinical", "독감+코로나 콤보 백신(mRNA-1083) 후기 데이터/허가 진전 예상",
          "콤보 백신 및 RSV·항암 mRNA 파이프라인 진전. 매출 반등 관건.",
          drug="mRNA-1083", indication="호흡기 백신", importance="medium",
          url="https://www.modernatx.com"),
        C("cat-bntx-327", "2026-11-01", "2026년 하반기", "half", "BioNTech", "BNTX", "US", "NASDAQ",
          "clinical", "BNT327(PD-L1xVEGF 이중항체) 글로벌 3상 데이터 예상",
          "BMS와 공동개발 이중항체의 후기 임상 데이터. 차세대 면역항암 핵심.",
          drug="BNT327", indication="고형암(면역항암)", importance="high",
          url="https://www.biontech.com"),
        C("cat-alny-pdufa", "2026-09-30", "2026-09-30", "day", "Alnylam", "ALNY", "US", "NASDAQ",
          "regulatory", "RNAi 신규 적응증 PDUFA 결정 예상",
          "TTR 아밀로이드증 등 RNAi 파이프라인 적응증 확대 허가 결정.",
          indication="RNAi 치료제", importance="medium",
          url="https://www.alnylam.com"),
        C("cat-regn-update", "2026-12-01", "2026년 4분기", "quarter", "Regeneron", "REGN", "US", "NASDAQ",
          "clinical", "듀피젠트/EYLEA HD 적응증 확대 데이터 예상",
          "면역·안과 블록버스터 추가 적응증 임상 데이터 및 허가 진전.",
          importance="medium", is_catalyst=False,
          url="https://www.regeneron.com"),

        # ===== 학회(섹터 전반 카탈리스트) =====
        C("conf-asco-26", "2026-06-26", "2026.6.26–6.30", "day", "ASCO 2026", "-", "US", "-",
          "conference", "ASCO 2026 (미국임상종양학회)",
          "글로벌 항암 데이터의 최대 발표 무대. 국내외 항암 파이프라인 초록·구연 발표 집중.",
          importance="high", is_catalyst=False, source="큐레이션(학회 공식)", url="https://www.asco.org"),
        C("conf-esmo-26", "2026-10-17", "2026.10.17–10.21", "day", "ESMO 2026", "-", "US", "-",
          "conference", "ESMO Congress 2026 (유럽종양학회)",
          "유럽 최대 항암 학회. 하반기 항암 데이터 카탈리스트 집중.",
          importance="high", is_catalyst=False, source="큐레이션(학회 공식)", url="https://www.esmo.org"),
        C("conf-ash-26", "2026-12-05", "2026.12.5–12.8", "day", "ASH 2026", "-", "US", "-",
          "conference", "ASH 2026 (미국혈액학회)",
          "혈액암·세포치료(CAR-T) 데이터 발표 무대. 큐로셀·앱클론 등 관련주 모멘텀.",
          importance="medium", is_catalyst=False, source="큐레이션(학회 공식)", url="https://www.hematology.org"),
        C("conf-jpm-27", "2027-01-11", "2027.1.11–1.14", "day", "JPM Healthcare 2027", "-", "US", "-",
          "conference", "J.P. Morgan Healthcare Conference 2027",
          "글로벌 바이오/헬스케어 최대 IR 행사. 연초 기술이전·파트너십 발표 집중.",
          importance="high", is_catalyst=False, source="큐레이션(학회 공식)", url="https://www.jpmorgan.com"),
    ]


def main():
    print("[1/3] ClinicalTrials.gov 임상 카탈리스트 수집 중...")
    clinical = collect_clinical()
    print(f"  => 임상 카탈리스트 {len(clinical)}건")

    print("[2/3] 큐레이션 카탈리스트(IR/규제/학회/딜) 추가...")
    curated = curated_events()
    print(f"  => 큐레이션 {len(curated)}건")

    all_events = curated + clinical
    # 정렬: 날짜 오름차순, 동일 날짜는 중요도 high 우선
    imp_rank = {"high": 0, "medium": 1, "low": 2}
    all_events.sort(key=lambda e: (e["date"], imp_rank.get(e.get("importance"), 3)))

    payload = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "count": len(all_events),
        "sources": ["ClinicalTrials.gov API v2", "curated catalysts (IR/FDA/conference)"],
        "events": all_events,
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(WEB_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "events.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    with open(os.path.join(WEB_DIR, "data.js"), "w", encoding="utf-8") as f:
        f.write("// 자동 생성 파일 (scripts/collect_data.py). 직접 수정 금지.\n")
        f.write("window.BIO_CALENDAR_DATA = ")
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write(";\n")

    cat = sum(1 for e in all_events if e.get("isCatalyst"))
    print(f"[3/3] 저장 완료: 총 {len(all_events)}건 (카탈리스트 {cat}건)")


if __name__ == "__main__":
    main()
