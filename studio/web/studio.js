// Scene Studio front end. State lives in `profile`; every control edits it and
// marks the profile dirty. "Send to display" saves, builds and flashes.
const $ = (s) => document.querySelector(s);
const PAGES = {
  console:   { name: "Console", desc: "Quota rings for every client", thumb: "/docimg/v1.4.2-rings.png", locked: true },
  details:   { name: "Details", desc: "Full usage breakdown", thumb: "/docimg/T-008A-details.png" },
  companion: { name: "Companion", desc: "MINT, the robot face", thumb: "/docimg/MINT-happy-device.png", scene: true },
  image:     { name: "Images", desc: "Rotates your images (GIF, PNG, SVG)", thumb: "/docimg/images-page.png", scene: true },
  city:      { name: "Synthwave City", desc: "Living pixel scene", thumb: "/docimg/city.png", scene: true },
  system:    { name: "System", desc: "Task Manager style PC resources", thumb: "/docimg/system-page.png" },
  scenes:    { name: "All scenes", desc: "Rotates through every scene in the library", thumb: "/library/miami-drive/preview.png", scene: true },
};
const TIMEOUTS = [10, 20, 30, 45, 60, 120, 180, 300, 600, 900, 1800, 3600];
const TABS = {
  layout: ["Layout", "Choose which pages appear on the display and in what order."],
  saver: ["Screensaver", "What the display does when nobody is looking."],
  playlists: ["Playlists", "Build your own rotations. Each can be a tap page or the screensaver."],
  library: ["Library", "Everything worth keeping. Captures remember the profile and code version that made them."],
  device: ["Display", "See what the display shows right now, and step through its pages."],
};

let state = { profiles: {}, library: [] };
let pid = localStorage.getItem("profile") || "default";
let profile = null;
let dirty = false;

// ---------------------------------------------------------------- helpers
async function api(path, body) {
  const r = await fetch(path, body === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  const j = await r.json();
  if (!r.ok || j.error) throw new Error(j.error || r.statusText);
  return j;
}
function toast(msg, kind = "ok") {
  const t = document.createElement("div");
  t.className = `toast ${kind}`;
  t.textContent = msg;
  $("#toasts").append(t);
  setTimeout(() => t.remove(), kind === "err" ? 6000 : 3000);
}
const fmtTime = (s) => (s < 60 ? `${s} s` : s < 3600 ? `${s / 60} min` : `${s / 3600} h`);
function touch() { dirty = true; $("#dirty").classList.add("on"); render(); }
const el = (html) => { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstChild; };

// ----------------------------------------------------------------- render
function render() {
  renderPages(); renderRotation(); renderSaver(); renderPlaylists();
  document.querySelectorAll("#remaining button").forEach((b) =>
    b.classList.toggle("on", +b.dataset.v === +profile.show_remaining));
  document.querySelectorAll("#layout button").forEach((b) =>
    b.classList.toggle("on", b.dataset.v === (profile.console_layout === "grid" ? "grid" : "rows")));
}

// Built-in pages plus every library scene ("scene:<id>") can be a tap page.
function pageInfo(id) {
  if (id.startsWith("playlist:")) {
    const pl = (profile.playlists || []).find((p) => p.id === id.slice(9));
    const first = pl && pl.scenes[0] && (state.scenes || []).find((x) => x.id === pl.scenes[0]);
    return { name: pl ? pl.name : id.slice(9), desc: pl ? `Playlist · ${pl.scenes.length} scenes, ${pl.seconds}s each` : "Missing playlist",
             thumb: first ? `/library/${first.entry}/preview.png` : "", scene: true };
  }
  if (!id.startsWith("scene:")) return PAGES[id];
  const sc = (state.scenes || []).find((x) => x.id === id.slice(6));
  if (!sc) return { name: id.slice(6), desc: "Missing from the library", thumb: "", scene: true };
  return { name: sc.name, desc: `Scene${sc.theme !== "original" ? ` · ${sc.theme} theme` : ""}`,
           thumb: `/library/${sc.entry}/preview.png`, scene: true, theme: sc.theme };
}
function allPages() {
  return [...Object.keys(PAGES), ...(profile.playlists || []).map((p) => `playlist:${p.id}`),
          ...(state.scenes || []).map((x) => `scene:${x.id}`)];
}
function orderedPages() {
  const on = profile.pages;
  return [...on, ...allPages().filter((p) => !on.includes(p))];
}

function renderPages() {
  const ul = $("#pages");
  ul.innerHTML = "";
  orderedPages().forEach((id) => {
    const p = pageInfo(id), on = profile.pages.includes(id), at = profile.pages.indexOf(id);
    const li = el(`<li class="page ${on ? "" : "off"}" draggable="true" data-id="${id}">
      <span class="grip" aria-hidden="true">⋮⋮</span><span class="num">${at + 1}</span>
      <div class="thumb${p.theme && p.theme !== "original" ? " themed" : ""}" data-theme="${p.theme || ""}" role="img" aria-label="${p.name} preview" style="background-image:url('${p.thumb}')"></div>
      <div class="meta"><b>${p.name}</b><small>${p.desc}</small></div>
      ${on ? `<span class="move"><button class="icon-btn up" title="Move up" aria-label="Move ${p.name} up" ${at === 0 ? "disabled" : ""}>↑</button><button class="icon-btn down" title="Move down" aria-label="Move ${p.name} down" ${at === profile.pages.length - 1 ? "disabled" : ""}>↓</button></span>` : ""}
      ${p.locked ? '<span class="lock">Always on</span>'
                 : `<label class="switch"><input type="checkbox" aria-label="Show ${p.name} on the display" ${on ? "checked" : ""}><i></i></label>`}
    </li>`);
    // Keyboard-friendly alternative to dragging; keeps focus on the moved row.
    li.querySelectorAll(".move button").forEach((b) => (b.onclick = () => {
      const to = at + (b.classList.contains("up") ? -1 : 1), pages = profile.pages;
      [pages[at], pages[to]] = [pages[to], pages[at]];
      touch();
      $(`#pages [data-id="${id}"] .move .${b.classList.contains("up") ? "up" : "down"}`)?.focus();
    }));
    const box = li.querySelector("input");
    if (box) box.onchange = () => {
      profile.pages = box.checked ? [...profile.pages, id] : profile.pages.filter((x) => x !== id);
      const s = profile.screensaver;
      touch();
    };
    li.ondragstart = () => li.classList.add("dragging");
    li.ondragend = () => {
      li.classList.remove("dragging");
      const order = [...ul.children].map((c) => c.dataset.id);
      profile.pages = order.filter((x) => profile.pages.includes(x));
      touch();
    };
    ul.append(li);
  });
}
$("#pages").addEventListener("dragover", (e) => {
  e.preventDefault();
  const ul = $("#pages"), drag = ul.querySelector(".dragging");
  const after = [...ul.querySelectorAll(".page:not(.dragging)")].find((c) => {
    const r = c.getBoundingClientRect();
    return e.clientY < r.top + r.height / 2;
  });
  if (after) ul.insertBefore(drag, after); else ul.append(drag);
});

function renderRotation() {
  const opts = [[1, "Landscape", "land r1"], [3, "Landscape ↻", "land r3"], [0, "Portrait", "port r0"], [2, "Portrait ↻", "port r2"]];
  const box = $("#rotation");
  box.innerHTML = "";
  opts.forEach(([v, label, cls]) => {
    const b = el(`<button class="${profile.rotation === v ? "on" : ""}"><div class="dev ${cls}"></div>${label}</button>`);
    b.onclick = () => { profile.rotation = v; touch(); };
    box.append(b);
  });
}
document.querySelectorAll("#remaining button").forEach((b) =>
  (b.onclick = () => { profile.show_remaining = b.dataset.v === "1"; touch(); }));

document.querySelectorAll("#layout button").forEach((b) =>
  (b.onclick = () => { profile.console_layout = b.dataset.v; touch(); }));

function renderSaver() {
  const s = profile.screensaver;
  $("#saverOn").checked = s.enabled;
  $("#saverBody").classList.toggle("off", !s.enabled);
  const box = $("#saverPage");
  box.innerHTML = "";
  allPages().filter((id) => pageInfo(id).scene).forEach((id) => {
    const p = pageInfo(id);
    const b = el(`<button class="scene ${s.page === id ? "on" : ""}">
      <div class="img${p.theme && p.theme !== "original" ? " themed" : ""}" data-theme="${p.theme || ""}" role="img" aria-label="${p.name} preview" style="background-image:url('${p.thumb}')"></div>
      <div class="cap">${p.name}<small>${p.desc}</small></div></button>`);
    b.onclick = () => { s.page = id; touch(); };
    box.append(b);
  });
  const idx = TIMEOUTS.indexOf(s.timeout_s);
  $("#timeout").value = idx < 0 ? 2 : idx;
  $("#timeoutVal").textContent = fmtTime(s.timeout_s);
  const views = $("#views");
  views.innerHTML = "";
  ["console", "details"].forEach((v) => {
    const c = s[v];
    const row = el(`<div class="vrow"><b>${PAGES[v].name}</b>
      <div class="opts">
        <label class="check"><input type="checkbox" class="en" ${c.enabled ? "checked" : ""}> Can sleep</label>
        <label class="check"><input type="checkbox" class="wk" ${c.wake_on_usage ? "checked" : ""}> Wake on new usage</label>
      </div>
      <select>${TIMEOUTS.map((t) => `<option value="${t}" ${t === c.timeout_s ? "selected" : ""}>${fmtTime(t)}</option>`).join("")}</select></div>`);
    row.querySelector(".en").onchange = (e) => { c.enabled = e.target.checked; touch(); };
    row.querySelector(".wk").onchange = (e) => { c.wake_on_usage = e.target.checked; touch(); };
    row.querySelector("select").onchange = (e) => { c.timeout_s = +e.target.value; touch(); };
    views.append(row);
  });
}
$("#saverOn").onchange = (e) => {
  const s = profile.screensaver;
  s.enabled = e.target.checked;
  if (s.enabled && !profile.pages.includes(s.page)) s.page = profile.pages.find((x) => PAGES[x].scene) || "";
  if (s.enabled && !s.page) { s.enabled = false; toast("Turn on a scene page in Layout first", "err"); }
  touch();
};
$("#timeout").oninput = (e) => {
  const t = TIMEOUTS[+e.target.value], s = profile.screensaver;
  // Per-page timers follow the main one unless they were set separately.
  ["console", "details"].forEach((v) => { if (s[v].timeout_s === s.timeout_s) s[v].timeout_s = t; });
  s.timeout_s = t;
  touch();
};

let libFilter = "all";
function renderLibrary() {
  const box = $("#library");
  box.innerHTML = "";
  document.querySelectorAll("#libFilter button").forEach((b) => {
    const n = state.library.filter((e) => b.dataset.f === "all" || (e.kind || "capture") === b.dataset.f).length;
    b.textContent = `${b.dataset.label || (b.dataset.label = b.textContent)} (${n})`;
  });
  const items = state.library.filter((e) => libFilter === "all" || (e.kind || "capture") === libFilter);
  if (!items.length) {
    box.append(el(`<div class="empty">Nothing here yet. Import art, or capture the display and save it from the Display tab.</div>`));
    return;
  }
  items.forEach((e) => {
    const kind = e.kind === "page" ? "page" : e.kind === "scene" ? "scene" : "capture";
    const card = el(`<div class="item"><img src="${e.preview_url}?${Date.now()}" alt="">
      <button class="icon-btn gear" title="Settings"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/></svg></button>
      <div class="body"><div class="row"><b></b><span class="chip kind">${kind}</span></div>
      <p></p><div class="chips">
        <span class="chip">${(e.created || "").replace("T", " ").slice(0, 16)}</span>
        ${e.kind === "scene" && (!e.scene.cycle || (e.scene.cycle.themes || []).length > 1) ? `<span class="chip">+ theme shift</span>` : ""}
        ${e.commit ? `<span class="chip">${e.commit}</span>` : ""}</div></div></div>`);
    card.querySelector("b").textContent = e.name;
    card.querySelector("p").textContent = e.notes || "";
    card.onclick = () => openViewer(e);
    if (e.kind === "scene" && e.scene) livePreview(card, e);
    card.querySelector(".gear").onclick = (ev) => { ev.stopPropagation(); openViewer(e, true); };
    box.append(card);
  });
}
document.querySelectorAll("#libFilter button").forEach((b) => (b.onclick = () => {
  libFilter = b.dataset.f;
  document.querySelectorAll("#libFilter button").forEach((x) => x.classList.toggle("on", x === b));
  renderLibrary();
}));

// ------------------------------------------------------------- profiles
function renderProfiles() {
  const sel = $("#profile");
  sel.innerHTML = Object.entries(state.profiles)
    .map(([id, p]) => `<option value="${id}" ${id === pid ? "selected" : ""}>${p.name || id}</option>`).join("");
}
$("#profile").onchange = (e) => {
  if (dirty && !confirm("Discard unsaved changes?")) { e.target.value = pid; return; }
  selectProfile(e.target.value);
};
function selectProfile(id) {
  pid = state.profiles[id] ? id : Object.keys(state.profiles)[0];
  localStorage.setItem("profile", pid);
  profile = structuredClone(state.profiles[pid]);
  dirty = false;
  $("#dirty").classList.remove("on");
  render();
}
async function saveProfile() {
  await api(`/api/profiles/${pid}`, profile);
  state.profiles[pid] = structuredClone(profile);
  dirty = false;
  $("#dirty").classList.remove("on");
}
$("#save").onclick = async () => {
  try { await saveProfile(); toast("Profile saved"); } catch (e) { toast(e.message, "err"); }
};
$("#newProfile").onclick = async () => {
  const name = prompt("Name for the new profile", `${profile.name} copy`);
  if (!name) return;
  const id = name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 40);
  if (!id || state.profiles[id]) return toast("Pick a different name", "err");
  const copy = { ...structuredClone(profile), name };
  try {
    await api(`/api/profiles/${id}`, copy);
    state.profiles[id] = copy;
    renderProfiles();
    selectProfile(id);
    renderProfiles();
    toast(`Created "${name}"`);
  } catch (e) { toast(e.message, "err"); }
};

// ------------------------------------------------------- send to display
const STEPS = ["Converting art", "Building firmware", "Flashing display"];
function drawSteps(job) {
  const cur = STEPS.indexOf(job.step);
  $("#steps").innerHTML = STEPS.map((s, i) => {
    let c = i < cur ? "ok" : i === cur ? (job.state === "running" ? "run" : job.state === "done" ? "ok" : "fail") : "";
    return `<span class="step ${c}"><i>${c === "ok" ? "✓" : c === "fail" ? "!" : ""}</i>${s}</span>`;
  }).join("") + (job.size ? `<span class="chip">${(job.size.bytes / 1024).toFixed(0)} KB · ${job.size.percent}% of flash</span>` : "");
  const log = $("#log");
  const atEnd = log.scrollTop + log.clientHeight >= log.scrollHeight - 8;
  log.textContent = job.log;
  if (atEnd) log.scrollTop = log.scrollHeight;
}
$("#send").onclick = async () => {
  const btn = $("#send");
  try {
    await saveProfile();
    btn.disabled = true;
    $("#drawer").classList.add("on");
    const { job } = await api("/api/flash", { profile: pid });
    for (;;) {
      await new Promise((r) => setTimeout(r, 700));
      const j = await api(`/api/jobs/${job}`);
      drawSteps(j);
      if (j.state !== "running") {
        if (j.state === "done") toast("The display is running your profile");
        else { toast(`${j.step} failed. Open the log for details.`, "err"); $("#log").hidden = false; }
        break;
      }
    }
  } catch (e) { toast(e.message, "err"); }
  btn.disabled = false;
};
$("#toggleLog").onclick = () => {
  const log = $("#log");
  log.hidden = !log.hidden;
  $("#toggleLog").textContent = log.hidden ? "Show log" : "Hide log";
};
$("#closeDrawer").onclick = () => $("#drawer").classList.remove("on");

// ------------------------------------------------------------- device
let busy = false, liveTimer = null;
async function capture(commands = []) {
  if (busy) return;
  busy = true;
  $("#screen").classList.add("loading");
  try {
    const r = await api("/api/device", { commands: [...commands, "!PERF"], shot: true });
    $("#screen").innerHTML = `<img src="${r.shot}" alt="Display">`;
    const perf = r.replies.find((x) => x.startsWith("@PERF"));
    if (perf) {
      const us = +perf.match(/render_us=(\d+)/)[1], heap = +perf.match(/heap=(\d+)/)[1];
      $("#statFrame").textContent = `${(us / 1000).toFixed(0)} ms`;
      $("#statFps").textContent = `${Math.min(1e6 / us, 60).toFixed(0)} fps`;
      $("#statHeap").textContent = `${(heap / 1024).toFixed(0)} KB`;
    }
  } catch (e) {
    toast(e.message, "err");
    $("#live").checked = false;
    clearInterval(liveTimer);
  }
  $("#screen").classList.remove("loading");
  busy = false;
}
$("#capture").onclick = () => capture();
$("#nextPage").onclick = () => capture(["!NEXT"]);
$("#live").onchange = (e) => {
  clearInterval(liveTimer);
  if (e.target.checked) { capture(); liveTimer = setInterval(() => capture(), 4000); }
};
$("#saveLib").onclick = async () => {
  try {
    await api("/api/library", { name: $("#libName").value, notes: $("#libNotes").value, profile: pid });
    $("#libName").value = $("#libNotes").value = "";
    toast("Saved to the library");
    await load();
  } catch (e) { toast(e.message, "err"); }
};

// ---------------------------------------------------------------- tabs
document.querySelectorAll(".nav").forEach((b) => (b.onclick = () => {
  document.querySelectorAll(".nav").forEach((x) => x.classList.toggle("on", x === b));
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("on", t.id === `tab-${b.dataset.tab}`));
  [$("#title").textContent, $("#subtitle").textContent] = TABS[b.dataset.tab];
  // The Display tab is empty until a capture; take the first one on arrival.
  if (b.dataset.tab === "device" && !$("#screen img")) capture();
}));
window.onbeforeunload = () => (dirty ? true : undefined);

async function load() {
  state = await api("/api/state");
  $("#commit").textContent = state.commit ? `build ${state.commit}` : "";
  renderProfiles();
  if (!profile) selectProfile(pid);
  renderLibrary();
}
load().catch((e) => toast(e.message, "err"));
