/* BIO Catalyst - ClinicalTrials.gov API 데이터 전용 */
(function () {
  "use strict";

  const DATA = window.BIO_CALENDAR_DATA || { events: [], count: 0, generatedAt: "" };
  const EVENTS = DATA.events || [];
  const FLAG = { KR: "🇰🇷", US: "🇺🇸" };
  const WD = ["일", "월", "화", "수", "목", "금", "토"];

  const TODAY = startOfDay(new Date());
  const TODAY_S = ymd(TODAY);

  const state = { view: "feed", country: "ALL", phase: "ALL", year: TODAY.getFullYear(), month: TODAY.getMonth(), selectedDate: TODAY_S };

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
      if (state.phase === "3" && !e.phase.includes("3")) return false;
      if (state.phase === "2" && e.phase !== "2상") return false;
      return true;
    });
  }

  function whenParts(e) {
    const dd = ddays(e.date);
    const o = parseYmd(e.date);
    if (e.datePrecision === "day") {
      const main = dd === 0 ? "오늘" : dd > 0 ? `D-${dd}` : `D+${-dd}`;
      const hot = e.isCatalyst && dd >= 0 && dd <= 21;
      return { main, sub: `${o.getMonth() + 1}.${o.getDate()}`, hot };
    }
    return { main: shortWhen(e.dateDisplay), sub: "등록", hot: false };
  }

  function rowHtml(e) {
    const icon = FLAG[e.country] || "🌐";
    const w = whenParts(e);
    const tk = e.ticker ? `<span class="tk">${esc(e.ticker)}</span>` : "";
    return `<div class="row ${e.isCatalyst ? "cat" : ""}" data-id="${e.id}">
      <div class="ico">${icon}<span class="tdot clinical"></span></div>
      <div class="row-main">
        <div class="row-co">${e.isCatalyst ? '<span class="star">★</span>' : ""}<span class="co">${esc(e.company)}</span>${tk}</div>
        <div class="row-title">${esc(e.title)}</div>
      </div>
      <div class="row-when">
        <span class="w-main ${w.hot ? "hot" : ""}">${esc(w.main)}</span>
        <span class="w-sub">${esc(w.sub)}</span>
      </div>
    </div>`;
  }

  function renderHero() {
    const up = filtered().filter((e) => e.date >= TODAY_S);
    const p3 = up.filter((e) => e.isCatalyst).length;
    const el = document.getElementById("heroTitle");
    if (!up.length) { el.innerHTML = "향후 1차완료 예정 임상이 없어요"; return; }
    el.innerHTML = `향후 1차완료 예정 임상 <b>${up.length}건</b><br><span style="font-size:0.72em;font-weight:600;color:var(--ink-2)">3상 ${p3}건 · ClinicalTrials.gov</span>`;
  }

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
    if (!list.length) {
      box.innerHTML = `<div class="empty">조건에 맞는 임상 일정이 없어요.<br>필터를 바꿔보세요.</div>`;
      return;
    }
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
      const cnt = (map[ds] || []).length;
      const dots = cnt ? `<i class="clinical"></i>` : "";
      const cls = ["cell", ds === TODAY_S ? "today" : "", ds === state.selectedDate ? "sel" : ""].join(" ").trim();
      cells += `<button class="${cls}" data-date="${ds}"><span class="n">${d}</span><span class="dots">${dots}</span></button>`;
    }
    grid.innerHTML = cells;
    grid.querySelectorAll(".cell[data-date]").forEach((c) => c.addEventListener("click", () => {
      state.selectedDate = c.getAttribute("data-date"); renderCalendar(); renderDayDetail();
    }));
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

  function bindRows(c) { c.querySelectorAll("[data-id]").forEach((el) => el.addEventListener("click", () => openSheet(el.getAttribute("data-id")))); }

  function openSheet(id) {
    const e = EVENTS.find((x) => x.id === id);
    if (!e) return;
    const dd = ddays(e.date);
    const ddTxt = e.datePrecision === "day" ? (dd === 0 ? "오늘" : dd > 0 ? `D-${dd}` : `D+${-dd}`) : "월 단위 등록";
    const rows = [
      ["기업", `${e.company} (${e.ticker})`],
      ["시장", `${FLAG[e.country] || ""} ${e.market || "-"}`],
      ["NCT ID", e.nctId || e.id.replace("ct-", "")],
      ["임상단계", e.phase || "-"],
      ["상태", e.status || "-"],
    ];
    if (e.indication) rows.push(["적응증", e.indication]);
    rows.push(["출처", e.source || "-"]);
    document.getElementById("sheetBody").innerHTML = `
      <div class="s-kicker"><span class="tdot clinical"></span>임상${e.isCatalyst ? ' <span class="cat">· 3상</span>' : ""}</div>
      <h3>${esc(e.title)}</h3>
      <div class="s-when"><span class="big">${esc(e.dateDisplay)}</span><span class="dday">${ddTxt}</span><span class="sub">Primary Completion</span></div>
      ${rows.map((r) => `<div class="s-row"><span>${r[0]}</span><span>${esc(String(r[1]))}</span></div>`).join("")}
      ${e.description ? `<div class="s-desc">${esc(e.description)}</div>` : ""}
      <a class="s-link" href="${e.sourceUrl}" target="_blank" rel="noopener">ClinicalTrials.gov에서 확인 ↗</a>
      <div class="s-note">Primary Completion Date는 1차 평가지표 완료 예정일입니다. 결과 발표일과 다를 수 있습니다.</div>`;
    document.getElementById("overlay").classList.remove("hidden");
  }

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
    document.querySelectorAll("#phaseTabs .tt").forEach((b) => b.addEventListener("click", () => {
      state.phase = b.dataset.phase;
      document.querySelectorAll("#phaseTabs .tt").forEach((x) => x.classList.toggle("active", x === b));
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
