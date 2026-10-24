// MateAI 데이터 비서 프론트(바닐라 JS). 백엔드 주소는 config.js 의 window.API_BASE_URL.
// 주 서버(Render)가 아직 없거나 잠들어 응답이 없으면 예비 서버(Vercel)로 바꾼다.
let API = (window.API_BASE_URL || "").replace(/\/$/, "");
const FALLBACK_API = "https://mateai-data-assistant-api.vercel.app";
async function pickApi() {
  try { const r = await fetch(API + "/health", { signal: AbortSignal.timeout(8000) }); if (r.ok) return; } catch {}
  API = FALLBACK_API;
}
const $ = (s) => document.querySelector(s);
const fmt = (n) => (n == null ? "-" : Math.round(n).toLocaleString("ko-KR"));
let convId = null;

async function api(path, opts = {}) {
  const t = setTimeout(() => $("#wake").classList.remove("hidden"), 3000); // 콜드스타트 안내
  try {
    const r = await fetch(API + path, { headers: { "Content-Type": "application/json" }, ...opts });
    if (!r.ok) {
      let d = ""; try { d = (await r.json()).detail; } catch {}
      throw new Error(`${r.status} ${typeof d === "string" ? d : JSON.stringify(d)}`);
    }
    return r.json();
  } finally { clearTimeout(t); $("#wake").classList.add("hidden"); }
}

// ---- 요약 ----
async function loadSummary() {
  const s = await api("/api/data/summary");
  $("#s-period").textContent = s.period; $("#s-count").textContent = `${s.count}개`;
  const m = s.metrics || {};
  $("#s-avg").textContent = `${fmt(m.average)}명`;
  $("#s-max").textContent = `${fmt(m.max)}명 (${m.max_date || "-"})`;
  $("#s-min").textContent = `${fmt(m.min)}명 (${m.min_date || "-"})`;
  const l = s.latest || {};
  $("#s-latest").textContent = `${fmt(l.value)}명 · ${l.date || "-"} (${l.yoy_pct == null ? "-" : (l.yoy_pct > 0 ? "+" : "") + l.yoy_pct + "%"})`;
  $("#s-trend").textContent = `추세: ${s.trend}`;
}

// ---- 채팅 ----
function addMsg(role, text, meta) {
  const d = document.createElement("div"); d.className = `msg ${role}`; d.textContent = text;
  if (meta) { const s = document.createElement("span"); s.className = "meta"; s.textContent = meta; d.appendChild(s); }
  $("#messages").appendChild(d); $("#messages").scrollTop = 1e9;
}
async function send(text) {
  if (!text.trim()) return;
  addMsg("user", text); $("#chat-input").value = "";
  $("#loading").classList.remove("hidden"); $("#chat-form button").disabled = true;
  try {
    const r = await api("/api/chat", { method: "POST", body: JSON.stringify({ message: text, conversation_id: convId }) });
    convId = r.conversation_id; $("#conv-title").textContent = `대화 ${convId.slice(0, 6)} · 자동 저장됨`;
    const tools = r.tool_calls?.length ? ` · 도구: ${r.tool_calls.map((t) => t.tool).join(", ")}` : "";
    addMsg("assistant", r.reply, `${r.mode === "offline" ? "오프라인 모드" : "GPT"} · 요약 ${r.summary.period}${tools}`);
  } catch (e) { addMsg("assistant", `오류: ${e.message}`); }
  finally { $("#loading").classList.add("hidden"); $("#chat-form button").disabled = false; }
}
$("#chat-form").onsubmit = (e) => { e.preventDefault(); send($("#chat-input").value); };
document.querySelectorAll(".chip").forEach((b) => (b.onclick = () => send(b.textContent)));
$("#new-chat").onclick = () => { convId = null; $("#messages").innerHTML = ""; $("#conv-title").textContent = "새 대화"; };

// ---- 데이터 관리 ----
let rows = [];
async function loadData() {
  rows = await api("/api/data?limit=2000");
  const tb = $("#d-rows"); tb.innerHTML = "";
  [...rows].reverse().forEach((r) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${r.date.slice(0, 7)}</td><td>${fmt(r.value)}</td><td></td><td><button class="ghost e">수정</button><button class="ghost x">삭제</button></td>`;
    tr.children[2].textContent = r.memo || "";
    tr.querySelector(".e").onclick = () => editRow(r);
    tr.querySelector(".x").onclick = () => delRow(r);
    tb.appendChild(tr);
  });
  drawChart();
}
function editRow(r) {
  $("#d-id").value = r.id; $("#d-date").value = r.date.slice(0, 10); $("#d-value").value = r.value; $("#d-memo").value = r.memo || "";
  $("#d-submit").textContent = "수정 저장"; $("#d-cancel").classList.remove("hidden"); $("#d-date").focus();
}
function resetForm() { $("#data-form").reset(); $("#d-id").value = ""; $("#d-submit").textContent = "추가"; $("#d-cancel").classList.add("hidden"); }
$("#d-cancel").onclick = resetForm;
async function delRow(r) {
  if (!confirm(`${r.date.slice(0, 7)} 데이터를 삭제할까요?`)) return;
  await api(`/api/data/${r.id}`, { method: "DELETE" }); flash(`${r.date.slice(0, 7)} 삭제됨`); refresh();
}
$("#data-form").onsubmit = async (e) => {
  e.preventDefault();
  const body = JSON.stringify({ date: $("#d-date").value, value: Number($("#d-value").value), memo: $("#d-memo").value });
  const id = $("#d-id").value;
  try {
    if (id) { await api(`/api/data/${id}`, { method: "PUT", body }); flash("수정 저장됨"); }
    else { await api("/api/data", { method: "POST", body }); flash("추가됨"); }
    resetForm(); refresh();
  } catch (err) { flash(`실패: ${err.message}`); }
};
function flash(t) { $("#d-msg").textContent = t; setTimeout(() => ($("#d-msg").textContent = ""), 4000); }
function refresh() { loadData(); loadSummary(); }

function drawChart() {
  const c = $("#chart"), ctx = c.getContext("2d"), dpr = window.devicePixelRatio || 1;
  const W = c.clientWidth, H = 220; c.width = W * dpr; c.height = H * dpr; ctx.scale(dpr, dpr); ctx.clearRect(0, 0, W, H);
  if (rows.length < 2) return;
  const vals = rows.map((r) => r.value), max = Math.max(...vals), pad = 36;
  const fg = getComputedStyle(document.body).getPropertyValue("--muted");
  ctx.strokeStyle = getComputedStyle(document.body).getPropertyValue("--accent"); ctx.lineWidth = 2; ctx.beginPath();
  rows.forEach((r, i) => { const x = pad + (i / (rows.length - 1)) * (W - pad * 1.5), y = H - 24 - (r.value / max) * (H - 44); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
  ctx.stroke(); ctx.fillStyle = fg; ctx.font = "12px sans-serif";
  ctx.fillText(`${fmt(max)}명`, 4, 14); ctx.fillText(rows[0].date.slice(0, 7), pad, H - 6);
  ctx.fillText(rows.at(-1).date.slice(0, 7), W - 70, H - 6); ctx.fillText("월별 방한 입국자 수 추이", W / 2 - 70, 14);
}
function setLinks() {
$("#exp-csv").href = `${API}/api/data/export?format=csv`;
$("#exp-json").href = `${API}/api/data/export?format=json`;
$("#docs-link").href = `${API}/docs`;
}

// ---- 대화 기록 ----
async function loadHistory() {
  const list = await api("/api/conversations"), ul = $("#conv-list"); ul.innerHTML = "";
  if (!list.length) ul.innerHTML = "<li class='muted'>저장된 대화가 없어요. 채팅을 하면 자동 저장돼요.</li>";
  list.forEach((c) => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="t"></span><span class="muted">${c.message_count}개 · ${(c.updated_at || "").slice(0, 16).replace("T", " ")}</span><button class="ghost o">불러오기</button><button class="ghost x">삭제</button>`;
    li.querySelector(".t").textContent = c.title;
    li.querySelector(".t").onclick = li.querySelector(".o").onclick = () => openConv(c.id);
    li.querySelector(".x").onclick = async () => { if (confirm("이 대화를 삭제할까요?")) { await api(`/api/conversations/${c.id}`, { method: "DELETE" }); loadHistory(); } };
    ul.appendChild(li);
  });
}
async function openConv(id) {
  const c = await api(`/api/conversations/${id}`);
  convId = c.id; $("#messages").innerHTML = ""; (c.messages || []).forEach((m) => addMsg(m.role, m.content));
  $("#conv-title").textContent = `불러온 대화: ${c.title}`; switchTab("chat");
}

// ---- 탭·다크 모드 ----
function switchTab(name) {
  document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
  document.querySelectorAll(".pane").forEach((p) => p.classList.toggle("hidden", p.id !== `tab-${name}`));
  if (name === "data") loadData(); if (name === "history") loadHistory();
}
document.querySelectorAll(".tab").forEach((b) => (b.onclick = () => switchTab(b.dataset.tab)));
if (localStorage.theme === "dark") document.body.classList.add("dark");
$("#theme").onclick = () => { document.body.classList.toggle("dark"); localStorage.theme = document.body.classList.contains("dark") ? "dark" : "light"; drawChart(); };

pickApi().then(setLinks).then(loadSummary).catch((e) => ($("#s-trend").textContent = `요약을 불러오지 못했어요: ${e.message} (API: ${API})`));
