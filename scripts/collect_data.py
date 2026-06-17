#!/usr/bin/env python3
"""
바이오 일정 캘린더 - ClinicalTrials.gov API 전용 데이터 수집

ClinicalTrials.gov API v2(인증 불필요)에서 국내/미국 상장 바이오 기업의
Phase 2/3 임상시험 중 PrimaryCompletionDate(1차 평가지표 완료 예정일)가
향후인 건만 수집한다.

※ PrimaryCompletionDate는 '결과 발표일'이 아니라 레지스트리상 1차완료 예정일이다.
  출처 URL(NCT 페이지)에서 원문 필드를 직접 확인할 수 있다.
"""

import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, date

CTGOV_BASE = "https://clinicaltrials.gov/api/v2/studies"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
WEB_DIR = os.path.join(ROOT, "web")

COMPANIES = [
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
    today = date.today().isoformat()
    if sort_date < today:
        return None

    overall = status.get("overallStatus", "UNKNOWN")
    if overall in ("TERMINATED", "WITHDRAWN", "SUSPENDED"):
        return None

    conditions = cond.get("conditions", []) or []
    indication = conditions[0] if conditions else ""
    phase_kr = PHASE_KR.get(phase, phase)
    is_p3 = phase in ("PHASE3", "PHASE2/PHASE3")

    if indication:
        title = f"{indication} {phase_kr} 1차완료 예정"
    else:
        title = f"{phase_kr} 1차완료 예정"

    return {
        "id": f"ct-{nct}",
        "nctId": nct,
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
        "source": "ClinicalTrials.gov API v2",
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
                seen.add(ev["id"])
                events.append(ev)
                n += 1
        print(f"  - {meta['spons']:30s} {n}건")
        time.sleep(0.25)
    return events


def main():
    print("ClinicalTrials.gov API v2 수집 중...")
    events = collect_clinical()
    imp_rank = {"high": 0, "medium": 1, "low": 2}
    events.sort(key=lambda e: (e["date"], imp_rank.get(e.get("importance"), 3)))
    print(f"  => 총 {len(events)}건 (향후 1차완료 예정, Phase 2/3)")

    payload = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "count": len(events),
        "sources": ["ClinicalTrials.gov API v2"],
        "events": events,
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(WEB_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "events.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    with open(os.path.join(WEB_DIR, "data.js"), "w", encoding="utf-8") as f:
        f.write("// 자동 생성 (scripts/collect_data.py)\n")
        f.write("window.BIO_CALENDAR_DATA = ")
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write(";\n")

    p3 = sum(1 for e in events if e.get("isCatalyst"))
    print(f"저장 완료: data/events.json, web/data.js (3상 {p3}건)")


if __name__ == "__main__":
    main()
