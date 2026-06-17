/* BIO Catalyst - 다크 미니멀 피드/캘린더 (서버 없음, data.js 정적 데이터) */
(function () {
  "use strict";

  const DATA = window.BIO_CALENDAR_DATA || { events: [], count: 0, generatedAt: "" };
  const EVENTS = DATA.events || [];

  const TYPE_LABEL = { clinical: "임상", regulatory: "규제", deal: "딜·L/O", conference: "학회", earnings: "실적" };
  const FLAG = { KR: "🇰🇷", US: "🇺🇸" };
  const WD = ["일", "월", "화", "수", "목", "금", "토"];

  const TODAY = startOfDay(new Date());
  const TODAY_S = ymd(TODAY);

  const state = { view: "feed", country: "ALL", type: "ALL", year: TODAY.getFullYear(), month: TODAY.getMonth(), selectedDate: TODAY_S };

  /* ---------- utils ---------- */
  function startOfDay(d) { const x = new Date(d); x.setHours(0, 0, 0, 0); return x; }
  function pad(n) { return String(n).padStart(2, "0"); }
  function ymd(d) { return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; }
  function parseYmd(s) { const [y, m, d] = s.split("-").map(Number); return new Date(y, m - 1, d); }
  function ddays(s) { return Math.round((parseYmd(s) - TODAY) / 86400000); }
  function esc(s) { return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
  function shortWhen(disp) { return disp.replace(/^\d{4}년\s*/, ""); }

  function filtered() {
    return EVENTS.filter((e) => {
      if (state.country !== "ALL" && e.country !== state.country) return false;
      if (state.type !== "ALL" && e.type !== state.type) return false;
      return true;
    });
  }

  /* ---------- 우측 시점 표기 (종목과 함께 1순위 강조) ---------- */
  function whenParts(e) {
    const dd = ddays(e.date);
    const o = parseYmd(e.date);
    if (e.datePrecision === "day") {
      const main = dd === 0 ? "오늘" : dd > 0 ? `D-${dd}` : `D+${-dd}`;
      const hot = e.isCatalyst && dd >= 0 && dd <= 21;
      return { main, sub: `${o.getMonth() + 1}.${o.getDate()}`, hot };
    }
    return { main: shortWhen(e.dateDisplay), sub: "예상", hot: false };
  }

  /* ---------- 리스트 행 ---------- */
  function rowHtml(e) {
    const icon = FLAG[e.country] || "🌐";
    const w = whenParts(e);
    const tk = e.ticker && e.ticker !== "-" ? `<span class="tk">${esc(e.ticker)}</span>` : "";
    return `<div class="row ${e.isCatalyst ? "cat" : ""}" data-id="${e.id}">
      <div class="ico">${icon}<span class="tdot ${e.type}"></span></div>
      <div class="row-main">
        <div class="row-co">${e.isCatalyst ? '<span class="star">★</span>' : ""}<span class="co">${esc(e.company)}</span>${tk}</div>
        <div class="row-title"><span class="ty ${e.type}">${TYPE_LABEL[e.type] || e.type}</span>${esc(e.title)}</div>
      </div>
      <div class="row-when">
        <span class="w-main ${w.hot ? "hot" : ""}">${esc(w.main)}</span>
        <span class="w-sub">${esc(w.sub)}</span>
      </div>
    </div>`;
  }

  /* ---------- 히어로 ---------- */
  function renderHero() {
    const up = filtered().filter((e) => e.date >= TODAY_S);
    const cats = up.filter((e) => e.isCatalyst).length;
    const el = document.getElementById("heroTitle");
    if (!up.length) { el.innerHTML = "예정된 일정이 없어요"; return; }
    el.innerHTML = `예정된 핵심 카탈리스트 <b>${cats}건</b>을<br>한눈에 확인하세요`;
  }

  /* ---------- 피드 ---------- */
  function groupLabel(key) {
    const [y, m] = key.split("-").map(Number);
    if (y === TODAY.getFullYear() && m === TODAY.getMonth() + 1) return { txt: "이번 달", now: true };
    if (y === TODAY.getFullYear()) return { txt: `${m}월`, now: false };
    return { txt: `${y}년 ${m}월`, now: false };
  }
  function renderFeed() {
    renderHero();
    const list = filtered().filter((e) => e.date >= TODAY_S).sort((a, b) => (a.date === b.date ? 0 : a.date < b.date ? -1 : 1));
    const box = document.getElementById("feedList");
    if (!list.length) { box.innerHTML = `<div class="empty">조건에 맞는 다가오는 일정이 없어요.<br>필터를 바꿔보세요.</div>`; return; }
    const groups = {};
    list.forEach((e) => { const k = e.date.slice(0, 7); (groups[k] = groups[k] || []).push(e); });
    let html = "";
    Object.keys(groups).sort().forEach((k) => {
      const g = groupLabel(k);
      html += `<div class="group ${g.now ? "now" : ""}">${g.txt}<span class="gc">${groups[k].length}</span></div>`;
      html += groups[k].map(rowHtml).join("");
    });
    box.innerHTML = html;
    bindRows(box);
  }

  /* ---------- 캘린더 ---------- */
  function eventsByDate() { const m = {}; filtered().forEach((e) => { (m[e.date] = m[e.date] || []).push(e); }); return m; }
  function renderCalendar() {
    const grid = document.getElementById("calGrid");
    document.getElementById("monthLabel").textContent = `${state.year}년 ${state.month + 1}월`;
    const map = eventsByDate();
    const startW = new Date(state.year, state.month, 1).getDay();
    const dim = new Date(state.year, state.month + 1, 0).getDate();
    const prevDim = new Date(state.year, state.month, 0).getDate();
    let cells = "";
    for (let i = startW - 1; i >= 0; i--) cells += `<div class="cell other empty"><span class="n">${prevDim - i}</span></div>`;
    for (let d = 1; d <= dim; d++) {
      const ds = `${state.year}-${pad(state.month + 1)}-${pad(d)}`;
      const types = [...new Set((map[ds] || []).map((e) => e.type))].slice(0, 4);
      const dots = types.map((t) => `<i class="${t}"></i>`).join("");
      const cls = ["cell", ds === TODAY_S ? "today" : "", ds === state.selectedDate ? "sel" : ""].join(" ").trim();
      cells += `<button class="${cls}" data-date="${ds}"><span class="n">${d}</span><span class="dots">${dots}</span></button>`;
    }
    grid.innerHTML = cells;
    grid.querySelectorAll(".cell[data-date]").forEach((c) => c.addEventListener("click", () => { state.selectedDate = c.getAttribute("data-date"); renderCalendar(); renderDayDetail(); }));
    renderDayDetail();
  }
  function renderDayDetail() {
    const list = (eventsByDate()[state.selectedDate] || []).sort((a, b) => (a.importance < b.importance ? -1 : 1));
    const o = parseYmd(state.selectedDate);
    document.getElementById("dayDetailTitle").textContent = `${o.getMonth() + 1}월 ${o.getDate()}일 (${WD[o.getDay()]}) · ${list.length}건`;
    const box = document.getElementById("dayDetailList");
    box.innerHTML = list.length ? list.map(rowHtml).join("") : `<div class="empty">이 날짜엔 일정이 없어요.</div>`;
    bindRows(box);
  }

  /* ---------- 상세 시트 ---------- */
  function bindRows(c) { c.querySelectorAll("[data-id]").forEach((el) => el.addEventListener("click", () => openSheet(el.getAttribute("data-id")))); }
  function openSheet(id) {
    const e = EVENTS.find((x) => x.id === id);
    if (!e) return;
    const dd = ddays(e.date);
    const ddTxt = e.datePrecision === "day" ? (dd === 0 ? "오늘" : dd > 0 ? `D-${dd}` : `D+${-dd}`) : "예상 시점";
    const rows = [["기업", `${e.company}${e.ticker && e.ticker !== "-" ? ` (${e.ticker})` : ""}`], ["시장", `${FLAG[e.country] || ""} ${e.market || "-"}`]];
    if (e.drug) rows.push(["대상물질", e.drug]);
    if (e.indication) rows.push(["적응증/분야", e.indication]);
    if (e.phase) rows.push(["임상단계", e.phase]);
    if (e.status) rows.push(["상태", e.status]);
    rows.push(["출처", e.source || "-"]);
    document.getElementById("sheetBody").innerHTML = `
      <div class="s-kicker"><span class="tdot ${e.type}"></span>${TYPE_LABEL[e.type] || e.type}${e.isCatalyst ? ' <span class="cat">· ★ 카탈리스트</span>' : ""}</div>
      <h3>${esc(e.title)}</h3>
      <div class="s-when"><span class="big">${esc(e.dateDisplay)}</span><span class="dday">${ddTxt}</span><span class="sub">${WD[parseYmd(e.date).getDay()]}요일 기준</span></div>
      ${rows.map((r) => `<div class="s-row"><span>${r[0]}</span><span>${esc(String(r[1]))}</span></div>`).join("")}
      ${e.description ? `<div class="s-desc">${esc(e.description)}</div>` : ""}
      ${e.sourceUrl && e.sourceUrl !== "#" ? `<a class="s-link" href="${e.sourceUrl}" target="_blank" rel="noopener">출처 보기 ↗</a>` : ""}
      <div class="s-note">${e.datePrecision === "day" ? "투자 참고용 프로토타입입니다." : "정확한 날짜가 공개되지 않은 추정 일정입니다. 투자 참고용."}</div>`;
    document.getElementById("overlay").classList.remove("hidden");
  }

  /* ---------- 뷰/바인딩 ---------- */
  function setView(v) {
    state.view = v;
    document.querySelectorAll(".vt").forEach((t) => t.classList.toggle("active", t.dataset.view === v));
    document.getElementById("feedView").classList.toggle("hidden", v !== "feed");
    document.getElementById("calendarView").classList.toggle("hidden", v !== "calendar");
    rerender();
  }
  function rerender() { state.view === "feed" ? renderFeed() : renderCalendar(); }

  function init() {
    document.querySelectorAll("#countrySeg .fs").forEach((b) => b.addEventListener("click", () => {
      state.country = b.dataset.country;
      document.querySelectorAll("#countrySeg .fs").forEach((x) => x.classList.toggle("active", x === b));
      rerender();
    }));
    document.querySelectorAll("#typeTabs .tt").forEach((b) => b.addEventListener("click", () => {
      state.type = b.dataset.type;
      document.querySelectorAll("#typeTabs .tt").forEach((x) => x.classList.toggle("active", x === b));
      rerender();
    }));
    document.querySelectorAll(".vt").forEach((t) => t.addEventListener("click", () => setView(t.dataset.view)));
    document.getElementById("prevMonth").addEventListener("click", () => { state.month--; if (state.month < 0) { state.month = 11; state.year--; } renderCalendar(); });
    document.getElementById("nextMonth").addEventListener("click", () => { state.month++; if (state.month > 11) { state.month = 0; state.year++; } renderCalendar(); });
    document.getElementById("overlay").addEventListener("click", (e) => { if (e.target.id === "overlay") document.getElementById("overlay").classList.add("hidden"); });
    renderFeed();
  }
  document.addEventListener("DOMContentLoaded", init);
})();
