// Scene player, library viewer/editor and importer.
// The player mirrors firmware/scene.cpp (same hash, effects and scroll maths)
// on the quantized layer strips the converter writes to <entry>/.build/.

const u32 = (x) => x >>> 0;
function hash(x) {
  x = u32(x ^ (x >>> 16)); x = u32(Math.imul(x, 0x7feb352d));
  x = u32(x ^ (x >>> 15)); x = u32(Math.imul(x, 0x846ca68b));
  return u32(x ^ (x >>> 16));
}
const to332 = (r, g, b) => (Math.round(r * 7 / 255) << 5) | (Math.round(g * 7 / 255) << 2) | Math.round(b * 3 / 255);
const from332 = (c) => [((c >> 5) & 7) * 255 / 7 | 0, ((c >> 2) & 7) * 255 / 7 | 0, (c & 3) * 85];
const hexRgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const FX_FRONT = { rain: 1, snow: 1 };
let THEMES = null;

class ScenePlayer {
  constructor(canvas) {
    this.c = canvas;
    this.g = canvas.getContext("2d", { willReadFrequently: true });
    this.layers = [];
    this.scene = null;
    this.t0 = performance.now();
    this.running = false;
  }
  async load(entryId, scene) {
    if (!THEMES) THEMES = await (await fetch("/api/themes")).json();
    const base = `/library/${entryId}/.build/`;
    const meta = await (await fetch(base + "layers.json?" + Date.now())).json();
    this.layers = await Promise.all(meta.map((m) => new Promise((ok) => {
      const img = new Image();
      img.onload = () => ok({ ...m, img });
      img.src = base + m.url + "?" + Date.now();
    })));
    this.scene = scene;
    this.start();
  }
  start() {
    if (this.running) return;
    this.running = true;
    const tick = () => {
      if (!this.running) return;
      this.draw(performance.now() - this.t0);
      setTimeout(() => requestAnimationFrame(tick), 30);
    };
    tick();
  }
  stop() { this.running = false; }

  draw(now) {
    const s = this.scene, g = this.g, W = 320, H = 240;
    if (!s) return;
    const bolt = s.effects.find((e) => e.type === "lightning");
    const flash = bolt && this.lightning(bolt, now);
    const top = hexRgb(s.background.top), bot = hexRgb(s.background.bottom);
    for (let y = 0; y < H; y++) {
      let c = top.map((v, k) => v + (bot[k] - v) * y / (H - 1) | 0);
      if (flash) c = c.map((v) => (v + 255) / 2 | 0);
      const q = from332(to332(...c));
      g.fillStyle = `rgb(${q})`;
      g.fillRect(0, y, W, 1);
    }
    g.imageSmoothingEnabled = false;
    for (const pass of [0, 1]) {
      s.effects.forEach((e) => {
        if ((FX_FRONT[e.type] ? 1 : 0) !== pass) return;
        if (e.type === "stars") this.stars(e, now);
        if (e.type === "rain" || e.type === "snow") this.fall(e, now, e.type === "snow");
      });
      if (pass) break;
      this.layers.forEach((L, i) => {
        const cfg = s.layers[i] || {};
        const speed = +cfg.speed || 0, period = L.w + (+cfg.gap || 0);
        let f = 0;
        if (L.frames > 1) {
          const total = L.durations.reduce((a, b) => a + b, 0);
          let t = now % total;
          while (t >= L.durations[f]) t -= L.durations[f++];
        }
        if (!speed) return g.drawImage(L.img, f * L.w, 0, L.w, L.h, (W - period) / 2 | 0, L.y, L.w, L.h);
        let off = Math.floor(now * speed / 1000) % period;
        if (off < 0) off += period;
        for (let x = -off; x < W; x += period) g.drawImage(L.img, f * L.w, 0, L.w, L.h, x, L.y, L.w, L.h);
      });
    }
    const lut = THEMES[s.theme || "original"];
    if (lut) {
      const d = g.getImageData(0, 0, W, H), p = d.data;
      for (let i = 0; i < p.length; i += 4) {
        const [r, gg, b] = from332(lut[to332(p[i], p[i + 1], p[i + 2])]);
        p[i] = r; p[i + 1] = gg; p[i + 2] = b;
      }
      g.putImageData(d, 0, 0);
    }
  }
  put(x, y, rgb) { this.g.fillStyle = rgb; this.g.fillRect(x | 0, y | 0, 1, 1); }
  stars(e, now) {
    const col = `rgb(${from332(to332(...hexRgb(e.color || "#b0a0ff")))})`;
    for (let i = 0; i < 20 * e.density; i++) {
      const h = hash(u32(i * 7919 + 1));
      const tw = hash(u32(i + Math.floor((now + h % 1100) / 1100))) % 10;
      if (tw > 2) this.put(h % 320, (h >>> 12) % 150, tw > 7 ? "#fff" : col);
    }
  }
  fall(e, now, snow) {
    const col = `rgb(${from332(to332(...hexRgb(e.color || "#9fb4ff")))})`;
    const n = (snow ? 30 : 40) * e.density;
    for (let i = 0; i < n; i++) {
      const h = hash(u32(Math.imul(i, 2654435761) + 3));
      const speed = snow ? 18 + h % 22 : 160 + h % 140;
      const y = Math.floor(now * speed / 1000 + (h >>> 8)) % 260 - 10;
      if (snow) {
        const x = h % 320 + 6 * (Math.floor(now / 700 + h) % 3) - 6;
        this.put(x, y, col);
        if (h & 1) this.put(x + 1, y, col);
      } else {
        const x = h % 360 - Math.floor(y / 4), len = 3 + h % 5;
        for (let k = 0; k < len; k++) this.put(x + Math.floor(k / 4), y - k, col);
      }
    }
  }
  lightning(e, now) {
    const period = Math.floor(14000 / e.density), t = now % period;
    const at = hash(Math.floor(now / period)) % (period - 400);
    return (t > at && t < at + 70) || (t > at + 160 && t < at + 230);
  }
}

// ------------------------------------------------------------------ viewer
const player = new ScenePlayer($("#stageCanvas"));
let viewing = null, draft = null;
const PAGE_NAMES = { console: "Console", details: "Details", companion: "Companion", image: "Images", city: "Synthwave City", scenes: "Scene playlist" };
const THEME_SWATCH = { original: "#ff3ea5", vapor: "#b04dff", toxic: "#39ff6a", dusk: "#ff7a3d", ice: "#7fd6ff",
  matrix: "#22c55e", amber: "#ffb84d", noir: "#9a9aa6", night: "#334a9a", sunset: "#ff8a5c" };

function openViewer(e) {
  viewing = e;
  $("#viewer").hidden = false;
  $("#vKind").textContent = e.kind === "page" ? `page · ${PAGE_NAMES[e.page] || e.page}` : e.kind;
  $("#vName").textContent = e.name;
  $("#vNotes").textContent = e.notes || "";
  $("#vChips").innerHTML = [e.created && e.created.slice(0, 10), e.license, e.commit].filter(Boolean)
    .map((c) => `<span class="chip"></span>`).join("");
  [...$("#vChips").children].forEach((el, i) =>
    (el.textContent = [e.created && e.created.slice(0, 10), e.license, e.commit].filter(Boolean)[i]));
  $("#vShow").hidden = !(e.kind === "scene" || e.kind === "page");
  const isScene = e.kind === "scene" && e.scene;
  $("#stageCanvas").hidden = !isScene;
  $("#stageImg").hidden = isScene;
  $("#editor").hidden = !isScene;
  player.stop();
  if (isScene) {
    draft = structuredClone(e.scene);
    player.load(e.id, draft).then(renderEditor).catch(() => toast("Preview missing. Save the scene to rebuild it.", "err"));
    renderEditor();
    $("#stageInfo").textContent = "Live preview in device colours. Scroll speeds and effects match the display.";
  } else {
    $("#stageImg").src = e.preview_url;
    $("#stageInfo").textContent = e.kind === "page" ? "Captured from the display." : "Saved capture.";
  }
}
function closeModals() {
  document.querySelectorAll(".modal").forEach((m) => (m.hidden = true));
  player.stop();
}
document.querySelectorAll("[data-close]").forEach((b) => (b.onclick = closeModals));
document.querySelectorAll(".modal").forEach((m) => m.addEventListener("mousedown", (ev) => { if (ev.target === m) closeModals(); }));
document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") closeModals(); });

function renderEditor() {
  const s = draft;
  s.variants = s.variants || [];
  const themes = $("#eThemes");
  themes.innerHTML = "";
  Object.keys(THEME_SWATCH).forEach((t) => {
    const main = (s.theme || "original") === t;
    const b = el(`<div class="theme ${main ? "on" : ""}"><span class="sw" style="background:${THEME_SWATCH[t]}"></span>${t}
      <input type="checkbox" title="Also add to playlist" ${s.variants.includes(t) ? "checked" : ""} ${main ? "disabled" : ""}></div>`);
    b.onclick = (ev) => {
      if (ev.target.tagName === "INPUT") {
        s.variants = ev.target.checked ? [...s.variants, t] : s.variants.filter((x) => x !== t);
      } else {
        s.theme = t;
        s.variants = s.variants.filter((x) => x !== t);
      }
      renderEditor();
    };
    themes.append(b);
  });
  const layers = $("#eLayers");
  layers.innerHTML = "";
  s.layers.forEach((L, i) => {
    const src = Array.isArray(L.src) ? `${L.src.length} frames` : L.src.split("/").pop();
    const row = el(`<div class="layer"><canvas width="30" height="22"></canvas>
      <div><b>${L.layer || src.replace(/\.\w+$/, "")}</b><small>${L.speed ? "scrolls" : "still, centred"}${L.gap ? ` · gap ${L.gap}px` : ""}</small></div>
      <input type="number" step="1" value="${L.speed || 0}" title="Speed in px/s"></div>`);
    row.querySelector("input").oninput = (ev) => { L.speed = +ev.target.value; };
    const strip = player.layers[i];
    if (strip) row.querySelector("canvas").getContext("2d").drawImage(strip.img, 0, 0, strip.w, strip.h, 0, 0, 30, 22);
    layers.append(row);
  });
  const fx = $("#eFx");
  fx.innerHTML = "";
  ["stars", "rain", "snow", "lightning"].forEach((type) => {
    const cur = s.effects.find((e) => e.type === type);
    const row = el(`<div class="fx"><span>${type[0].toUpperCase() + type.slice(1)}</span>
      <div class="seg">${["Off", "Light", "Medium", "Heavy"].map((l, d) =>
        `<button data-d="${d}" class="${(cur ? cur.density : 0) === d ? "on" : ""}">${l}</button>`).join("")}</div>
      ${type === "lightning" ? "<span></span>" : `<input type="color" value="${cur?.color || (type === "stars" ? "#b0a0ff" : "#9fb4ff")}">`}</div>`);
    row.querySelectorAll("button").forEach((b) => (b.onclick = () => {
      const d = +b.dataset.d;
      s.effects = s.effects.filter((e) => e.type !== type);
      if (d) s.effects.push({ type, density: d, color: row.querySelector("input")?.value });
      renderEditor();
    }));
    const color = row.querySelector("input");
    if (color) color.oninput = () => { const e = s.effects.find((x) => x.type === type); if (e) e.color = color.value; };
    fx.append(row);
  });
  $("#eTop").value = s.background.top;
  $("#eBottom").value = s.background.bottom;
}
$("#eTop").oninput = (e) => (draft.background.top = e.target.value);
$("#eBottom").oninput = (e) => (draft.background.bottom = e.target.value);
$("#eReset").onclick = () => { draft = structuredClone(viewing.scene); player.scene = draft; renderEditor(); };
$("#eSave").onclick = async () => {
  try {
    $("#eSave").disabled = true;
    await api(`/api/library/${viewing.id}/scene`, { scene: draft });
    viewing.scene = structuredClone(draft);
    toast("Scene saved. Send to display to update the device.");
    await load();
  } catch (e) { toast(e.message, "err"); }
  $("#eSave").disabled = false;
};
$("#vShow").onclick = async () => {
  const target = viewing.kind === "page" ? viewing.page : viewing.id;
  try {
    $("#vShow").disabled = true;
    const r = await api("/api/device", { commands: [`!SHOW ${target}`] });
    if ((r.replies[0] || "").startsWith("@SHOW ok")) toast(`Showing ${viewing.name} on the display. Tap it to go back.`);
    else toast("That isn't on the display yet. Send to display first.", "err");
  } catch (e) { toast(e.message, "err"); }
  $("#vShow").disabled = false;
};
$("#vDelete").onclick = async () => {
  if (!confirm(`Delete "${viewing.name}" from the library? Its imported files go too.`)) return;
  await api(`/api/library/${viewing.id}/delete`, {});
  closeModals();
  await load();
};

// ------------------------------------------------------------------ importer
let picked = [];
const readFile = (f) => new Promise((ok) => { const r = new FileReader(); r.onload = () => ok({ name: f.name, data: r.result }); r.readAsDataURL(f); });
function renderPicked() {
  $("#flist").innerHTML = "";
  picked.forEach((f, i) => {
    const li = el(`<li>${f.name} <button title="Move toward the back">↑</button><button title="Remove">×</button></li>`);
    const [up, rm] = li.querySelectorAll("button");
    up.onclick = (ev) => { ev.preventDefault(); if (i) [picked[i - 1], picked[i]] = [picked[i], picked[i - 1]]; renderPicked(); };
    rm.onclick = (ev) => { ev.preventDefault(); picked.splice(i, 1); renderPicked(); };
    $("#flist").append(li);
  });
  if (picked.length && !$("#impName").value) $("#impName").value = picked[0].name.replace(/\.\w+$/, "").replace(/[-_]+/g, " ");
}
async function addFiles(list) { picked.push(...(await Promise.all([...list].map(readFile)))); renderPicked(); }
$("#importBtn").onclick = () => { picked = []; renderPicked(); $("#impName").value = ""; $("#importer").hidden = false; };
$("#files").onchange = (e) => addFiles(e.target.files);
const drop = $("#drop");
drop.ondragover = (e) => { e.preventDefault(); drop.classList.add("over"); };
drop.ondragleave = () => drop.classList.remove("over");
drop.ondrop = (e) => { e.preventDefault(); drop.classList.remove("over"); addFiles(e.dataTransfer.files); };
$("#impGo").onclick = async () => {
  const btn = $("#impGo");
  try {
    btn.disabled = true;
    btn.textContent = "Importing…";
    const { id } = await api("/api/import", { name: $("#impName").value, license: $("#impLicense").value, files: picked });
    await load();
    closeModals();
    const e = state.library.find((x) => x.id === id);
    if (e) openViewer(e);
    toast("Imported. Tune it, save, then Send to display.");
  } catch (e) { toast(e.message, "err"); }
  btn.disabled = false;
  btn.textContent = "Create scene";
};
