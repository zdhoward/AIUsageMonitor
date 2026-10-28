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

const IDENTITY = [...Array(256)].map((_, i) => i);
let themesLoading = null;
function loadThemes(force = false) {
  if (force || !themesLoading) {
    themesLoading = (async () => {
      const [luts, info] = await Promise.all([fetch("/api/themes").then((r) => r.json()),
                                              fetch("/api/theme-info").then((r) => r.json())]);
      THEMES = luts;
      window.THEME_INFO = info;
    })();
    themesLoading.catch(() => { themesLoading = null; });  // allow a retry after a failed load
  }
  return themesLoading;
}
function cycleLut(s, now) {
  const c = s.cycle;
  const list = c && (c.themes || []).filter((t) => t in THEMES);
  if (!list || list.length < 2) return null;
  const hold = Math.max(1, +c.hold || 20) * 1000, fade = Math.max(0, +c.fade || 0) * 1000, period = hold + fade;
  const t = now % (period * list.length), k = Math.floor(t / period), u = t % period;
  const a = THEMES[list[k]] || IDENTITY;
  if (u < hold || !fade) return a;
  const b = THEMES[list[(k + 1) % list.length]] || IDENTITY, f = Math.floor((u - hold) * 256 / fade);
  return a.map((x, i) => {
    const y = b[i];
    const r = (x >> 5) * (256 - f) + (y >> 5) * f, g = ((x >> 2) & 7) * (256 - f) + ((y >> 2) & 7) * f;
    const bl = (x & 3) * (256 - f) + (y & 3) * f;
    return (((r + 128) >> 8) << 5) | (((g + 128) >> 8) << 2) | ((bl + 128) >> 8);
  });
}

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
    await loadThemes();
    this.entry = entryId;
    // Scenes in the native engine stream the firmware's own pixels; edits travel as tune blobs.
    this.native = (state.native || []).includes(entryId);
    const base = `/library/${entryId}/.build/`;
    const meta = await (await fetch(base + "layers.json?" + Date.now())).json();
    this.layers = await Promise.all(meta.map((m) => new Promise((ok) => {
      const img = new Image();
      img.onload = () => ok({ ...m, img });
      img.src = base + m.url + "?" + Date.now();
    })));
    this.gen = await (await fetch(base + "gen.json?" + Date.now())).json().catch(() => null);
    this.warpStars = null;
    this.scene = scene;
    this.savedFit = scene.layers.map((L) => L.fit || "original");  // what the strips were built with
    this.start();
  }
  start() {
    if (this.running) return;
    this.running = true;
    const tick = async () => {
      if (!this.running) return;
      const t = performance.now() - this.t0;
      if (this.native) await this.drawNative(t).catch(() => { this.native = false; });
      else this.draw(t);
      setTimeout(tick, this.native ? 15 : 30);
    };
    tick();
  }
  // One frame from the native engine (RGB332), with unsaved edits applied.
  async drawNative(t, warm = 0) {
    const r = await fetch("/api/frame", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ entry: this.entry, t: Math.floor(t), scene: this.scene, warm, shift: !!this.shift }) });
    if (!r.ok) throw new Error("no native frame");
    this.tuneStatus = r.headers.get("X-Tune");
    const px = new Uint8Array(await r.arrayBuffer());
    const img = this.g.createImageData(320, 240), d = img.data;
    for (let i = 0; i < px.length; i++) {
      const c = px[i], o = i * 4;
      d[o] = ((c >> 5) & 7) * 255 / 7; d[o + 1] = ((c >> 2) & 7) * 255 / 7; d[o + 2] = (c & 3) * 85; d[o + 3] = 255;
    }
    this.g.putImageData(img, 0, 0);
  }
  stop() { this.running = false; }

  draw(now) {
    const s = this.scene, g = this.g, W = 320, H = 240;
    if (!s) return;
    const bolt = s.effects.find((e) => e.type === "lightning");
    const flash = bolt && this.lightning(bolt, now);
    const top = hexRgb(s.background.top), bot = hexRgb(s.background.bottom);
    if (s.generator) this.genDraw(now);
    else for (let y = 0; y < H; y++) {
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
        const fixed = +cfg.frame_ms || (Array.isArray(cfg.src) && +cfg.ms);
        if (L.frames > 1 && fixed) f = Math.floor(now / fixed) % L.frames;
        else if (L.frames > 1) {
          const total = L.durations.reduce((a, b) => a + b, 0);
          let t = now % total;
          while (t >= L.durations[f]) t -= L.durations[f++];
        }
        if (!speed) {
          // Mock an unsaved fit change by scaling the built strip; Save bakes exact pixels.
          const fit = cfg.fit || "original";
          if (fit === this.savedFit[i]) return g.drawImage(L.img, f * L.w, 0, L.w, L.h, (W - period) / 2 | 0, L.y, L.w, L.h);
          const k = { pixel: Math.max(1, Math.floor(Math.min(W / L.w, H / L.h))), contain: Math.min(W / L.w, H / L.h),
                      cover: Math.max(W / L.w, H / L.h), original: 1 }[fit];
          const dw = fit === "stretch" ? W : Math.round(L.w * k), dh = fit === "stretch" ? H : Math.round(L.h * k);
          return g.drawImage(L.img, f * L.w, 0, L.w, L.h, (W - dw) / 2 | 0, (H - dh) / 2 | 0, dw, dh);
        }
        let off = Math.floor(now * speed / 1000) % period;
        if (off < 0) off += period;
        for (let x = -off; x < W; x += period) g.drawImage(L.img, f * L.w, 0, L.w, L.h, x, L.y, L.w, L.h);
      });
    }
    const lut = (this.shift && cycleLut({ ...s, cycle: { hold: 20, fade: 4, ...s.cycle, themes: shiftList(s) } }, now)) || THEMES[s.theme || "original"];
    if (lut) {
      const d = g.getImageData(0, 0, W, H), p = d.data;
      for (let i = 0; i < p.length; i += 4) {
        const [r, gg, b] = from332(lut[to332(p[i], p[i + 1], p[i + 2])]);
        p[i] = r; p[i + 1] = gg; p[i + 2] = b;
      }
      g.putImageData(d, 0, 0);
    }
  }
  // Ports of the firmware generators (scene.cpp), drawn straight into pixels.
  genDraw(now) {
    const G = this.scene.generator, W = 320, H = 240;
    const img = this.g.createImageData(W, H), p = img.data;
    const cols = (G.colors || ["#000000", "#ffffff"]).map((h) => to332(...hexRgb(h)));
    const rgb = cols.map(from332);
    const set = (x, y, c) => {
      if (x < 0 || y < 0 || x >= W || y >= H) return;
      const i = (y * W + x) * 4, v = from332(c);
      p[i] = v[0]; p[i + 1] = v[1]; p[i + 2] = v[2]; p[i + 3] = 255;
    };
    if (G.type === "patterns" && this.gen && this.gen.tiles.length) {
      const tiles = this.gen.tiles, tc = tiles.length / 32;
      const hold = (+G.seconds || 7) * 1000, step = Math.floor(now / hold), into = now % hold;
      const pairs = Math.max(1, cols.length >> 1);
      const cur = step % tc, prev = (step + tc - 1) % tc;
      const pc = (step % pairs) * 2, pp = ((step + pairs - 1) % pairs) * 2;
      const edge = into < 900 && step ? (W + H) * into / 900 | 0 : 1 << 30;
      const sc = +G.scale || 3, ox = Math.trunc(now * (+G.vx || 0) / 1000), oy = Math.trunc(now * (+G.vy || 0) / 1000);
      const bit = (t, x, y) => (tiles[t * 32 + (y & 15) * 2 + ((x & 15) >> 3)] >> (7 - (x & 7))) & 1;
      for (let y = 0; y < H; y++) {
        const ty = Math.trunc((y + oy) / sc) & 15;
        for (let x = 0; x < W; x++) {
          const tx = Math.trunc((x + ox) / sc) & 15;
          const c = x + y < edge ? rgb[pc + bit(cur, tx, ty)] : rgb[pp + bit(prev, tx, ty)];
          const i = (y * W + x) * 4;
          p[i] = c[0]; p[i + 1] = c[1]; p[i + 2] = c[2]; p[i + 3] = 255;
        }
      }
    } else if (G.type === "matrix") {
      this.matrix(G, cols, now, set, p);
    } else if (G.type === "plasma" || G.type === "warp") {
      const sin8 = [...Array(256)].map((_, i) => 128 + 127 * Math.sin(i * 6.2831853 / 256) | 0);
      const n = Math.max(2, cols.length);
      const ramp = [...Array(256)].map((_, i) => {
        const seg = Math.floor(i * n / 256), a = cols[seg % cols.length], b = cols[((seg + 1) % n) % cols.length];
        const u = (i * n) % 256;
        const ch = (sh, bits) => { const m = (1 << bits) - 1, va = (a >> sh) & m, vb = (b >> sh) & m; return (va + Math.trunc(((vb - va) * u + 128) / 256)) & m; };
        return (ch(5, 3) << 5) | (ch(2, 3) << 2) | ch(0, 2);
      });
      if (G.type === "plasma") {
        const bs = +G.scale || 2, t1 = (now / 23 | 0) & 255, t2 = (now / 37 | 0) & 255, t3 = (now / 61 | 0) & 255;
        for (let y = 0; y < H; y += bs)
          for (let x = 0; x < W; x += bs) {
            const v = (sin8[(x + t1) & 255] >> 2) + (sin8[(y * 2 - t2) & 255] >> 2) + (sin8[(x + y + t3) & 255] >> 2) +
                      (sin8[((sin8[((x >> 1) + t2) & 255] >> 1) + y - t1) & 255] >> 2);
            const c = ramp[(v + (now / 40 | 0)) & 255];
            for (let yy = y; yy < y + bs; yy++) for (let xx = x; xx < x + bs; xx++) set(xx, yy, c);
          }
      } else {
        for (let i = 0; i < W * H; i++) { p[i * 4] = rgb[0][0]; p[i * 4 + 1] = rgb[0][1]; p[i * 4 + 2] = rgb[0][2]; p[i * 4 + 3] = 255; }
        if (!this.warpStars) this.warpStars = [...Array(150)].map((_, i) => {
          const h = hash(u32(i * 977 + 5));
          return { x: h % 2000 - 1000, y: (h >>> 11) % 1500 - 750, z: 1 + (h >>> 22) % 1000 };
        });
        const dt = Math.min(200, now - (this.last || now)) || 40;
        this.last = now;
        const speed = Math.trunc((+G.speed || 300) * dt / 1000);
        this.warpStars.forEach((st, i) => {
          const pz = st.z;
          st.z = st.z > speed + 1 ? st.z - speed : 0;
          if (!st.z) { const h = hash(u32(i + now)); Object.assign(st, { x: h % 2000 - 1000, y: (h >>> 11) % 1500 - 750, z: 1000 }); return; }
          const x = 160 + Math.trunc(st.x * 128 / st.z), y = 120 + Math.trunc(st.y * 128 / st.z);
          const px = 160 + Math.trunc(st.x * 128 / pz), py = 120 + Math.trunc(st.y * 128 / pz);
          const c = ramp[255 - (st.z >> 2)], steps = Math.max(Math.abs(x - px), Math.abs(y - py)) || 1;
          for (let k = 0; k <= steps; k++) set(px + Math.trunc((x - px) * k / steps), py + Math.trunc((y - py) * k / steps), c);
        });
      }
    }
    this.g.putImageData(img, 0, 0);
  }
  // Digital rain, mirroring drawMatrix() in scene.cpp.
  matrix(G, cols, now, set, p) {
    const W = 320, H = 240, sc = +G.scale || 1, cw = 6 * sc, ch = 8 * sc;
    const ncol = Math.min(64, Math.floor(W / cw)), nrow = Math.min(40, Math.floor(H / ch));
    const ramp = this.rampFor(cols);
    const key = `${sc}|${G.speed}|${G.density}`;
    const respawn = (d, seed) => {
      const h = hash(u32(seed)), base = +G.speed || 12;
      d.speed = (base >> 1) + h % (base + 1);
      d.len = 6 + (h >>> 8) % Math.floor(nrow * 2 / 3);
      const active = (h >>> 16) % 100 < (+G.density || 70);
      d.head16 = -((h >>> 20) % (active ? nrow : nrow * 4)) * 16;
    };
    if (this.mxKey !== key) {
      this.mxGlyph = [...Array(64)].map((_, k) => [...Array(7)].map((_, r) => {
        const h = hash(u32(k * 131 + r * 7 + 9));
        let row = h & 0x1f;
        if (r === 0 || (h >>> 5) % 4 === 0) row = (h >>> 8) % 2 ? 0x1f : row | 0x11;
        return row;
      }));
      this.mxCell = [...Array(64 * 40)].map((_, i) => hash(u32(i + 77)) & 63);
      this.mxDrop = [...Array(64)].map((_, x) => { const d = {}; respawn(d, x * 911 + 1); return d; });
      this.mxKey = key;
      this.mxLast = now;
    }
    const dt = now - this.mxLast > 200 || now < this.mxLast ? 40 : now - this.mxLast;
    this.mxLast = now;
    const bg = from332(cols[0]);
    for (let i = 0; i < W * H; i++) { p[i * 4] = bg[0]; p[i * 4 + 1] = bg[1]; p[i * 4 + 2] = bg[2]; p[i * 4 + 3] = 255; }
    for (let n = Math.floor(ncol * nrow / 30); n > 0; n--) {
      const h = hash(u32(Math.imul(now, 31) + n));
      this.mxCell[h % (64 * 40)] = (h >>> 16) & 63;
    }
    const head = cols[cols.length - 1];
    for (let x = 0; x < ncol; x++) {
      const d = this.mxDrop[x];
      d.head16 += Math.trunc(d.speed * dt * 16 / 1000);
      const hr = Math.trunc(d.head16 / 16);
      if (hr - d.len > nrow) { respawn(d, now + x * 7919); continue; }
      for (let k = 0; k <= d.len; k++) {
        const r = hr - k;
        if (r < 0 || r >= nrow) continue;
        const c = k === 0 ? head : ramp[200 - Math.trunc(190 * k / (d.len + 1))];
        const gl = this.mxGlyph[this.mxCell[x * 40 + r]];
        for (let gy = 0; gy < 7; gy++)
          for (let gx = 0; gx < 5; gx++)
            if ((gl[gy] >> (4 - gx)) & 1)
              for (let yy = 0; yy < sc; yy++) for (let xx = 0; xx < sc; xx++) set(x * cw + gx * sc + xx, r * ch + gy * sc + yy, c);
      }
    }
  }
  rampFor(cols) {
    const n = Math.max(2, cols.length);
    return [...Array(256)].map((_, i) => {
      const seg = Math.floor(i * n / 256), a = cols[seg % cols.length], b = cols[((seg + 1) % n) % cols.length];
      const u = (i * n) % 256;
      const ch = (sh, bits) => { const m = (1 << bits) - 1, va = (a >> sh) & m, vb = (b >> sh) & m; return (va + Math.trunc(((vb - va) * u + 128) / 256)) & m; };
      return (ch(5, 3) << 5) | (ch(2, 3) << 2) | ch(0, 2);
    });
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

// ------------------------------------------------------------------ library cards
// Scene cards play on hover (one player at a time keeps the page light), and
// scenes without a thumbnail get one rendered by the same player.
let hoverPlayer = null;
function livePreview(card, e) {
  const img = card.querySelector("img");
  card.addEventListener("mouseenter", () => {
    const cv = document.createElement("canvas");
    cv.width = 320; cv.height = 240;
    cv.className = "live";
    img.after(cv);
    hoverPlayer?.stop();
    hoverPlayer = new ScenePlayer(cv);
    hoverPlayer.load(e.id, e.scene).catch(() => cv.remove());
  });
  card.addEventListener("mouseleave", () => {
    hoverPlayer?.stop();
    card.querySelectorAll("canvas.live").forEach((c) => c.remove());
  });
  if (!e.has_preview) renderThumb(e, img);
}
const thumbQueue = [];
function renderThumb(e, img) {
  thumbQueue.push(async () => {
    const cv = document.createElement("canvas");
    cv.width = 320; cv.height = 240;
    const p = new ScenePlayer(cv);
    await p.load(e.id, e.scene);
    p.stop();
    if (p.native) await p.drawNative(4000, 100);  // warm-up frames let stateful effects settle
    else for (let t = 0; t <= 4000; t += 40) p.draw(t);
    const data = cv.toDataURL("image/png");
    img.src = data;
    await api(`/api/library/${e.id}/preview`, { data });
    e.has_preview = true;
  });
  if (thumbQueue.length === 1) drainThumbs();
}
async function drainThumbs() {
  while (thumbQueue.length) {
    try { await thumbQueue[0](); } catch (err) { console.warn("thumbnail", err); }
    thumbQueue.shift();
  }
}

loadThemes().catch(() => {});

// ------------------------------------------------------------------ viewer
const player = new ScenePlayer($("#stageCanvas"));
let viewing = null, draft = null;
const PAGE_NAMES = { console: "Console", details: "Details", companion: "Companion", image: "Images", city: "Synthwave City", scenes: "Scene playlist", system: "System" };

function openViewer(e, settings = false) {
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
  $("#vLiveRow").hidden = !isScene;
  setLive(false);
  $("#stageCanvas").hidden = !isScene;
  $("#stageImg").hidden = isScene;
  $("#editor").hidden = !isScene;
  const ringPage = e.kind === "page" && (e.page === "console" || e.page === "details");
  $("#pageSettings").hidden = !ringPage;
  if (ringPage) renderRings();
  if (settings) setTimeout(() => $(ringPage ? "#pageSettings" : "#editor").scrollIntoView({ behavior: "smooth" }), 80);
  player.stop();
  if (isScene) {
    draft = structuredClone(e.scene);
    player.shift = false;
    player.load(e.id, draft).then(renderEditor).catch(() => toast("Preview missing. Save the scene to rebuild it.", "err"));
    renderEditor();
    $("#stageInfo").textContent = "Live preview in the display's colours. Scroll speeds and effects match it.";
  } else {
    $("#stageImg").src = e.preview_url;
    $("#stageInfo").textContent = e.kind === "page" ? "Captured from the display." : "Saved capture.";
  }
}
function closeModals() {
  document.querySelectorAll(".modal").forEach((m) => (m.hidden = true));
  player.stop();
  setLive(false);
}

// Live on device: while on, every edit is sent to the display as a tune blob.
let liveOn = false, liveEditTimer = null, liveSent = "";
function setLive(on) {
  if (liveOn && !on) api("/api/live", { off: true }).catch(() => {});
  liveOn = on;
  const sw = $("#vLive");
  if (sw) sw.checked = on;
  clearInterval(liveEditTimer);
  liveSent = "";
  if (on) liveEditTimer = setInterval(pushLive, 400);
}
async function pushLive() {
  if (!liveOn || !viewing || !draft) return;
  const body = JSON.stringify({ entry: viewing.id, scene: draft, shift: !!player.shift });
  if (body === liveSent) return;
  liveSent = body;
  try {
    const r = await api("/api/live", JSON.parse(body));
    $("#vLiveNote").textContent = r.last && r.last.startsWith("@ERR") ? r.last.slice(5) : "Edits show on the display as you make them.";
  } catch (e) { $("#vLiveNote").textContent = e.message; }
}
document.querySelectorAll("[data-close]").forEach((b) => (b.onclick = closeModals));
document.querySelectorAll(".modal").forEach((m) => m.addEventListener("mousedown", (ev) => { if (ev.target === m) closeModals(); }));
document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") closeModals(); });

function renderEditor() {
  const s = draft;
  delete s.variants;  // retired: theme shift replaces per-theme copies
  renderThemes();
  const layers = $("#eLayers");
  $("#eLayersWrap").hidden = !s.layers.length;
  layers.innerHTML = "";
  s.layers.forEach((L, i) => {
    const strip = player.layers[i];
    const multi = Array.isArray(L.src) || (strip && strip.frames > 1);
    const src = Array.isArray(L.src) ? `${L.src.length} frames` : L.src.split("/").pop();
    const still = !+L.speed;
    const msKey = Array.isArray(L.src) ? "ms" : "frame_ms";
    const row = el(`<div class="layer"><canvas width="30" height="22"></canvas>
      <div><b>${L.layer || src.replace(/\.\w+$/, "")}</b><small>${still ? "still, centred" : "scrolls, wraps forever"}</small></div>
      <div class="knobs">
        <label>Speed<input type="number" data-k="speed" value="${L.speed || 0}"></label>
        ${multi ? `<label>Frame ms<input type="number" data-k="${msKey}" value="${L[msKey] || ""}" placeholder="auto"></label>` : ""}
        ${still ? `<label>Fit<select data-k="fit">${["original", "pixel", "contain", "cover", "stretch"].map((f) =>
          `<option ${(L.fit || "original") === f ? "selected" : ""}>${f}</option>`).join("")}</select></label>`
               : `<label>Gap<input type="number" data-k="gap" value="${L.gap || 0}"></label>`}
      </div></div>`);
    row.querySelectorAll("[data-k]").forEach((inp) => (inp.onchange = inp.oninput = () => {
      const k = inp.dataset.k;
      if (k === "fit") {
        if (inp.value === "original") delete L.fit; else L.fit = inp.value;
        $("#eNote").textContent = "The preview shows the new fit now; Save scene bakes it into the art.";
      } else if (inp.value === "") delete L[k];
      else L[k] = +inp.value;
      if (k === "speed" && !!+inp.value === still) renderEditor();
    }));
    if (strip) row.querySelector("canvas").getContext("2d").drawImage(strip.img, 0, 0, strip.w, strip.h, 0, 0, 30, 22);
    layers.append(row);
  });
  renderGen();
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
  const hasGen = Boolean(s.generator);
  const skyWrap = $("#eSkyWrap");
  if (skyWrap) skyWrap.hidden = hasGen;
  if (!hasGen && s.background) {
    $("#eTop").value = s.background.top || "#000000";
    $("#eBottom").value = s.background.bottom || "#000000";
  }
}
$("#eTop").oninput = (e) => (draft.background.top = e.target.value);
$("#eBottom").oninput = (e) => (draft.background.bottom = e.target.value);
$("#eReset").onclick = () => { draft = structuredClone(viewing.scene); player.scene = draft; renderEditor(); };
$("#eSave").onclick = async () => {
  try {
    $("#eSave").disabled = true;
    await api(`/api/library/${viewing.id}/scene`, { scene: draft });
    viewing.scene = structuredClone(draft);
    toast("Scene saved. Send to display to update it.");
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

// Themes: every scene plays as its original (the picked theme) and as a theme
// shift that cross-fades through the ticked themes (all by default).
function shiftList(s) {
  return s.cycle ? s.cycle.themes || [] : window.THEME_INFO.map((t) => t.id);
}
function renderThemes() {
  const s = draft;
  const box = $("#eThemes");
  if (!(window.THEME_INFO || []).length) {  // themes still loading (or failed): load, then draw
    box.innerHTML = `<div class="tl-empty">Loading themes…</div>`;
    loadThemes(true).then(() => draft === s && renderThemes()).catch(() => (box.innerHTML = `<div class="tl-empty">Couldn't load themes. Is the Studio server running?</div>`));
    return;
  }
  const extras = shiftList(s);
  const setExtras = (next) => { s.cycle = { hold: 20, fade: 4, ...s.cycle, themes: next }; };
  const filter = (box.querySelector(".tl-filter") || {}).value || "";
  box.innerHTML = `<div class="tl-head"><input class="tl-filter" placeholder="Filter ${window.THEME_INFO.length} themes…"><span>In theme shift</span></div><div class="tl-rows"></div>`;
  const f = box.querySelector(".tl-filter");
  f.value = filter;
  f.oninput = () => { renderThemes(); const nf = $("#eThemes .tl-filter"); nf.focus(); nf.setSelectionRange(nf.value.length, nf.value.length); };
  const rows = box.querySelector(".tl-rows");
  const info = window.THEME_INFO;
  const main = s.theme || "original";
  // ticked themes in shift order, then everything else
  const order = [...extras, ...info.map((t) => t.id).filter((id) => !extras.includes(id))];
  order.map((id) => info.find((t) => t.id === id)).filter(Boolean)
    .filter((t) => !filter || (t.name + " " + (t.author || "")).toLowerCase().includes(filter.toLowerCase()))
    .forEach((t) => {
      const isMain = t.id === main, extra = extras.includes(t.id), k = extras.indexOf(t.id);
      const row = el(`<div class="tl-row ${isMain ? "main" : ""} ${extra ? "extra" : ""}" title="Click to use this theme for the original">
        <span class="tl-check">${isMain ? "✓" : ""}</span>
        <span class="sw-strip wide">${t.colors.map((c) => `<i style="background:${c}"></i>`).join("")}</span>
        <div class="tl-name"><b></b><small></small></div>
        <span class="tl-move">${extra && extras.length > 1 ? `<button class="mini-btn" data-d="-1" title="Earlier">↑</button><button class="mini-btn" data-d="1" title="Later">↓</button>` : ""}</span>
        ${t.kind === "palette" ? '<button class="mini-btn del" title="Remove palette">×</button>' : "<span></span>"}
        <label class="tl-also" title="Fade to this theme in the theme shift">
          <input type="checkbox" ${extra ? "checked" : ""}></label>
      </div>`);
      row.querySelector("b").textContent = t.name + (isMain ? "  (original)" : "");
      row.querySelector("small").textContent = t.kind === "palette" ? `Lospec · ${t.author || "unknown"} · ${t.colors.length} colours` : "Built in";
      row.onclick = (ev) => {
        if (ev.target.closest("button, label")) return;
        s.theme = t.id;
        setPreview(false);
      };
      row.querySelector(".tl-also input").onchange = (e) => {
        setExtras(e.target.checked ? [...extras, t.id] : extras.filter((x) => x !== t.id));
        setPreview(true);
      };
      row.querySelectorAll("[data-d]").forEach((btn) => (btn.onclick = () => {
        const next = [...extras], j = k + +btn.dataset.d;
        if (j < 0 || j >= next.length) return;
        [next[k], next[j]] = [next[j], next[k]];
        setExtras(next);
        setPreview(true);
      }));
      const del = row.querySelector(".del");
      if (del) del.onclick = async () => {
        if (!confirm(`Remove the ${t.name} palette? Scenes using it fall back to original colours.`)) return;
        await api(`/api/themes/${t.id}/delete`, {});
        if (s.theme === t.id) s.theme = "original";
        if (s.cycle) setExtras(extras.filter((x) => x !== t.id));
        await loadThemes(true);
        renderThemes();
      };
      rows.append(row);
    });
  const shift = player.shift, n = extras.length;
  const mode = $("#eThemeMode");
  mode.innerHTML = `<div class="seg"><button data-m="0" class="${shift ? "" : "on"}">Preview original</button>
    <button data-m="1" class="${shift ? "on" : ""}" ${n > 1 ? "" : "disabled"}>Preview theme shift</button></div>
    <span class="cyc">Hold <input type="number" min="1" class="c-hold"> s · Fade <input type="number" min="0" step="0.5" class="c-fade"> s</span>
    <button class="btn ghost" data-all="1">Tick all</button><button class="btn ghost" data-all="0">Untick all</button>
    <button class="btn ghost" id="lospecBtn">Browse Lospec palettes</button>`;
  mode.querySelectorAll("[data-m]").forEach((b) => (b.onclick = () => setPreview(b.dataset.m === "1")));
  mode.querySelectorAll("[data-all]").forEach((b) => (b.onclick = () => {
    setExtras(b.dataset.all === "1" ? info.map((t) => t.id) : []);
    setPreview(b.dataset.all === "1");
  }));
  const hold = mode.querySelector(".c-hold"), fade = mode.querySelector(".c-fade");
  hold.value = s.cycle?.hold ?? 20;
  fade.value = s.cycle?.fade ?? 4;
  hold.oninput = () => { setExtras(extras); s.cycle.hold = Math.max(1, +hold.value || 1); };
  fade.oninput = () => { setExtras(extras); s.cycle.fade = Math.max(0, +fade.value || 0); };
  $("#eThemeHint").textContent = n > 1
    ? `Plays twice: the original in ${main}, then a theme shift through ${n} themes, holding each ${s.cycle?.hold ?? 20}s and cross-fading for ${s.cycle?.fade ?? 4}s.`
    : "Tick two or more themes to add a theme shift. With fewer, only the original plays.";
  $("#lospecBtn").onclick = openLospec;
}
// Which playlist entry the preview (and live display) shows: the original or its theme shift.
function setPreview(shift) {
  player.shift = shift && shiftList(draft).length > 1;
  liveSent = "";
  renderThemes();
}

// Lospec browser: search palettes by tag, or paste a palette link.
async function openLospec() {
  $("#lospec").hidden = false;
  if (!$("#lsGrid").children.length) searchLospec();
}
async function searchLospec(page = 0) {
  const grid = $("#lsGrid");
  grid.innerHTML = `<div class="hint">Searching Lospec…</div>`;
  try {
    const tag = $("#lsTag").value || "cyberpunk";
    const list = await api(`/api/lospec?tag=${encodeURIComponent(tag)}&page=${page}`);
    grid.innerHTML = "";
    if (!list.length) grid.innerHTML = `<div class="hint">No palettes tagged "${tag}".</div>`;
    const have = new Set((window.THEME_INFO || []).map((t) => t.id));
    list.forEach((p) => {
      const card = el(`<div class="ls-card"><div class="ls-strip">${p.colors.map((c) => `<i style="background:#${c}"></i>`).join("")}</div>
        <div class="ls-meta"><b></b><small></small></div><button class="btn ${have.has(p.slug) ? "ghost" : "primary"}">${have.has(p.slug) ? "Added" : "Add"}</button></div>`);
      card.querySelector("b").textContent = p.title;
      card.querySelector("small").textContent = `${p.colors.length} colours · ${p.author} · ♥ ${p.likes}`;
      const btn = card.querySelector("button");
      btn.disabled = have.has(p.slug);
      btn.onclick = () => addPalette(p.slug, btn);
      grid.append(card);
    });
    $("#lsPage").textContent = `Page ${page + 1}`;
    $("#lsPrev").disabled = page === 0;
    $("#lsPrev").onclick = () => searchLospec(page - 1);
    $("#lsNext").onclick = () => searchLospec(page + 1);
  } catch (e) { grid.innerHTML = `<div class="hint">Lospec is unreachable: ${e.message}</div>`; }
}
async function addPalette(slug, btn) {
  try {
    if (btn) { btn.disabled = true; btn.textContent = "Adding…"; }
    const t = await api("/api/themes/lospec", { slug });
    await loadThemes(true);
    if (btn) btn.textContent = "Added";
    toast(`Added ${t.name} by ${t.author}. Pick it as a theme.`);
    if (draft) renderThemes();
  } catch (e) {
    toast(e.message, "err");
    if (btn) { btn.disabled = false; btn.textContent = "Add"; }
  }
}
$("#lsGo").onclick = () => searchLospec(0);
$("#lsTag").onkeydown = (e) => { if (e.key === "Enter") searchLospec(0); };
$("#lsLinkGo").onclick = () => addPalette($("#lsLink").value);

const GEN_TITLES = {
  patterns: "Pixel Patterns settings",
  plasma: "Plasma settings",
  warp: "Warp Speed settings",
  matrix: "Digital Rain settings",
  fire: "Campfire settings",
  lava: "Lava Lamp settings",
  aurora: "Aurora settings",
  life: "Game of Life settings",
  ripple: "Ripples settings",
  fireworks: "Fireworks settings",
  videoeq: "Video Equations settings",
  spectre: "Spectre Patch settings",
};

// Generator settings (patterns, plasma, warp).
function renderGen() {
  const box = $("#eGen"), G = draft.generator;
  box.innerHTML = "";
  if (!G) return;
  const fields = { patterns: [["scale", "Zoom (px)"], ["vx", "Drift X (px/s)"], ["vy", "Drift Y (px/s)"], ["seconds", "Duration (s)"]],
                   plasma: [["scale", "Block size (px)"]], warp: [["speed", "Warp speed (px/s)"]],
                   matrix: [["scale", "Glyph scale (px)"], ["speed", "Fall speed (px/s)"], ["density", "Trail density (%)"]],
                   fire: [["scale", "Cell size (px)"], ["speed", "Wind drift (px/s)"], ["density", "Heat (%)"]],
                   lava: [["scale", "Cell size (px)"], ["speed", "Blob speed"], ["density", "Blob count"]],
                   aurora: [["scale", "Cell size (px)"], ["speed", "Wave speed"], ["density", "Brightness (%)"]],
                   life: [["scale", "Cell size (px)"], ["speed", "Generations/s"], ["density", "Seed density (%)"], ["seconds", "Reseed interval (s)"]],
                   ripple: [["scale", "Cell size (px)"], ["density", "Drop rate (drops/min)"]],
                   fireworks: [["speed", "Gravity"], ["density", "Launch rate (launches/min)"]],
                   videoeq: [["scale", "Cell size (px)"], ["speed", "Equation speed"], ["mode", "Equation (1-8, 0=all)"], ["seconds", "Duration (s)"]],
                   spectre: [["scale", "Cell size (px)"], ["speed", "Patch speed"], ["mode", "Patch (1-6, 0=all)"], ["seconds", "Duration (s)"]] }[G.type] || [];
  const tiles = player.gen ? player.gen.tiles.length / 32 : 0;
  const genTitle = GEN_TITLES[G.type] || `${G.type[0].toUpperCase() + G.type.slice(1)} settings`;
  box.append(el(`<h3>${genTitle} <span class="hint">${G.type === "patterns"
    ? `${tiles} tiles · colours are background/foreground pairs` : "colours are gradient stops"}</span></h3>`));
  const grid = el(`<div class="gen-grid"></div>`);
  fields.forEach(([k, label]) => {
    const f = el(`<label>${label}<input type="number" value="${G[k] ?? ""}"></label>`);
    f.querySelector("input").oninput = (e) => { G[k] = +e.target.value; player.warpStars = null; player.mxKey = null; };
    grid.append(f);
  });
  box.append(grid);
  const sw = el(`<div class="swatches"></div>`);
  const step = G.type === "patterns" ? 2 : 1;
  for (let i = 0; i < G.colors.length; i += step) {
    const grp = el(`<span class="pair"></span>`);
    for (let k = i; k < i + step && k < G.colors.length; k++) {
      const inp = el(`<input type="color" value="${G.colors[k]}">`);
      inp.oninput = () => (G.colors[k] = inp.value);
      grp.append(inp);
    }
    sw.append(grp);
  }
  const add = el(`<button class="icon-btn" title="Add colour">+</button>`);
  add.onclick = () => { G.colors.push(...(step === 2 ? ["#101018", "#ffffff"] : ["#ffffff"])); renderGen(); };
  const rm = el(`<button class="icon-btn" title="Remove last">−</button>`);
  rm.onclick = () => { if (G.colors.length > step) G.colors.splice(-step); renderGen(); };
  sw.append(add, rm);
  box.append(sw);
}

// Quota ring colours, stored on the active profile.
const RING_DEFAULTS = { healthy: "#49d7a0", warning: "#f4bc52", critical: "#ff6b6b", weekly: "#ffff00" };
function ringColors() { return { ...RING_DEFAULTS, ...(profile.colors || {}) }; }
function renderRings() {
  const c = ringColors(), levels = c.weekly === "levels";
  document.querySelectorAll("#pageSettings [data-c]").forEach((inp) => {
    const k = inp.dataset.c;
    inp.value = k === "weekly" && levels ? RING_DEFAULTS.weekly : c[k];
    inp.disabled = k === "weekly" && levels;
    inp.oninput = () => { profile.colors = { ...ringColors(), [k]: inp.value }; touch(); drawRingMock(); };
  });
  $("#weeklyLevels").checked = levels;
  drawRingMock();
}
$("#weeklyLevels").onchange = (e) => {
  profile.colors = { ...ringColors(), weekly: e.target.checked ? "levels" : RING_DEFAULTS.weekly };
  touch();
  renderRings();
};
$("#ringReset").onclick = () => { delete profile.colors; touch(); renderRings(); };
function drawRingMock() {
  const g = $("#ringMock").getContext("2d"), c = ringColors();
  g.fillStyle = "#101923";
  g.fillRect(0, 0, 320, 120);
  const ring = (x, left, col, label) => {
    g.lineWidth = 9;
    g.strokeStyle = "#29303d"; g.beginPath(); g.arc(x, 52, 30, 0, 7); g.stroke();
    g.strokeStyle = col; g.beginPath(); g.arc(x, 52, 30, -Math.PI / 2, -Math.PI / 2 + 6.283 * left / 100); g.stroke();
    g.fillStyle = col; g.font = "600 13px Segoe UI"; g.textAlign = "center"; g.fillText(`${left}%`, x, 57);
    g.fillStyle = "#8b8aa3"; g.font = "11px Segoe UI"; g.fillText(label, x, 104);
  };
  const lv = (l) => (l <= 10 ? c.critical : l <= 30 ? c.warning : c.healthy);
  [[70, "healthy"], [22, "warning"], [6, "critical"]].forEach(([l, label], i) => ring(45 + i * 70, l, lv(l), label));
  ring(275, 58, c.weekly === "levels" ? lv(58) : c.weekly, "weekly");
}

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

$("#vLive").onchange = (e) => setLive(e.target.checked);
