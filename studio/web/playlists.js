// Playlists tab: build named scene rotations. Each playlist can be a tap page
// ("playlist:<id>" in profile.pages) or the screensaver. The built-in
// "All scenes" page rotates through everything every scene_seconds.

let plSel = null;          // selected playlist id, or "all"
let plPlayer = null, plTimer = null, plPos = 0;

const plList = () => (profile.playlists = profile.playlists || []);
const plFind = (id) => plList().find((p) => p.id === id);
const sceneById = (id) => (state.scenes || []).find((s) => s.id === id);
function sceneThumb(id) { const s = sceneById(id); return s ? `/library/${s.entry}/preview.png` : ""; }

// Older profiles had a single "playlist" list: turn it into a named playlist.
function migratePlaylist() {
  if (!profile.playlist) return;
  plList().push({ id: "my-rotation", name: "My rotation", seconds: profile.scene_seconds || 90, scenes: profile.playlist });
  delete profile.playlist;
}

function renderPlaylists() {
  migratePlaylist();
  const box = $("#plList");
  if (!box) return;
  box.innerHTML = "";
  const all = el(`<button class="pl-card ${plSel === "all" ? "on" : ""}">
    <div class="pl-strip">${(state.scenes || []).slice(0, 4).map((s) => `<span style="background-image:url('${sceneThumb(s.id)}')"></span>`).join("")}</div>
    <b>All scenes</b><small>${(state.scenes || []).length} scenes · ${profile.scene_seconds || 90}s each · built in</small></button>`);
  all.onclick = () => { plSel = "all"; renderPlaylists(); };
  box.append(all);
  plList().forEach((pl) => {
    const b = el(`<button class="pl-card ${plSel === pl.id ? "on" : ""}">
      <div class="pl-strip">${pl.scenes.slice(0, 4).map((id) => `<span style="background-image:url('${sceneThumb(id)}')"></span>`).join("")}</div>
      <b></b><small>${pl.scenes.length} scenes · ${pl.seconds}s each${profile.pages.includes(`playlist:${pl.id}`) ? " · tap page" : ""}${profile.screensaver.page === `playlist:${pl.id}` ? " · screensaver" : ""}</small></button>`);
    b.querySelector("b").textContent = pl.name;
    b.onclick = () => { plSel = pl.id; renderPlaylists(); };
    box.append(b);
  });
  const add = el(`<button class="pl-card new"><b>+ New playlist</b><small>Pick scenes and their order</small></button>`);
  add.onclick = () => {
    let n = plList().length + 1, id;
    do id = `rotation-${n++}`; while (plFind(id));
    plList().push({ id, name: `Rotation ${n - 1}`, seconds: 60, scenes: [] });
    plSel = id;
    touch();
  };
  box.append(add);
  if (!plSel) plSel = plList()[0]?.id || "all";
  renderPlEditor();
}

function renderPlEditor() {
  const ed = $("#plEditor");
  const isAll = plSel === "all", pl = isAll ? null : plFind(plSel);
  if (!isAll && !pl) { plSel = "all"; return renderPlaylists(); }
  const pageId = isAll ? "scenes" : `playlist:${pl.id}`;
  const scenes = isAll ? (state.scenes || []).map((s) => s.id) : pl.scenes;
  const index = isAll ? -1 : plList().indexOf(pl);
  ed.innerHTML = `
    <div class="pl-head">
      <input class="pl-name" ${isAll ? "disabled" : ""}>
      <label class="pl-secs">Each scene <input type="number" min="1" max="3600" class="pl-sec"> s</label>
    </div>
    <div class="pl-flags">
      <label class="check"><input type="checkbox" class="pl-page" ${profile.pages.includes(pageId) ? "checked" : ""}> Tap page in Layout</label>
      <label class="check"><input type="radio" name="plsaver" class="pl-saver" ${profile.screensaver.page === pageId ? "checked" : ""}> Use as screensaver</label>
      ${isAll ? "" : `<label class="check" title="Each scene turn picks clear skies, rain, snow or a storm, replacing the scene's own weather"><input type="checkbox" class="pl-weather" ${pl.weather === "random" ? "checked" : ""}> Random weather</label>`}
      <span class="grow"></span>
      <button class="btn ghost pl-show">Show on display</button>
      ${isAll ? "" : '<button class="btn ghost danger pl-del">Delete</button>'}
    </div>
    <div class="pl-body">
      <div class="pl-stage"><canvas width="320" height="240"></canvas><div class="pl-now"></div></div>
      <div class="pl-side">
        <h3>Rotation order <span class="hint">${isAll ? "every scene, library order" : "drag to reorder"}</span></h3>
        <ol class="pl-order"></ol>
        ${isAll ? "" : '<h3>Add scenes <span class="hint">click to append</span></h3><div class="pl-add"></div>'}
      </div>
    </div>`;
  const name = ed.querySelector(".pl-name");
  name.value = isAll ? "All scenes" : pl.name;
  name.oninput = () => { pl.name = name.value; touch(); };
  const wx = ed.querySelector(".pl-weather");
  if (wx) wx.onchange = () => { if (wx.checked) pl.weather = "random"; else delete pl.weather; touch(); };
  const secs = ed.querySelector(".pl-sec");
  secs.value = isAll ? profile.scene_seconds || 90 : pl.seconds;
  secs.onchange = () => {
    const v = Math.min(3600, Math.max(1, +secs.value || 60));
    if (isAll) profile.scene_seconds = v; else pl.seconds = v;
    touch();
  };
  ed.querySelector(".pl-page").onchange = (e) => {
    profile.pages = e.target.checked ? [...profile.pages, pageId] : profile.pages.filter((x) => x !== pageId);
    touch();
  };
  ed.querySelector(".pl-saver").onchange = () => {
    profile.screensaver.page = pageId;
    profile.screensaver.enabled = true;
    touch();
  };
  ed.querySelector(".pl-show").onclick = async () => {
    try {
      const r = await api("/api/device", { commands: [`!SHOW ${isAll ? "scenes" : `playlist-${index}`}`] });
      if ((r.replies[0] || "").startsWith("@SHOW ok")) toast(`Playing ${name.value} on the display. Tap it to go back.`);
      else toast("This playlist isn't on the display yet. Send to display first.", "err");
    } catch (e) { toast(e.message, "err"); }
  };
  const del = ed.querySelector(".pl-del");
  if (del) del.onclick = () => {
    if (!confirm(`Delete playlist "${pl.name}"?`)) return;
    profile.playlists = plList().filter((p) => p !== pl);
    profile.pages = profile.pages.filter((x) => x !== pageId);
    if (profile.screensaver.page === pageId) profile.screensaver.page = "scenes";
    plSel = null;
    touch();
  };

  const ol = ed.querySelector(".pl-order");
  scenes.forEach((id, i) => {
    const s = sceneById(id);
    const li = el(`<li draggable="${!isAll}" data-i="${i}"><span class="pl-thumb" style="background-image:url('${sceneThumb(id)}')"></span>
      <span class="grow"></span>${isAll ? "" : '<button class="icon-btn" title="Remove">×</button>'}</li>`);
    li.querySelector(".grow").textContent = s ? s.name : `${id} (missing)`;
    li.onclick = (ev) => { if (ev.target.tagName !== "BUTTON") playAt(i); };
    const rm = li.querySelector("button");
    if (rm) rm.onclick = () => { pl.scenes.splice(i, 1); touch(); };
    if (!isAll) {
      li.ondragstart = () => li.classList.add("dragging");
      li.ondragend = () => {
        li.classList.remove("dragging");
        pl.scenes = [...ol.children].map((c) => scenes[+c.dataset.i]);
        touch();
      };
    }
    ol.append(li);
  });
  ol.addEventListener("dragover", (e) => {
    e.preventDefault();
    const drag = ol.querySelector(".dragging");
    if (!drag) return;
    const after = [...ol.querySelectorAll("li:not(.dragging)")].find((c) => e.clientY < c.getBoundingClientRect().top + c.offsetHeight / 2);
    if (after) ol.insertBefore(drag, after); else ol.append(drag);
  });
  if (!scenes.length) ol.append(el(`<li class="empty-row">No scenes yet. Add some below.</li>`));

  const addBox = ed.querySelector(".pl-add");
  if (addBox) (state.scenes || []).forEach((s) => {
    const b = el(`<button class="pl-pick"><span class="pl-thumb" style="background-image:url('${sceneThumb(s.id)}')"></span><span></span></button>`);
    b.lastChild.textContent = s.name;
    b.onclick = () => { pl.scenes.push(s.id); touch(); };
    addBox.append(b);
  });

  // Preview: step through the rotation every 4 s (faster than the device, to skim it).
  clearInterval(plTimer);
  plPlayer?.stop();
  plPlayer = new ScenePlayer(ed.querySelector(".pl-stage canvas"));
  plPos = 0;
  const playAt = async (i) => {
    if (!scenes.length) return;
    plPos = i % scenes.length;
    const s = sceneById(scenes[plPos]);
    const entry = s && state.library.find((e) => e.id === s.entry);
    ed.querySelector(".pl-now").textContent = s ? `${plPos + 1}/${scenes.length} · ${s.name}` : "";
    [...ol.children].forEach((c, k) => c.classList.toggle("now", k === plPos));
    if (entry) await plPlayer.load(entry.id, { ...structuredClone(entry.scene), theme: s.theme }).catch(() => {});
  };
  playAt(0);
  plTimer = setInterval(() => {
    if (!document.contains(ol) || !$("#tab-playlists").classList.contains("on")) return plPlayer.stop();
    playAt(plPos + 1);
  }, 4000);
}
