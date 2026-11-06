// Updates tab: check upstream, show what is new, update safely, undo.
// Upstream text (commit subjects, file names) is untrusted: it is only ever set via textContent.
(function () {
  const $u = (s) => document.querySelector(s);
  const show = (sel, on) => { $u(sel).hidden = !on; };
  let st = null;
  let busy = false;

  function notice(msg, kind = "") {
    const n = $u("#updNotice");
    n.hidden = !msg;
    n.textContent = msg || "";
    n.className = `settings-notice ${kind}`.trim();
  }

  function fill(list, items) {
    list.replaceChildren(...items.map((t) => { const li = document.createElement("li"); li.textContent = t; return li; }));
  }

  function render(s) {
    st = s;
    const where = s.branch ? `branch ${s.branch}` : "";
    $u("#updTitle").textContent = s.version ? `Version ${s.version}` : "Updates";
    $u("#updSub").textContent = [where, s.commit && `build ${s.commit}`].filter(Boolean).join(" · ");
    $u("#updateDot").hidden = !(s.behind > 0);
    const hasUpdate = s.behind > 0;
    show("#updAvail", hasUpdate);
    if (hasUpdate) {
      const target = s.upstream_version && s.upstream_version !== s.version ? ` (${s.upstream_version})` : "";
      $u("#updAvailTitle").textContent = `${s.behind} new change${s.behind === 1 ? "" : "s"} available${target}`;
      fill($u("#updList"), s.pending);
      const m = $u("#updMerge");
      if (s.conflicts && s.conflicts.length) { m.textContent = `Overlaps with your edits in ${s.conflicts.length} file(s)`; m.className = "hint warn"; }
      else if (s.conflicts) { m.textContent = "Merges cleanly with your changes"; m.className = "hint good"; }
      else { m.textContent = ""; m.className = "hint"; }
      show("#updSaveRow", s.dirty.length > 0);
      $u("#updSaveText").textContent = `Save my ${s.dirty.length} uncommitted change${s.dirty.length === 1 ? "" : "s"} first`;
      $u("#updApply").disabled = busy || Boolean(s.blocker);
    }
    if (s.fetch_error) notice(`Could not check GitHub: ${s.fetch_error}`, "err");
    else if (s.blocker) notice(s.blocker, "err");
    else if (s.checked && !hasUpdate) notice("You are up to date.", "ok");
    else notice("");
    $u("#updBackupInfo").textContent = s.backups.length ? `Restores ${s.backups[0].replace("backup/pre-update-", "")}` : "No backup yet";
    $u("#updRollback").disabled = busy || !s.backups.length;
  }

  async function refresh(check) {
    if (busy) return;
    busy = true;
    $u("#updCheck").disabled = true;
    if (check) notice("Checking GitHub…");
    try {
      render(await api(check ? "/api/update/check" : "/api/update/status", check ? {} : undefined));
    } catch (e) { notice(e.message, "err"); }
    busy = false;
    $u("#updCheck").disabled = false;
    if (st) $u("#updRollback").disabled = !st.backups.length;
  }

  async function follow(jobId, label) {
    show("#updLogCard", true);
    $u("#updStep").textContent = label;
    for (;;) {
      await new Promise((r) => setTimeout(r, 700));
      const j = await api(`/api/jobs/${jobId}`);
      const log = $u("#updLog");
      log.textContent = j.log;
      log.scrollTop = log.scrollHeight;
      if (j.step) $u("#updStep").textContent = j.step;
      if (j.state !== "running") return j;
    }
  }

  async function applyUpdate() {
    if (busy) return;
    busy = true;
    ["#updApply", "#updCheck", "#updRollback"].forEach((s) => ($u(s).disabled = true));
    show("#updConflict", false);
    show("#updDone", false);
    try {
      const { job } = await api("/api/update/apply", { commit_first: $u("#updSaveFirst").checked });
      const j = await follow(job, "Updating");
      const r = j.result || { ok: j.state === "done" };
      if (r.ok) {
        notice(r.warning || "Update merged.", r.warning ? "err" : "ok");
        show("#updAvail", false);
        $u("#updDoneVer").textContent = r.backup ? `Backup: ${r.backup}` : "";
        show("#updDone", true);
      } else if (r.conflicts) {
        notice("The update was not applied. Nothing changed.", "err");
        fill($u("#updConflictFiles"), r.conflicts);
        $u("#updPrompt").value = r.prompt || "";
        show("#updConflict", true);
      } else {
        notice(r.error || "Update failed.", "err");
      }
    } catch (e) { notice(e.message, "err"); }
    busy = false;
    $u("#updCheck").disabled = false;
    await refresh(false);
  }

  async function flashNow() {
    if (busy) return;
    busy = true;
    $u("#updFlash").disabled = true;
    try {
      const { job } = await api("/api/flash", { profile: typeof pid === "string" ? pid : "default" });
      const j = await follow(job, "Building");
      toast(j.state === "done" ? "The display is running the new version" : `${j.step} failed. See the log.`, j.state === "done" ? "ok" : "err");
    } catch (e) { toast(e.message, "err"); }
    busy = false;
    $u("#updFlash").disabled = false;
  }

  async function restartService() {
    $u("#updService").disabled = true;
    try {
      const r = await api("/api/update/restart-service", {});
      toast(r.ok ? "Service restarted" : `Restart failed: ${r.error || r.log}`, r.ok ? "ok" : "err");
    } catch (e) { toast(e.message, "err"); }
    $u("#updService").disabled = false;
  }

  async function rollback() {
    if (busy || !confirm("Go back to how things were before the last update? Your uncommitted changes must be saved first.")) return;
    try {
      const r = await api("/api/update/rollback", {});
      if (r.ok) { notice(`Restored ${r.backup}. ${r.next}`, "ok"); show("#updDone", true); }
      else notice(r.error, "err");
    } catch (e) { notice(e.message, "err"); }
    await refresh(false);
  }

  $u("#updCheck").onclick = () => refresh(true);
  $u("#updApply").onclick = applyUpdate;
  $u("#updFlash").onclick = flashNow;
  $u("#updService").onclick = restartService;
  $u("#updRollback").onclick = rollback;
  $u("#updCopy").onclick = async () => {
    try { await navigator.clipboard.writeText($u("#updPrompt").value); toast("Prompt copied"); }
    catch { $u("#updPrompt").select(); toast("Press Ctrl+C to copy", "err"); }
  };

  window.openUpdates = () => refresh(false);
  // Quietly look for updates once when Studio opens, to light the dot in the sidebar.
  window.addEventListener("load", () => setTimeout(() => api("/api/update/check", {}).then(render).catch(() => {}), 1500));
})();
