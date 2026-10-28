// Service Settings tab controller (T-024).
// Manages local aimon.config.json fields without credentials or profile pollution.

(function () {
  const SETTING_FIELDS = [
    { id: "cfg_serial_port", key: "serial_port", type: "string" },
    { id: "cfg_auto_brightness_enabled", key: "auto_brightness_enabled", type: "boolean" },
    { id: "cfg_auto_brightness_lat", key: "auto_brightness_lat", type: "float" },
    { id: "cfg_auto_brightness_lng", key: "auto_brightness_lng", type: "float" },
    { id: "cfg_auto_brightness_tz", key: "auto_brightness_tz", type: "string" },
    { id: "cfg_auto_brightness_day_duty", key: "auto_brightness_day_duty", type: "int" },
    { id: "cfg_auto_brightness_night_duty", key: "auto_brightness_night_duty", type: "int" },
    { id: "cfg_auto_brightness_startup_duty", key: "auto_brightness_startup_duty", type: "int" },
    { id: "cfg_auto_brightness_transition_duration", key: "auto_brightness_transition_duration", type: "int" },
    { id: "cfg_auto_brightness_smoothing_duration", key: "auto_brightness_smoothing_duration", type: "int" },
    { id: "cfg_limits_stale_s", key: "limits_stale_s", type: "float" },
    { id: "cfg_reset_warning_s", key: "reset_warning_s", type: "int" },
    { id: "cfg_quota_refresh_s", key: "quota_refresh_s", type: "float" },
    { id: "cfg_refresh_s", key: "refresh_s", type: "float" },
  ];

  let originalSettings = null;
  let settingsDirty = false;
  let isFetching = false;
  let isSaving = false;

  function setNotice(msg, kind = "") {
    const el = document.querySelector("#settingsNotice");
    if (!el) return;
    if (!msg) {
      el.hidden = true;
      el.textContent = "";
      el.className = "settings-notice";
      return;
    }
    el.hidden = false;
    el.textContent = msg;
    el.className = `settings-notice ${kind}`.trim();
  }

  function setDirty(dirty) {
    settingsDirty = dirty;
    const badge = document.querySelector("#settingsDirty");
    if (badge) badge.classList.toggle("on", dirty);
    const rev = document.querySelector("#settingsRevert");
    if (rev) rev.disabled = !dirty || isSaving;
  }

  function getFormValues() {
    const vals = {};
    SETTING_FIELDS.forEach(({ id, key, type }) => {
      const el = document.querySelector(`#${id}`);
      if (!el) return;
      if (type === "boolean") {
        vals[key] = Boolean(el.checked);
      } else if (type === "int") {
        vals[key] = el.value === "" ? null : Number(el.value);
      } else if (type === "float") {
        vals[key] = el.value === "" ? null : Number(el.value);
      } else {
        vals[key] = el.value.trim();
      }
    });
    return vals;
  }

  function checkDirty() {
    if (!originalSettings) {
      setDirty(false);
      return;
    }
    const current = getFormValues();
    let changed = false;
    for (const { key, type } of SETTING_FIELDS) {
      const orig = originalSettings[key];
      const cur = current[key];
      if (type === "float") {
        if (Math.abs((orig ?? 0) - (cur ?? 0)) > 1e-6) {
          changed = true;
          break;
        }
      } else if (orig !== cur) {
        changed = true;
        break;
      }
    }
    setDirty(changed);
  }

  function populateForm(data) {
    SETTING_FIELDS.forEach(({ id, key, type }) => {
      const el = document.querySelector(`#${id}`);
      if (!el || !(key in data)) return;
      if (type === "boolean") {
        el.checked = Boolean(data[key]);
      } else {
        el.value = data[key] ?? "";
      }
    });

    const abBody = document.querySelector("#cfgBrightnessBody");
    if (abBody) {
      abBody.classList.toggle("off", !data.auto_brightness_enabled);
    }
    setDirty(false);
  }

  async function loadSettings(force = false) {
    if (isFetching || (originalSettings && !force)) return;
    isFetching = true;
    setNotice("Loading settings\u2026");
    try {
      const r = await fetch("/api/settings");
      const data = await r.json();
      if (!r.ok || data.error) throw new Error(data.error || "Failed to load settings");
      originalSettings = structuredClone(data);
      populateForm(originalSettings);
      setNotice("");
    } catch (err) {
      setNotice(err.message, "err");
      if (typeof toast === "function") toast(err.message, "err");
    } finally {
      isFetching = false;
    }
  }

  function revertSettings() {
    if (!originalSettings) return;
    populateForm(originalSettings);
    setNotice("");
  }

  async function saveSettings() {
    if (isSaving || isFetching || !originalSettings) return;
    for (const { id } of SETTING_FIELDS) {
      const field = document.getElementById(id);
      if (field && !field.reportValidity()) return;
    }
    const saveBtn = document.querySelector("#settingsSave");
    const revertBtn = document.querySelector("#settingsRevert");
    const payload = getFormValues();

    isSaving = true;
    if (saveBtn) saveBtn.disabled = true;
    if (revertBtn) revertBtn.disabled = true;
    setNotice("Saving settings\u2026");

    try {
      const res = await api("/api/settings", payload);
      if (res.settings) {
        originalSettings = structuredClone(res.settings);
        populateForm(originalSettings);
      }
      setDirty(false);
      const msg = res.message || "Settings saved. Restart the AI Usage Monitor service to apply changes.";
      setNotice(msg, "ok");
      if (typeof toast === "function") toast(msg, "ok");
    } catch (err) {
      setNotice(err.message, "err");
      if (typeof toast === "function") toast(err.message, "err");
    } finally {
      isSaving = false;
      if (saveBtn) saveBtn.disabled = false;
      if (revertBtn) revertBtn.disabled = !settingsDirty;
    }
  }

  function initListeners() {
    SETTING_FIELDS.forEach(({ id }) => {
      const el = document.querySelector(`#${id}`);
      if (!el) return;
      el.addEventListener("input", checkDirty);
      el.addEventListener("change", checkDirty);
    });

    const abToggle = document.querySelector("#cfg_auto_brightness_enabled");
    if (abToggle) {
      abToggle.addEventListener("change", () => {
        const abBody = document.querySelector("#cfgBrightnessBody");
        if (abBody) abBody.classList.toggle("off", !abToggle.checked);
        checkDirty();
      });
    }

    const saveBtn = document.querySelector("#settingsSave");
    if (saveBtn) saveBtn.onclick = saveSettings;

    const revertBtn = document.querySelector("#settingsRevert");
    if (revertBtn) revertBtn.onclick = revertSettings;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initListeners);
  } else {
    initListeners();
  }

  window.loadServiceSettings = loadSettings;
  window.hasUnsavedSettings = () => settingsDirty;
  window.revertServiceSettings = revertSettings;
})();
