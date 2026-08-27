(() => {
  const HIDDEN = new Set([
    "setPureDirectOn",
    "setSetupLock",
    "setAdjustEQ",
    "setGEQCurveCopy",
    "setGEQSetDefaults",
    "setAudioDelay",
    "setMainPwOnLevel",
    "setSourceLevelDigital",
    "setCLA",
    "setDelayTimeAllSet",
    "setLfeLevel",
    "FriendlySet",
    "FriendlyDef",
    "setZoneRenameAll",
    "setZoneRenameDefault",
    "setQuickSelectName",
    "setQuickSelectNameAll",
    "setUpdateCheck",
    "setAddNewFeature",
    "setFirmwareUpdateWebUpdate",
  ]);
  const BANDS = [
    ["63", "textGEQ63"],
    ["125", "textGEQ125"],
    ["250", "textGEQ250"],
    ["500", "textGEQ500"],
    ["1k", "textGEQ1k"],
    ["2k", "textGEQ2k"],
    ["4k", "textGEQ4k"],
    ["8k", "textGEQ8k"],
    ["16k", "textGEQ16k"],
  ];
  const INFO_ACTIONS = new Set([
    "info_network",
    "info_firmware",
    "info_dashboard",
    "setup_info",
  ]);
  // Network pages must NEVER auto-apply — saving resets the LAN connection.
  const NETWORK_EXPLICIT_SAVE = new Set([
    "network_settings_s_network_setting_dhcp",
    "network_connection_s_network_setting_dhcp",
  ]);
  // Apply only via Set / Set Defaults buttons (Denon button-gated forms).
  const EXPLICIT_SAVE = new Set([
    "inputs_sourcerename_s_rename",
    "inputs_sourcelevel_s_inputsetup",
    "speakers_levels_s_speakersetup",
    "general_zonerename_s_general",
    "general_selectnames_s_general",
    "audio_audiodelay_s_audio",
    ...NETWORK_EXPLICIT_SAVE,
  ]);
  const PRIMARY_SAVE_ACTIONS = {
    inputs_sourcerename_s_rename: { setFuncRenameAll: "on" },
    inputs_sourcelevel_s_inputsetup: { setSourceLevelDigital: "on" },
    speakers_levels_s_speakersetup: { setCLA: "Set" },
    speakers_distances_s_speakersetup: { setDelayTimeAllSet: "Set" },
    network_friendlyname_s_network: { FriendlySet: "Set" },
    general_zonerename_s_general: { setZoneRenameAll: "on" },
    general_selectnames_s_general: { setbtnQuickSelectNameAll: " Set" },
    audio_audiodelay_s_audio: { setAudioDelay: "on" },
    audio_surroundparameter_s_audio: { setLfeLevel: "on" },
    audio_volume_s_audio: { setMainPwOnLevel: "on" },
  };
  const PAGE_HELP = {
    inputs_sourcerename_s_rename:
      "Allows you to change the names of the source inputs",
    inputs_hidesources_s_delete:
      "Selects source inputs to hide on the GUI and front panel displays",
    inputs_sourcelevel_s_inputsetup:
      "Adjusts the input level for the current source",
    speakers_levels_s_speakersetup:
      "Manually adjust the levels for each channel — drag sliders for preview, then press Set",
    speakers_distances_s_speakersetup:
      "Select the distance for each speaker, then press Set",
    network_friendlyname_s_network:
      "Edits the name of the AVR that is displayed on the network",
    general_zonerename_s_general: "Changes the name of each zone",
    general_selectnames_s_general: "Changes the Quick Select display names",
    video_tvformat_s_video:
      "Selects the format used to send video to the TV",
    video_hdmisetup_s_video: "Adjusts the HDMI settings",
    video_onscreendisplay_s_video: "Sets the on-screen display",
    audio_dialoglevel_s_audio: "Adjusts the dialog level",
    audio_subwooferlevel_s_audio:
      "Adjusts the subwoofer channel volume for more or less bass",
    audio_surroundparameter_s_audio: "Adjusts the surround sound parameters",
    audio_audiodelay_s_audio:
      "Compensates for incorrect timing between video and audio signals",
    audio_volume_s_audio: "Adjusts volume parameters",
    audio_audyssey_s_audio: "Adjusts Audyssey parameters",
    audio_graphiceq_s_audio:
      "Graphic EQ per speaker. Channel list follows Amp Assign. Export/Import all curves; blocked if Amp Assign differs; missing speakers skipped.",
    audio_bilingualmode_s_audio: "Sets bilingual audio mode",
  };
  const state = {
    connected: false,
    menu: null,
    sectionId: "audio",
    selectedMenuId: null,
    endpointId: null,
    writeAllowed: true,
    realtimeTimer: null,
    realtimeBusy: false,
    infoCards: [],
    infoLoaded: false,
    eqEnabled: false,
    eqBusy: false,
    eqLoading: false,
    lastEqBands: Object.fromEntries(BANDS.map(([k]) => [k, 0])),
    eqRemoteFingerprint: null,
    eqPendingFingerprint: null,
    eqPendingSince: 0,
    reloadAction: null,
    menuRefreshTimer: null,
    pollTimer: null,
    pollInFlight: false,
    pollTick: 0,
    pageDirty: false,
    lastLocalWriteAt: 0,
    lastAvrCheckAt: null,
    lastAvrUpdateAt: null,
    powerOn: null,
    powerBusy: false,
    powerZone: "MAIN ZONE",
    powerInput: "—",
    route: { view: "dashboard" },
    controlCatalog: null,
    controlCatalogByLayout: { less: null, more: null },
    controlSectionId: null,
    /** Per nav-section override: 'less' | 'more' — independent of Settings */
    controlSectionLayout: {},
    controlEntities: {},
    controlPollTimer: null,
    controlLog: [],
    controlBusy: false,
    activityLog: [],
    activityUnread: 0,
    activityOpen: false,
    activityBannerTimer: null,
    dashboard: null,
    dashboardEdit: false,
    dashboardCatalog: null,
    dashboardDrag: null,
    dashboardIcons: null,
    dashboardIconTarget: null,
    dashboardStatusReady: false,
    appSettings: {
      poll_enabled: true,
      poll_interval_sec: 5,
      eq_confirm_sec: 30,
      edit_mode: "realtime",
      lock_settings_in_standby: true,
      show_sync_timestamps: true,
      theme: "system",
      confirm_network_save: true,
      confirm_firmware_actions: true,
      avr_model: "AVR-X1200W",
      control_grouping: "less controls",
      show_zone2: false,
      show_zone3: false,
    },
    buildChannel: "production",
    appSettingsMeta: [],
    appSettingsPath: "",
    appSettingsFileExists: false,
    settingsDirty: false,
    mqttSettings: null,
    mqttCatalog: null,
    mqttPresets: [],
    mqttLayout: "less",
    mqttPresetPreviewId: null,
    mqttPresetEntityLabels: {},
    mqttPresetRemoteRegions: [],
    mqttPresetManagerOpen: false,
    mqttExportMode: "mqtt",
    mqttLovelaceStyle: "rc1189",
    mqttSectionId: null,
    mqttHaFormat: "json",
  };

  const DEFAULT_APP_SETTINGS = { ...state.appSettings };

  function radioOptionSelected(meta, opt, raw) {
    if (opt && typeof opt === "object" && opt.selected) return true;
    if (meta?.value == null || meta.value === "") return false;
    return String(meta.value).toUpperCase() === String(raw).toUpperCase();
  }

  function pollIntervalMs() {
    const n = Number(state.appSettings.poll_interval_sec);
    const sec = Number.isFinite(n) ? Math.max(2, Math.min(120, n)) : 5;
    return Math.round(sec * 1000);
  }

  function eqConfirmMs() {
    const n = Number(state.appSettings.eq_confirm_sec);
    const sec = Number.isFinite(n) ? Math.max(0, Math.min(300, n)) : 30;
    return Math.round(sec * 1000);
  }

  function isSaveEditMode() {
    return String(state.appSettings.edit_mode || "realtime") === "save";
  }

  function usesExplicitSave(endpointId) {
    const id = endpointId || state.endpointId;
    if (!id) return isSaveEditMode();
    if (NETWORK_EXPLICIT_SAVE.has(id) || EXPLICIT_SAVE.has(id)) return true;
    return isSaveEditMode();
  }

  function editorHasFocus() {
    const form = $("field-form");
    const active = document.activeElement;
    if (!form || !active) return false;
    return form.contains(active);
  }

  function syncEditModeUi() {
    const mode = isSaveEditMode() ? "save" : "realtime";
    for (const btn of document.querySelectorAll("[data-edit-mode]")) {
      btn.classList.toggle(
        "active",
        btn.getAttribute("data-edit-mode") === mode
      );
    }
    const hint = $("live-hint");
    if (hint) {
      hint.textContent = isSaveEditMode()
        ? "Edit locally, then press Save"
        : "Realtime edits";
      hint.classList.toggle("is-save-mode", isSaveEditMode());
    }
    const badge = $("build-badge");
    if (badge) {
      const isDev = state.buildChannel === "dev";
      badge.hidden = !isDev;
      document.body.classList.toggle("is-dev-build", isDev);
    }
    document.body.classList.toggle("edit-mode-save", isSaveEditMode());
    document.body.classList.toggle("edit-mode-realtime", !isSaveEditMode());
    syncPageSaveToolbar();
  }

  async function setEditMode(mode) {
    const next = mode === "save" ? "save" : "realtime";
    if (String(state.appSettings.edit_mode) === next) {
      syncEditModeUi();
      return;
    }
    try {
      await persistAppSettings({ edit_mode: next });
      setStatus(
        next === "save"
          ? "Save mode on — press Save to write and refresh"
          : "Realtime on — changes apply as you edit",
        "ok"
      );
      if (typeof state.reloadAction === "function") {
        await state.reloadAction();
      }
    } catch (err) {
      setStatus(err.message, "err");
    }
  }

  function wireEditModeToggle() {
    for (const btn of document.querySelectorAll("[data-edit-mode]")) {
      btn.addEventListener("click", () => {
        setEditMode(btn.getAttribute("data-edit-mode")).catch(() => {});
      });
    }
  }

  function isMergedSetLabel(text) {
    const t = String(text || "")
      .trim()
      .toLowerCase()
      .replace(/\s+/g, " ");
    if (!t) return false;
    if (/default|curve|copy|reset|upload|update|firmware|connect|engage|cancel|clear/.test(t)) {
      return false;
    }
    return t === "set" || t === "apply" || t === "save" || t === "ok";
  }

  function shouldHideMergedSetButton(name, meta) {
    // Keep per-page Set / Set Defaults visible in both realtime and Save mode.
    return false;
  }

  function primarySaveActionFields(endpointId) {
    const id = endpointId || state.endpointId;
    if (!id) return {};
    const action = PRIMARY_SAVE_ACTIONS[id];
    if (!action) return {};
    const form = $("field-form");
    if (id === "audio_surroundparameter_s_audio" && !form?.querySelector('[name="textLfeLevel"]')) {
      return {};
    }
    if (id === "audio_volume_s_audio" && !form?.querySelector('[name="textMainPwOnLevel"]')) {
      return {};
    }
    return { ...action };
  }

  function padQuickSelectName(value) {
    const s = String(value ?? "");
    if (s.length >= 16) return s.slice(0, 16);
    return s.padEnd(16, " ");
  }

  function mergeSubmitFields(extra) {
    const fields = { ...collectFields(), ...(extra || {}) };
    if (state.endpointId === "general_selectnames_s_general") {
      for (const [name, value] of Object.entries(fields)) {
        if (name.startsWith("textQuickSelectName")) fields[name] = padQuickSelectName(value);
      }
    }
    const hiddenOffUnless = [
      "setFuncRenameDefault",
      "setFuncRenameAll",
      "setSourceLevelDigital",
      "buttonNet",
      "setLfeLevel",
      "setAudioDelay",
      "setMainPwOnLevel",
      "setCLA",
      "setDelayTimeAllSet",
      "FriendlySet",
      "FriendlyDef",
      "setZoneRenameAll",
      "setZoneRenameDefault",
      "setQuickSelectName",
      "setQuickSelectNameAll",
    ];
    for (const name of hiddenOffUnless) {
      if (!extra?.[name]) fields[name] = "off";
    }
    // Denon submit/button names — omit entirely unless this action set them.
    // Posting setBtnQuickSelectNameDefault=off triggers Set Defaults on Quick Select.
    const submitOnly = [
      "setBtnQuickSelectNameDefault",
      "setbtnQuickSelectNameAll",
      "setbtnLfeLevel",
    ];
    for (const name of submitOnly) {
      if (!extra?.[name]) delete fields[name];
    }
    return fields;
  }

  function syncEditorPrimaryBtn() {
    const btn = $("editor-primary-btn");
    if (!btn) return;
    btn.textContent = "Save";
    btn.setAttribute("aria-label", "Save");
    btn.title = "Save to AVR and refresh this page";
    btn.classList.remove("icon-btn", "is-save-mode");
    btn.classList.add("btn-ghost", "editor-save-btn");
    const canSave =
      isSaveEditMode() &&
      Boolean(state.endpointId) &&
      state.writeAllowed !== false &&
      !NETWORK_EXPLICIT_SAVE.has(state.endpointId || "");
    btn.hidden = !canSave;
    btn.disabled = false;
  }

  function runEditorReload() {
    return refreshMenuAvailability({ immediate: true })
      .catch(() => {})
      .finally(() => {
        if (typeof state.reloadAction === "function") state.reloadAction();
        else {
          const node = findMenuNode(state.selectedMenuId);
          if (node) openMenuNode(node);
        }
      });
  }

  async function onEditorPrimaryClick() {
    const btn = $("editor-primary-btn");
    if (!btn || btn.hidden || btn.disabled) return;
    if (!isSaveEditMode()) return;
    if (!state.endpointId || !state.writeAllowed) return;
    if (!settingsWritable()) {
      setStatus("Main Zone Standby — settings locked", "warn");
      applyStandbySettingsLock();
      return;
    }
    try {
      btn.disabled = true;
      const ok = await saveEndpoint({ quiet: false, fromPrimary: true });
      if (ok) await runEditorReload();
    } catch (err) {
      setStatus(err.message, "err");
    } finally {
      btn.disabled = false;
      syncEditorPrimaryBtn();
    }
  }

  function syncPageSaveToolbar() {
    // Legacy toolbar removed — primary Save/Reload lives in the editor header.
    const bar = $("page-save-toolbar");
    if (bar) bar.remove();
    syncEditorPrimaryBtn();
  }

  const $ = (id) => document.getElementById(id);
  const statusEl = $("connect-status");

  function setAvrHostLabel(host) {
    const el = $("avr-host");
    if (!el) return;
    el.textContent = cleanText(host) || "—";
    el.title = "DENON_HOST from docker-compose / environment";
  }

  async function api(path, opts = {}) {
    const res = await fetch(path, {
      headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
      ...opts,
    });
    const text = await res.text();
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = { detail: text };
    }
    if (!res.ok) {
      const msg =
        data?.detail?.message ||
        (typeof data?.detail === "string" ? data.detail : null) ||
        data?.message ||
        res.statusText;
      throw new Error(typeof msg === "string" ? msg : JSON.stringify(data?.detail || msg));
    }
    return data;
  }

  function setStatus(text, kind) {
    statusEl.textContent = text;
    statusEl.classList.remove("ok", "err", "warn");
    if (kind) statusEl.classList.add(kind);
  }

  function pushActivity(text, kind = "info", { silent = false } = {}) {
    const msg = String(text || "").trim();
    if (!msg) return;
    // Skip transient progress noise in the feed
    const skip =
      /^(Applying|Updating|Reading AVR|Loading AVR|Refreshing|Ready)/i.test(msg);
    if (!skip) {
      state.activityLog.unshift({
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
        text: msg,
        kind: kind || "info",
        at: new Date().toISOString(),
      });
      if (state.activityLog.length > 100) state.activityLog.length = 100;
      if (!state.activityOpen) {
        state.activityUnread = Math.min(99, (state.activityUnread || 0) + 1);
      }
      renderActivityBadge();
      if (state.activityOpen) renderActivityList();
    }
    // Never mirror activity into page banners — the bell is the notification UI.
    void silent;
  }

  function flashTransientBanner(_text, _kind) {
    // Intentionally empty: activity goes to the top-bar bell only.
  }

  function renderActivityBadge() {
    const badge = $("activity-count");
    const btn = $("activity-btn");
    if (!badge) return;
    const n = state.activityUnread || 0;
    if (n <= 0) {
      badge.hidden = true;
      badge.textContent = "0";
      btn?.classList.remove("has-unread");
      return;
    }
    badge.hidden = false;
    badge.textContent = n > 99 ? "99+" : String(n);
    btn?.classList.add("has-unread");
  }

  function renderActivityList() {
    const list = $("activity-list");
    if (!list) return;
    list.innerHTML = "";
    if (!state.activityLog.length) {
      list.innerHTML = `<p class="meta activity-empty">No activity yet</p>`;
      return;
    }
    for (const item of state.activityLog) {
      const row = document.createElement("div");
      row.className = `activity-item kind-${item.kind || "info"}`;
      const time = document.createElement("time");
      time.dateTime = item.at;
      time.textContent = formatSyncClock(item.at);
      const body = document.createElement("p");
      body.textContent = item.text;
      row.appendChild(time);
      row.appendChild(body);
      list.appendChild(row);
    }
  }

  function setActivityOpen(open) {
    state.activityOpen = Boolean(open);
    const panel = $("activity-panel");
    const btn = $("activity-btn");
    if (panel) panel.hidden = !state.activityOpen;
    btn?.setAttribute("aria-expanded", state.activityOpen ? "true" : "false");
    btn?.classList.toggle("is-open", state.activityOpen);
    if (state.activityOpen) {
      state.activityUnread = 0;
      renderActivityBadge();
      renderActivityList();
    }
  }

  function wireActivity() {
    $("activity-btn")?.addEventListener("click", (ev) => {
      ev.stopPropagation();
      setActivityOpen(!state.activityOpen);
    });
    $("activity-close")?.addEventListener("click", () => setActivityOpen(false));
    $("activity-clear")?.addEventListener("click", () => {
      state.activityLog = [];
      state.activityUnread = 0;
      renderActivityBadge();
      renderActivityList();
    });
    document.addEventListener("click", (ev) => {
      if (!state.activityOpen) return;
      const panel = $("activity-panel");
      const btn = $("activity-btn");
      if (panel?.contains(ev.target) || btn?.contains(ev.target)) return;
      setActivityOpen(false);
    });
  }

  function formatSyncClock(isoOrDate) {
    const d =
      isoOrDate instanceof Date
        ? isoOrDate
        : isoOrDate
          ? new Date(isoOrDate)
          : new Date();
    if (Number.isNaN(d.getTime())) return "—";
    return d.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }

  /** Show when we last polled / talked to the AVR. */
  function markAvrSyncTime(opts = {}) {
    const iso = opts.at || new Date().toISOString();
    const changed = Boolean(opts.changed);
    state.lastAvrCheckAt = iso;
    if (changed) state.lastAvrUpdateAt = iso;

    const clock = formatSyncClock(iso);
    const show = state.appSettings.show_sync_timestamps !== false;
    const eqEl = $("eq-sync");
    if (eqEl) {
      eqEl.classList.toggle("is-hidden", !show);
      if (show) {
        eqEl.textContent = changed
          ? `Last update from AVR: ${clock}`
          : `Last AVR check: ${clock}`;
      }
    }
    const poll = $("poll-stamp");
    if (poll) {
      poll.classList.toggle("is-hidden", !show);
      if (show) poll.textContent = clock;
    }
  }

  function escapeHtml(s) {
    return String(s)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
  }

  function cleanText(s) {
    let t = String(s ?? "")
      .replace(/<[^>]+>/g, " ")
      .replace(/&nbsp;/gi, " ")
      .replace(/\s+/g, " ")
      .trim();
    if (!t) return "";
    if (t === "-" || t === "–" || t === "—") return "-";
    // Keep leading minus for numeric / dB labels (−79.5dB, −20dB, …)
    if (/^[\-–—]\s*\d/.test(t)) {
      if (t[0] === "–" || t[0] === "—") t = "-" + t.slice(1).replace(/^\s+/, "");
      return t;
    }
    // Keep Denon child markers ("-ARC", "-Reference Level Offset") — no space after dash
    if (/^[\-–—][A-Za-z]/.test(t)) {
      return t.replace(/^[–—]/, "-");
    }
    return t.replace(/^[\s\-–—·•\*]+/, "").trim();
  }

  function applyTheme(mode, { persist = false } = {}) {
    const m = ["system", "light", "dark"].includes(mode) ? mode : "system";
    document.documentElement.setAttribute("data-theme", m);
    state.appSettings.theme = m;
    for (const btn of document.querySelectorAll("[data-theme-set]")) {
      btn.classList.toggle("active", btn.getAttribute("data-theme-set") === m);
    }
    if (persist) {
      void persistAppSettings({ theme: m }).catch((err) =>
        setStatus(err.message, "err")
      );
    }
  }

  function initTheme() {
    applyTheme(state.appSettings.theme || "system");
    for (const btn of document.querySelectorAll("[data-theme-set]")) {
      btn.addEventListener("click", () => {
        applyTheme(btn.getAttribute("data-theme-set"), { persist: true });
        const sel = $("settings-theme");
        if (sel) sel.value = state.appSettings.theme;
      });
    }
  }

  /* ---------- In-page views + hash permalinks (#/dashboard, #/setup/menu_id, …) ---------- */

  const APP_VIEWS = new Set([
    "dashboard",
    "setup",
    "control",
    "info",
    "settings",
    "mqtt",
    "help",
  ]);

  let _routeFromCode = false;

  function parseRouteFromHash() {
    const raw = (location.hash || "").replace(/^#\/?/, "").trim();
    if (!raw) return { view: "dashboard" };
    const parts = raw.split("/").filter(Boolean);
    const view = parts[0];
    if (!APP_VIEWS.has(view)) return { view: "dashboard" };
    const route = { view };
    if (view === "setup" && parts[1]) {
      route.menuId = decodeURIComponent(parts.slice(1).join("/"));
    }
    if (view === "control" && parts[1]) {
      route.controlSection = decodeURIComponent(parts[1]);
    }
    return route;
  }

  function routeToHash(route) {
    const view = route?.view || "dashboard";
    if (view === "setup" && route.menuId) {
      return `#/setup/${encodeURIComponent(route.menuId)}`;
    }
    if (view === "control" && route.controlSection) {
      return `#/control/${encodeURIComponent(route.controlSection)}`;
    }
    return `#/${view}`;
  }

  function syncRouteToUrl({ replace = false } = {}) {
    const next = routeToHash({
      view: state.route.view,
      menuId: state.route.view === "setup" ? state.selectedMenuId : null,
      controlSection: state.route.view === "control" ? state.controlSectionId : null,
    });
    const url = `${location.pathname}${location.search}${next}`;
    if (`${location.pathname}${location.search}${location.hash}` === url) return;
    _routeFromCode = true;
    if (replace) history.replaceState({ route: next }, "", url);
    else history.pushState({ route: next }, "", url);
    queueMicrotask(() => {
      _routeFromCode = false;
    });
  }

  function findSectionForMenuId(menuId) {
    for (const section of state.menu?.sections || []) {
      for (const node of section.children || []) {
        if (node.id === menuId) return section.id;
        for (const child of node.children || []) {
          if (child.id === menuId) return section.id;
        }
      }
    }
    return null;
  }

  async function restoreRouteSubNav(route) {
    if (!route || !state.connected) return;
    if (route.view === "setup" && route.menuId) {
      const sec = findSectionForMenuId(route.menuId);
      if (sec) {
        state.sectionId = sec;
        renderSections();
        renderMenuItems();
      }
      const node = findMenuNode(route.menuId);
      if (node) await openMenuNode(node, { skipRouteSync: true });
    } else if (route.view === "control") {
      await loadControlPanel({ force: true });
      if (route.controlSection) await selectControlSection(route.controlSection, { skipRouteSync: true });
    } else if (route.view === "info") {
      await loadInfoDashboard(true);
    } else if (route.view === "dashboard") {
      await loadDashboard({ force: true });
    }
  }

  async function applyRouteFromHash() {
    if (!state.connected) return;
    const route = parseRouteFromHash();
    state.route.view = route.view;
    await showView(route.view, { loadInfo: false, skipRouteSync: true });
    await restoreRouteSubNav(route);
    syncRouteToUrl({ replace: true });
  }

  function showView(view, { loadInfo = true, skipRouteSync = false } = {}) {
    const next = APP_VIEWS.has(view) ? view : "dashboard";
    const changed = state.route.view !== next;
    const prev = state.route.view;
    state.route = { view: next };
    for (const el of document.querySelectorAll(".view")) el.hidden = true;
    const pane = $(`view-${next}`);
    if (pane) pane.hidden = false;
    $("tab-dashboard")?.classList.toggle("active", next === "dashboard");
    $("tab-setup")?.classList.toggle("active", next === "setup");
    $("tab-control")?.classList.toggle("active", next === "control");
    $("tab-info")?.classList.toggle("active", next === "info");
    $("tab-settings")?.classList.toggle("active", next === "settings");
    $("tab-mqtt")?.classList.toggle("active", next === "mqtt");
    $("tab-help")?.classList.toggle("active", next === "help");
    if (prev === "control" && next !== "control") stopControlPoll();
    let loadPromise;
    if (next === "dashboard") {
      loadPromise = loadDashboard({ force: changed || !state.dashboard });
    } else if (next === "settings") {
      loadPromise = loadSettingsPage();
    } else if (next === "mqtt") {
      loadPromise = loadMqttPage();
    } else if (next === "control") {
      loadPromise = loadControlPanel({ force: changed || !state.controlCatalog });
    } else if (
      loadInfo &&
      state.connected &&
      next === "info" &&
      (changed || !state.infoLoaded)
    ) {
      loadPromise = loadInfoDashboard();
    } else {
      loadPromise = Promise.resolve();
    }
    if (!skipRouteSync) {
      loadPromise = loadPromise.then(() => syncRouteToUrl());
    }
    return loadPromise;
  }

  function wireTabs() {
    for (const tab of document.querySelectorAll("[data-view]")) {
      tab.addEventListener("click", (ev) => {
        ev.preventDefault();
        showView(tab.getAttribute("data-view")).catch((err) =>
          setStatus(err.message, "err")
        );
      });
    }
  }

  /* ---------- Boot ---------- */

  /** Settings writes only when Main Zone is On (unless standby lock is disabled). */
  function settingsWritable() {
    if (!state.connected) return false;
    if (!state.appSettings.lock_settings_in_standby) return true;
    return state.powerOn === true;
  }

  function applyStandbySettingsLock() {
    const standby = state.powerOn === false;
    const form = $("field-form");
    if (form) {
      if (standby) {
        for (const el of form.querySelectorAll("input, select, textarea, button")) {
          el.disabled = true;
        }
      } else {
        for (const el of form.querySelectorAll("input, select, textarea, button")) {
          const wrap = el.closest(".field");
          el.disabled = Boolean(wrap?.classList.contains("is-inactive"));
        }
        applyLiveGates();
      }
    }
    for (const id of ["eq-set", "eq-curve-copy", "eq-defaults"]) {
      const btn = $(id);
      if (!btn) continue;
      btn.disabled = standby || !state.eqEnabled;
    }
    for (const id of ["eq-export", "eq-import"]) {
      const btn = $(id);
      if (btn) btn.disabled = standby;
    }
    const banner = $("editor-banner");
    if (standby && banner && state.endpointId) {
      banner.hidden = false;
      banner.textContent =
        "Main Zone is on Standby — settings are locked. Power On to make changes.";
    }
  }

  function applyPowerUi(data) {
    const on = data?.power === "on" || data?.power_on === true;
    const known =
      data?.power === "on" ||
      data?.power === "standby" ||
      data?.power_on === true ||
      data?.power_on === false;
    state.powerOn = known ? on : null;
    state.powerZone = data?.zone || "MAIN ZONE";
    state.powerInput = data?.input || "—";
    const btn = $("power-btn");
    const zone = $("power-zone");
    const input = $("power-input");
    const st = $("power-state");
    if (zone) zone.textContent = state.powerZone;
    if (input) input.textContent = state.powerInput || "—";
    if (st) {
      st.textContent =
        state.powerOn == null ? "…" : state.powerOn ? "On" : "Standby";
    }
    if (btn) {
      btn.disabled = !state.connected || state.powerBusy;
      btn.classList.toggle("is-on", state.powerOn === true);
      btn.classList.toggle("is-off", state.powerOn === false);
      btn.classList.toggle("is-busy", state.powerBusy);
      btn.setAttribute(
        "aria-pressed",
        state.powerOn == null ? "mixed" : state.powerOn ? "true" : "false"
      );
      btn.title = state.powerOn
        ? "Turn Main Zone to Standby"
        : "Turn Main Zone On";
    }
    applyStandbySettingsLock();
  }

  async function refreshPower() {
    try {
      const data = await api("/api/power");
      const wasOn = state.powerOn;
      applyPowerUi(data);
      if (wasOn === false && state.powerOn === true) {
        refreshMenuAvailability({ immediate: true }).catch(() => {});
        if (typeof state.reloadAction === "function") state.reloadAction();
      }
      return data;
    } catch (err) {
      applyPowerUi({ power: "unknown", zone: "MAIN ZONE", input: "—" });
      throw err;
    }
  }

  async function togglePower() {
    if (!state.connected || state.powerBusy) return;
    state.powerBusy = true;
    applyPowerUi({
      power: state.powerOn ? "on" : "standby",
      zone: state.powerZone,
      input: state.powerInput,
      power_on: state.powerOn,
    });
    setStatus("Sending power command…");
    try {
      const data = await api("/api/power", {
        method: "POST",
        body: JSON.stringify({ toggle: true }),
      });
      const wasOn = state.powerOn;
      applyPowerUi(data);
      markLocalWrite();
      if (data.power === "standby") {
        setStatus("Main Zone Standby — settings locked", "warn");
        applyStandbySettingsLock();
      } else {
        setStatus("Main Zone On — settings unlocked", "ok");
        if (wasOn === false) {
          refreshMenuAvailability({ immediate: true }).catch(() => {});
          if (typeof state.reloadAction === "function") state.reloadAction();
        }
      }
    } catch (err) {
      setStatus(err.message, "err");
      try {
        await refreshPower();
      } catch {
        /* ignore */
      }
    } finally {
      state.powerBusy = false;
      applyPowerUi({
        power: state.powerOn ? "on" : "standby",
        zone: state.powerZone,
        input: state.powerInput,
        power_on: state.powerOn,
      });
    }
  }

  async function boot({ preserveNav = false } = {}) {
    const urlRoute = preserveNav ? null : parseRouteFromHash();
    const prevView = preserveNav ? state.route?.view || "dashboard" : urlRoute.view;
    const prevMenuId = preserveNav ? state.selectedMenuId : urlRoute.menuId;
    const prevControlSection = preserveNav ? state.controlSectionId : urlRoute.controlSection;
    const prevReload = state.reloadAction;
    state.route = { view: prevView };
    setStatus("Loading app settings…");
    $("tabs").hidden = false;
    $("main").hidden = false;
    try {
      await refreshAppSettings();
    } catch (err) {
      setStatus(`Settings load failed: ${err.message}`, "warn");
    }
    applyTheme(state.appSettings.theme || "system");
    markAvrSyncTime({ changed: false });
    setStatus("Connecting to configured AVR…");
    try {
      const data = await api("/api/connection");
      setAvrHostLabel(data.avr_host);
      if (!data.reachable) {
        setStatus(
          `AVR not reachable. Check DENON_HOST. ${data.probe?.error || ""}`,
          "err"
        );
        state.connected = false;
        applyPowerUi({ power: "unknown", zone: "MAIN ZONE", input: "—" });
        stopRemotePolling();
        await showView("settings", { loadInfo: false });
        return;
      }
      setStatus("Connected · live updates", "ok");
      state.connected = true;
      await refreshPower().catch(() => {});
      await loadMenu();
      await showView(prevView, { loadInfo: false, skipRouteSync: true });
      if (prevView === "setup") {
        if (typeof prevReload === "function") {
          try {
            await prevReload();
          } catch (err) {
            setStatus(err.message, "err");
          }
        } else {
          await restoreRouteSubNav({
            view: "setup",
            menuId: prevMenuId,
          });
        }
      } else {
        await restoreRouteSubNav({
          view: prevView,
          controlSection: prevControlSection,
        });
      }
      syncRouteToUrl({ replace: true });
      startRemotePolling();
    } catch (err) {
      setStatus(err.message, "err");
      state.connected = false;
      stopRemotePolling();
      await showView("settings", { loadInfo: false });
    }
  }

  function markLocalWrite() {
    state.lastLocalWriteAt = Date.now();
    state.pageDirty = false;
    state.eqPendingFingerprint = null;
    state.eqPendingSince = 0;
  }

  function markPageDirty() {
    state.pageDirty = true;
    state.eqPendingFingerprint = null;
    state.eqPendingSince = 0;
  }

  function stopRemotePolling() {
    clearInterval(state.pollTimer);
    state.pollTimer = null;
    state.pollInFlight = false;
  }

  function startRemotePolling() {
    stopRemotePolling();
    if (!state.appSettings.poll_enabled) return;
    const ms = pollIntervalMs();
    // Check AVR often; Manual EQ only applies after eq_confirm_sec stable fingerprint.
    state.pollTimer = setInterval(() => {
      pollRemoteChanges().catch(() => {});
    }, ms);
  }

  function applyAppSettings(data) {
    const next = { ...DEFAULT_APP_SETTINGS, ...(data?.settings || {}) };
    state.appSettings = next;
    state.appSettingsMeta = Array.isArray(data?.meta) ? data.meta : state.appSettingsMeta;
    state.appSettingsPath = data?.path || state.appSettingsPath || "";
    if (typeof data?.exists === "boolean") {
      state.appSettingsFileExists = data.exists;
    }
    if (data?.build_channel) {
      state.buildChannel = data.build_channel === "dev" ? "dev" : "production";
    }
    applyTheme(next.theme || "system");
    syncEditModeUi();
    markAvrSyncTime({
      at: state.lastAvrCheckAt || new Date().toISOString(),
      changed: false,
    });
    if (state.connected) startRemotePolling();
    else stopRemotePolling();
  }

  async function refreshAppSettings() {
    const data = await api("/api/app-settings");
    applyAppSettings(data);
    return data;
  }

  async function persistAppSettings(partial) {
    const data = await api("/api/app-settings", {
      method: "PUT",
      body: JSON.stringify({ settings: partial }),
    });
    applyAppSettings(data);
    state.settingsDirty = false;
    return data;
  }

  function collectSettingsForm() {
    const form = $("settings-form");
    const out = {};
    if (!form) return out;
    for (const meta of state.appSettingsMeta) {
      const key = meta.key;
      const el = form.querySelector(`[name="${key}"]`);
      if (!el) continue;
      if (meta.type === "boolean") out[key] = Boolean(el.checked);
      else if (meta.type === "number") out[key] = Number(el.value);
      else out[key] = el.value;
    }
    return out;
  }

  function renderSettingsForm() {
    const form = $("settings-form");
    if (!form) return;
    const meta = state.appSettingsMeta.length
      ? state.appSettingsMeta
      : Object.keys(DEFAULT_APP_SETTINGS).map((key) => ({
          key,
          label: key,
          type: typeof DEFAULT_APP_SETTINGS[key] === "boolean" ? "boolean" : "number",
          description: "",
        }));
    const frag = document.createDocumentFragment();
    for (const item of meta) {
      const row = document.createElement("div");
      row.className = "settings-row";
      const head = document.createElement("div");
      head.className = "settings-row-head";
      const label = document.createElement("label");
      label.className = "settings-label";
      label.htmlFor = `settings-${item.key}`;
      label.textContent = item.label || item.key;
      head.appendChild(label);

      const val = state.appSettings[item.key];
      let control;
      if (item.type === "boolean") {
        control = document.createElement("input");
        control.type = "checkbox";
        control.checked = Boolean(val);
      } else if (item.type === "enum") {
        control = document.createElement("select");
        for (const opt of item.options || []) {
          const o = document.createElement("option");
          o.value = opt;
          o.textContent = opt.charAt(0).toUpperCase() + opt.slice(1);
          if (String(val) === String(opt)) o.selected = true;
          control.appendChild(o);
        }
      } else {
        control = document.createElement("input");
        control.type = "number";
        control.value = String(val ?? "");
        if (item.min != null) control.min = String(item.min);
        if (item.max != null) control.max = String(item.max);
        if (item.step != null) control.step = String(item.step);
      }
      control.id = `settings-${item.key}`;
      control.name = item.key;
      control.addEventListener("change", () => {
        state.settingsDirty = true;
      });
      head.appendChild(control);
      row.appendChild(head);
      if (item.description) {
        const desc = document.createElement("p");
        desc.className = "settings-desc";
        desc.textContent = item.description;
        row.appendChild(desc);
      }
      frag.appendChild(row);
    }
    form.innerHTML = "";
    form.appendChild(frag);
    const pathEl = $("settings-path");
    if (pathEl) {
      pathEl.textContent = state.appSettingsPath
        ? `File: ${state.appSettingsPath}${
            state.appSettingsFileExists ? "" : " (created on first Save)"
          }`
        : "";
    }
  }

  async function loadSettingsPage() {
    const banner = $("settings-banner");
    if (banner) banner.hidden = true;
    try {
      const data = await refreshAppSettings();
      renderSettingsForm();
      await renderTelnetProxyStatus();
    } catch (err) {
      if (banner) {
        banner.hidden = false;
        banner.textContent = err.message;
      }
      renderSettingsForm();
    }
  }

  async function renderTelnetProxyStatus() {
    const el = $("telnet-proxy-status");
    if (!el) return;
    try {
      const st = await api("/api/telnet-proxy/status");
      const port = st.listen_port ?? 2323;
      const baud = st.baud_rate ?? 9600;
      const configured = st.configured ?? st.enabled;
      if (!configured) {
        el.textContent =
          "Telnet proxy: disabled — enable in settings above, then Save.";
        return;
      }
      if (!st.running) {
        const err = st.last_error ? ` (${st.last_error})` : "";
        el.textContent =
          `Telnet proxy: enabled but not listening${err}. Save settings or check Docker port mapping (host → ${port}).`;
        return;
      }
      el.textContent =
        `Telnet proxy: listening on TCP port ${port} → AVR:23 | clients ${st.client_count ?? 0} | hub ${st.hub_connected ? "connected" : "offline"} | PuTTY: Raw/Telnet (not Serial), baud ${baud} ref only`;
    } catch (err) {
      el.textContent = `Telnet proxy: ${err.message}`;
    }
  }

  async function saveSettingsPage() {
    const banner = $("settings-banner");
    try {
      const prevModel = state.appSettings?.avr_model;
      const prevZ2 = state.appSettings?.show_zone2;
      const prevZ3 = state.appSettings?.show_zone3;
      const prevGrouping = state.appSettings?.control_grouping;
      await persistAppSettings(collectSettingsForm());
      renderSettingsForm();
      if (banner) {
        banner.hidden = false;
        banner.textContent = "Saved";
      }
      setStatus("Saved", "ok");
      await renderTelnetProxyStatus();
      // Reload Control Panel when model, layout, or zone visibility changes
      if (
        state.appSettings?.avr_model !== prevModel ||
        state.appSettings?.show_zone2 !== prevZ2 ||
        state.appSettings?.show_zone3 !== prevZ3 ||
        state.appSettings?.control_grouping !== prevGrouping
      ) {
        state.controlCatalog = null;
        state.controlCatalogByLayout = { less: null, more: null };
        state.controlSectionId = null;
        state.controlSectionLayout = {};
      }
    } catch (err) {
      if (banner) {
        banner.hidden = false;
        banner.textContent = err.message;
      }
      setStatus(err.message, "err");
    }
  }

  async function resetSettingsPage() {
    if (
      !window.confirm(
        "Reset all app settings to defaults and overwrite the settings file on the Docker volume?"
      )
    ) {
      return;
    }
    const banner = $("settings-banner");
    try {
      const data = await api("/api/app-settings/reset", { method: "POST" });
      applyAppSettings(data);
      renderSettingsForm();
      if (banner) {
        banner.hidden = false;
        banner.textContent = "Defaults restored.";
      }
      setStatus("App settings reset", "ok");
    } catch (err) {
      if (banner) {
        banner.hidden = false;
        banner.textContent = err.message;
      }
      setStatus(err.message, "err");
    }
  }

  /* ---------- MQTT page ---------- */

  function mqttLayoutKey() {
    const lay = state.mqttLayout || state.mqttSettings?.control_layout || "less";
    if (lay === "more" || lay === "both") return lay;
    return "less";
  }

  function mqttPublishLayout() {
    const lay = state.mqttSettings?.control_layout || "both";
    if (lay === "more" || lay === "both") return lay;
    return "less";
  }

  function ensureMqttEnabledEntities() {
    if (!state.mqttSettings) state.mqttSettings = {};
    const raw = state.mqttSettings.enabled_entities;
    if (!raw || typeof raw !== "object") {
      state.mqttSettings.enabled_entities = { less: {}, more: {} };
      return state.mqttSettings.enabled_entities;
    }
    if (Object.prototype.hasOwnProperty.call(raw, "less") || Object.prototype.hasOwnProperty.call(raw, "more")) {
      if (!raw.less) raw.less = {};
      if (!raw.more) raw.more = {};
      return raw;
    }
    state.mqttSettings.enabled_entities = { less: { ...raw }, more: {} };
    return state.mqttSettings.enabled_entities;
  }

  function mqttEnabledMap() {
    const all = ensureMqttEnabledEntities();
    const view = mqttLayoutKey();
    if (view === "both") {
      return { ...(all.less || {}), ...(all.more || {}) };
    }
    return all[view] || {};
  }

  function entityEnabledInBucket(ent) {
    const all = ensureMqttEnabledEntities();
    const bucket = ent?.source_layout === "more" ? "more" : "less";
    return Boolean((all[bucket] || {})[ent.id]);
  }

  function syncMqttEntityChecksToState() {
    const all = ensureMqttEnabledEntities();
    for (const cb of document.querySelectorAll("#mqtt-entities-list input[data-entity-id]")) {
      const id = cb.dataset.entityId;
      const bucket = cb.dataset.sourceLayout === "more" ? "more" : "less";
      if (!all[bucket]) all[bucket] = {};
      all[bucket][id] = cb.checked;
    }
  }

  function collectMqttPresetEntities() {
    syncMqttEntityChecksToState();
    const all = ensureMqttEnabledEntities();
    const entities = { less: [], more: [] };
    for (const lay of ["less", "more"]) {
      entities[lay] = Object.entries(all[lay] || {})
        .filter(([, on]) => on)
        .map(([id]) => id)
        .sort();
    }
    return entities;
  }

  function mqttField(name) {
    return document.querySelector(`#mqtt-form [name="${name}"]`);
  }

  function applyMqttForm(settings) {
    const s = settings || {};
    const enabled = mqttField("enabled");
    if (enabled) enabled.checked = Boolean(s.enabled);
    for (const key of [
      "device_name",
      "host",
      "port",
      "username",
      "password",
      "topic",
      "refresh_sec",
      "discovery_prefix",
      "tls_mode",
    ]) {
      const el = mqttField(key);
      if (!el) continue;
      el.value = s[key] != null ? String(s[key]) : "";
    }
    const jsonStyle = mqttField("json_style");
    if (jsonStyle) jsonStyle.checked = Boolean(s.json_style);
    const haDiscovery = mqttField("ha_discovery");
    if (haDiscovery) haDiscovery.checked = s.ha_discovery !== false;
    const layoutEl = mqttField("control_layout");
    const savedLayout = s.control_layout || "both";
    if (layoutEl) layoutEl.value = savedLayout;
    state.mqttLayout = savedLayout;
    syncMqttLayoutButtons();
    $("mqtt-ca-name").textContent = s.ca_cert_file || "—";
    $("mqtt-cert-name").textContent = s.client_cert_file || "—";
    $("mqtt-key-name").textContent = s.client_key_file || "—";
  }

  function collectMqttForm() {
    const num = (name, fallback) => {
      const el = mqttField(name);
      const n = Number(el?.value);
      return Number.isFinite(n) ? n : fallback;
    };
    return {
      enabled: Boolean(mqttField("enabled")?.checked),
      device_name: mqttField("device_name")?.value?.trim() || "Denon AVR",
      host: mqttField("host")?.value?.trim() || "",
      port: num("port", 1883),
      username: mqttField("username")?.value?.trim() || "",
      password: mqttField("password")?.value || "",
      topic: mqttField("topic")?.value?.trim() || "denon_avr",
      refresh_sec: num("refresh_sec", 30),
      discovery_prefix: mqttField("discovery_prefix")?.value?.trim() || "homeassistant",
      json_style: Boolean(mqttField("json_style")?.checked),
      ha_discovery: Boolean(mqttField("ha_discovery")?.checked),
      tls_mode: mqttField("tls_mode")?.value || "none",
      control_layout: mqttField("control_layout")?.value || "both",
      enabled_entities: ensureMqttEnabledEntities(),
    };
  }

  function syncMqttLayoutButtons() {
    const lay = mqttLayoutKey();
    $("mqtt-layout-less")?.classList.toggle("active", lay === "less");
    $("mqtt-layout-more")?.classList.toggle("active", lay === "more");
    $("mqtt-layout-both")?.classList.toggle("active", lay === "both");
  }

  async function loadMqttCatalog(layout) {
    const lay =
      layout === "more" || layout === "both"
        ? layout
        : layout === "less"
          ? "less"
          : mqttLayoutKey();
    state.mqttCatalog = await api(`/api/mqtt/catalog?layout=${encodeURIComponent(lay)}`);
    state.mqttLayout = lay;
    syncMqttLayoutButtons();
    if (!state.mqttSectionId && state.mqttCatalog?.sections?.length) {
      state.mqttSectionId = state.mqttCatalog.sections[0].id;
    }
    renderMqttEntities(state.mqttCatalog);
  }

  async function setMqttLayout(layout) {
    syncMqttEntityChecksToState();
    const lay = layout === "more" || layout === "both" ? layout : "less";
    state.mqttLayout = lay;
    const layoutEl = mqttField("control_layout");
    if (layoutEl) layoutEl.value = lay;
    syncMqttLayoutButtons();
    await loadMqttCatalog(lay);
    await refreshMqttExportOutput();
  }

  function renderMqttStatus(status) {
    const el = $("mqtt-status-line");
    if (!el) return;
    if (!status) {
      el.textContent = "MQTT status: —";
      return;
    }
    const parts = [];
    parts.push(status.enabled ? "enabled" : "disabled");
    if (status.enabled) {
      parts.push(status.connected ? "connected" : "disconnected");
      if (status.host) parts.push(String(status.host));
      if (status.topic) parts.push(`topic ${status.topic}`);
      if (status.last_error) parts.push(`error: ${status.last_error}`);
    }
    el.textContent = `MQTT status: ${parts.join(" · ")}`;
  }

  function renderMqttSectionNav(catalog) {
    const nav = $("mqtt-section-nav");
    if (!nav) return;
    nav.innerHTML = "";
    const sections = catalog?.sections || [];
    if (!sections.length) return;
    if (!state.mqttSectionId || !sections.some((s) => s.id === state.mqttSectionId)) {
      state.mqttSectionId = sections[0].id;
    }
    const enabled = mqttEnabledMap();
    const frag = document.createDocumentFragment();
    for (const sec of sections) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "tab" + (sec.id === state.mqttSectionId ? " active" : "");
      const items = catalog?.sections_map?.[sec.id] || [];
      const onCount = items.filter((e) =>
        catalog?.layout === "both" ? entityEnabledInBucket(e) : enabled[e.id]
      ).length;
      const label = sec.label || sec.id;
      btn.textContent = onCount > 0 ? `${label} (${onCount})` : label;
      btn.dataset.sectionId = sec.id;
      btn.addEventListener("click", () => {
        state.mqttSectionId = sec.id;
        renderMqttSectionNav(catalog);
        renderMqttEntities(catalog);
      });
      frag.appendChild(btn);
    }
    nav.appendChild(frag);
  }

  function renderMqttEntities(catalog) {
    const root = $("mqtt-entities-list");
    const meta = $("mqtt-section-meta");
    if (!root) return;
    renderMqttSectionNav(catalog);
    root.innerHTML = "";
    const sections = catalog?.sections || [];
    const sectionId = state.mqttSectionId || sections[0]?.id;
    const navSec = sections.find((s) => s.id === sectionId);
    let items = (catalog?.sections_map?.[sectionId] || []).slice();
    if (catalog?.layout === "both" && mqttLayoutKey() !== "both") {
      items = items.filter((e) => (e.source_layout || "less") === mqttLayoutKey());
    }
    const enabled = mqttEnabledMap();
    const totalOn =
      catalog?.layout === "both"
        ? (catalog.entities || []).filter((e) => entityEnabledInBucket(e)).length
        : Object.values(enabled).filter(Boolean).length;
    if (meta) {
      const model = catalog?.model || state.appSettings?.avr_model || "AVR";
      const layLabel =
        mqttLayoutKey() === "both"
          ? "both (hybrid)"
          : mqttLayoutKey() === "more"
            ? "more controls"
            : "less controls";
      const preview = state.mqttPresetPreviewId
        ? " · preset preview (Save to persist)"
        : "";
      meta.textContent = `${navSec?.label || sectionId || "—"} · ${items.length} in section · ${totalOn} enabled total · ${model} · ${layLabel}${preview}`;
    }
    if (!items.length) {
      root.innerHTML = "<p class=\"meta\">No MQTT entities in this section for the current layout.</p>";
      return;
    }
    const grid = document.createElement("div");
    grid.className = "mqtt-entity-grid";
    for (const ent of items) {
      const label = document.createElement("label");
      label.className = "mqtt-entity-item";
      const isOn =
        catalog?.layout === "both" ? entityEnabledInBucket(ent) : Boolean(enabled[ent.id]);
      label.classList.toggle("mqtt-entity-enabled", isOn);
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.dataset.entityId = ent.id;
      cb.dataset.sourceLayout = ent.source_layout || "less";
      cb.checked = isOn;
      cb.addEventListener("change", () => {
        syncMqttEntityChecksToState();
        label.classList.toggle("mqtt-entity-enabled", cb.checked);
        state.mqttPresetPreviewId = null;
        state.mqttPresetEntityLabels = {};
        state.mqttPresetRemoteRegions = [];
        renderMqttSectionNav(catalog);
      });
      label.appendChild(cb);
      const text = document.createElement("span");
      text.textContent = ent.label || ent.id;
      label.appendChild(text);
      if (catalog?.layout === "both" && ent.source_layout) {
        const srcBadge = document.createElement("span");
        srcBadge.className = "mqtt-source-badge";
        srcBadge.textContent = ent.source_layout;
        srcBadge.title = "Entity bucket (less = merged toggles, more = discrete)";
        label.appendChild(srcBadge);
      }
      const remoteLabel = state.mqttPresetEntityLabels?.[ent.id];
      if (remoteLabel) {
        const badge = document.createElement("span");
        badge.className = "mqtt-remote-badge";
        badge.textContent = remoteLabel;
        badge.title = "RC-1189 remote button";
        label.appendChild(badge);
      }
      const kind = document.createElement("small");
      kind.textContent = ent.ha_component || ent.kind || "";
      label.appendChild(kind);
      if (isOn && ent.ha_entity_id) {
        const eid = document.createElement("code");
        eid.className = "mqtt-entity-id";
        eid.textContent = ent.ha_entity_id;
        label.appendChild(eid);
      } else if (isOn && ent.ha_component) {
        const eid = document.createElement("code");
        eid.className = "mqtt-entity-id";
        eid.textContent = `${ent.ha_component}.${(state.mqttSettings?.topic || "denon_avr").replace(/\//g, "_")}_${ent.id}`;
        label.appendChild(eid);
      }
      grid.appendChild(label);
    }
    root.appendChild(grid);
  }

  function renderMqttPresetSelect() {
    const sel = $("mqtt-preset-select");
    if (!sel) return;
    const current = sel.value;
    sel.innerHTML = "";
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Choose preset…";
    sel.appendChild(placeholder);
    const builtin = (state.mqttPresets || []).filter((p) => p.builtin);
    const custom = (state.mqttPresets || []).filter((p) => !p.builtin);
    const addGroup = (label, items) => {
      if (!items.length) return;
      const grp = document.createElement("optgroup");
      grp.label = label;
      for (const p of items) {
        const opt = document.createElement("option");
        opt.value = p.id;
        const remote = p.remote ? ` (${p.remote})` : "";
        opt.textContent = `${p.label}${remote}`;
        opt.title = p.description || "";
        grp.appendChild(opt);
      }
      sel.appendChild(grp);
    };
    addGroup("Built-in", builtin);
    addGroup("Custom", custom);
    if (current && [...sel.options].some((o) => o.value === current)) {
      sel.value = current;
    }
  }

  function renderMqttCustomPresetList() {
    const list = $("mqtt-custom-preset-list");
    if (!list) return;
    list.innerHTML = "";
    const custom = (state.mqttPresets || []).filter((p) => !p.builtin);
    if (!custom.length) {
      list.innerHTML = "<li class=\"meta\">No custom presets yet — tick entities and use Save as custom.</li>";
      return;
    }
    for (const p of custom) {
      const li = document.createElement("li");
      li.className = "mqtt-custom-preset-item";
      const title = document.createElement("span");
      title.className = "mqtt-custom-preset-title";
      title.textContent = p.label;
      if (p.description) title.title = p.description;
      li.appendChild(title);
      const actions = document.createElement("span");
      actions.className = "mqtt-custom-preset-actions";
      const loadBtn = document.createElement("button");
      loadBtn.type = "button";
      loadBtn.className = "btn-ghost";
      loadBtn.textContent = "Load";
      loadBtn.addEventListener("click", () => {
        const sel = $("mqtt-preset-select");
        if (sel) sel.value = p.id;
        void previewMqttPreset(p.id);
      });
      const editBtn = document.createElement("button");
      editBtn.type = "button";
      editBtn.className = "btn-ghost";
      editBtn.textContent = "Edit";
      editBtn.addEventListener("click", () => {
        void previewMqttPreset(p.id).then(() => openMqttPresetForm(p));
      });
      const delBtn = document.createElement("button");
      delBtn.type = "button";
      delBtn.className = "btn-ghost";
      delBtn.textContent = "Delete";
      delBtn.addEventListener("click", () => deleteMqttCustomPreset(p.id));
      actions.append(loadBtn, editBtn, delBtn);
      li.appendChild(actions);
      list.appendChild(li);
    }
  }

  function toggleMqttPresetManager(show) {
    const panel = $("mqtt-preset-manager");
    state.mqttPresetManagerOpen = show ?? !state.mqttPresetManagerOpen;
    if (panel) panel.hidden = !state.mqttPresetManagerOpen;
    if (state.mqttPresetManagerOpen) renderMqttCustomPresetList();
  }

  function openMqttPresetForm(preset) {
    toggleMqttPresetManager(true);
    $("mqtt-preset-edit-id").value = preset?.id || "";
    $("mqtt-preset-name").value = preset?.label || "";
    $("mqtt-preset-desc").value = preset?.description || "";
    const remoteSel = $("mqtt-preset-remote");
    if (remoteSel) remoteSel.value = preset?.remote || "";
    if (!preset?.id) {
      const sel = $("mqtt-preset-select");
      const current = state.mqttPresets?.find((p) => p.id === sel?.value);
      if (remoteSel && current?.remote) remoteSel.value = current.remote;
    }
  }

  function resetMqttPresetForm() {
    $("mqtt-preset-edit-id").value = "";
    $("mqtt-preset-name").value = "";
    $("mqtt-preset-desc").value = "";
    const remoteSel = $("mqtt-preset-remote");
    if (remoteSel) remoteSel.value = "";
  }

  async function saveMqttCustomPreset(ev) {
    ev?.preventDefault?.();
    const editId = $("mqtt-preset-edit-id")?.value?.trim();
    const label = $("mqtt-preset-name")?.value?.trim();
    if (!label) {
      setStatus("Preset name is required", "err");
      return;
    }
    const description = $("mqtt-preset-desc")?.value?.trim() || "";
    const remote = $("mqtt-preset-remote")?.value?.trim() || null;
    const entities = collectMqttPresetEntities();
    const banner = $("mqtt-banner");
    try {
      let data;
      if (editId) {
        data = await api(`/api/mqtt/presets/custom/${encodeURIComponent(editId)}`, {
          method: "PUT",
          body: JSON.stringify({ label, description, remote, entities }),
        });
      } else {
        data = await api("/api/mqtt/presets/custom", {
          method: "POST",
          body: JSON.stringify({ label, description, remote, entities }),
        });
      }
      state.mqttPresets = data.presets || state.mqttPresets;
      renderMqttPresetSelect();
      renderMqttCustomPresetList();
      resetMqttPresetForm();
      if (data.preset?.id) {
        const sel = $("mqtt-preset-select");
        if (sel) sel.value = data.preset.id;
      }
      if (banner) {
        banner.hidden = false;
        banner.textContent = editId ? "Custom preset updated." : "Custom preset saved.";
      }
      setStatus("Preset saved", "ok");
    } catch (err) {
      if (banner) {
        banner.hidden = false;
        banner.textContent = err.message;
      }
      setStatus(err.message, "err");
    }
  }

  async function deleteMqttCustomPreset(presetId) {
    if (!window.confirm("Delete this custom preset?")) return;
    try {
      const data = await api(`/api/mqtt/presets/custom/${encodeURIComponent(presetId)}`, {
        method: "DELETE",
      });
      state.mqttPresets = data.presets || [];
      renderMqttPresetSelect();
      renderMqttCustomPresetList();
      setStatus("Preset deleted", "ok");
    } catch (err) {
      setStatus(err.message, "err");
    }
  }

  async function duplicateMqttPreset() {
    const sel = $("mqtt-preset-select");
    const presetId = sel?.value?.trim();
    if (!presetId) {
      setStatus("Choose a preset to duplicate", "err");
      return;
    }
    const label = window.prompt("Name for the copy:", "My preset (copy)");
    if (label === null) return;
    syncMqttEntityChecksToState();
    try {
      const data = await api(`/api/mqtt/presets/${encodeURIComponent(presetId)}/duplicate`, {
        method: "POST",
        body: JSON.stringify({
          label: label.trim() || undefined,
          enabled_entities: ensureMqttEnabledEntities(),
        }),
      });
      state.mqttPresets = data.presets || state.mqttPresets;
      renderMqttPresetSelect();
      renderMqttCustomPresetList();
      if (data.preset?.id) {
        if (sel) sel.value = data.preset.id;
        await previewMqttPreset(data.preset.id);
      }
      setStatus("Preset duplicated", "ok");
    } catch (err) {
      setStatus(err.message, "err");
    }
  }

  function applyPresetPreviewData(data) {
    if (!state.mqttSettings) state.mqttSettings = {};
    if (data.enabled_entities) {
      state.mqttSettings.enabled_entities = data.enabled_entities;
    } else if (data.enabled_map) {
      const all = ensureMqttEnabledEntities();
      all[mqttLayoutKey()] = { ...data.enabled_map };
    }
    state.mqttPresetPreviewId = data.preset?.id || state.mqttPresetPreviewId || "custom";
    state.mqttPresetEntityLabels = data.entity_labels || {};
    state.mqttPresetRemoteRegions = data.remote_regions || [];
    if (data.preset?.remote !== "RC-1189" && !data.entity_labels) {
      state.mqttPresetEntityLabels = {};
    }
    if (data.catalog) {
      state.mqttCatalog = data.catalog;
      renderMqttEntities(data.catalog);
    }
  }

  async function previewMqttPreset(presetId) {
    if (!presetId) {
      state.mqttPresetPreviewId = null;
      state.mqttPresetEntityLabels = {};
      state.mqttPresetRemoteRegions = [];
      return;
    }
    const banner = $("mqtt-banner");
    try {
      const data = await api(
        `/api/mqtt/presets/${encodeURIComponent(presetId)}/preview?layout=${mqttLayoutKey()}`
      );
      applyPresetPreviewData(data);
      await refreshMqttExportOutput();
      const label = data.preset?.label || presetId;
      if (banner) {
        banner.hidden = false;
        banner.textContent = `Preset loaded: ${label} (${data.enabled_count ?? 0} checked) — add more entities, then Save.`;
      }
      setStatus(`Preset preview: ${label}`, "ok");
    } catch (err) {
      if (banner) {
        banner.hidden = false;
        banner.textContent = err.message;
      }
      setStatus(err.message, "err");
    }
  }

  async function exportMqttPresetsFile() {
    try {
      const data = await api("/api/mqtt/presets/export/file");
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `denon-mqtt-presets-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      setStatus("Presets exported", "ok");
    } catch (err) {
      setStatus(err.message, "err");
    }
  }

  async function importMqttPresetsFile(file) {
    if (!file) return;
    const text = await file.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      setStatus("Invalid preset JSON file", "err");
      return;
    }
    try {
      const result = await api("/api/mqtt/presets/import/file", {
        method: "POST",
        body: JSON.stringify({ merge: true, data }),
      });
      state.mqttPresets = result.presets || state.mqttPresets;
      renderMqttPresetSelect();
      renderMqttCustomPresetList();
      setStatus(`Imported ${result.imported ?? 0} preset(s)`, "ok");
    } catch (err) {
      setStatus(err.message, "err");
    }
  }

  async function applyMqttPreset() {
    const sel = $("mqtt-preset-select");
    const presetId = sel?.value?.trim();
    if (!presetId) {
      setStatus("Choose a preset first", "err");
      return;
    }
    await previewMqttPreset(presetId);
  }

  function setMqttEntitySelection(mode) {
    const catalog = state.mqttCatalog;
    if (!catalog?.entities?.length) return;
    if (!state.mqttSettings) state.mqttSettings = {};
    const all = ensureMqttEnabledEntities();
    for (const ent of catalog.entities) {
      const bucket = ent.source_layout === "more" ? "more" : "less";
      if (!all[bucket]) all[bucket] = {};
      if (mode === "all") all[bucket][ent.id] = true;
      else if (mode === "none") all[bucket][ent.id] = false;
      else if (mode === "featured") all[bucket][ent.id] = Boolean(ent.featured);
    }
    state.mqttPresetPreviewId = null;
    state.mqttPresetEntityLabels = {};
    renderMqttEntities(catalog);
    void refreshMqttExportOutput();
  }

  function updateMqttExportUi() {
    const isLovelace = state.mqttExportMode === "lovelace";
    $("mqtt-export-mqtt")?.classList.toggle("active", !isLovelace);
    $("mqtt-export-lovelace")?.classList.toggle("active", isLovelace);
    $("mqtt-lovelace-style")?.toggleAttribute("hidden", !isLovelace);
    for (const el of document.querySelectorAll(".mqtt-mqtt-only")) {
      el.toggleAttribute("hidden", isLovelace);
    }
    const desc = $("mqtt-export-desc");
    if (desc) {
      desc.textContent = isLovelace
        ? "Lovelace YAML — RC-1189 remote, theater mode, section cards, compact bar, or entity grid."
        : "MQTT entity config JSON/YAML for manual setup (when HA Discovery is off).";
    }
  }

  async function refreshMqttExportOutput() {
    const out = $("mqtt-ha-output");
    const note = $("mqtt-export-note");
    if (!out) return;
    updateMqttExportUi();
    syncMqttEntityChecksToState();
    const exportBody = {
      layout: mqttLayoutKey(),
      enabled_entities: ensureMqttEnabledEntities(),
    };
    try {
      if (state.mqttExportMode === "lovelace") {
        const style = $("mqtt-lovelace-style")?.value || state.mqttLovelaceStyle || "rc1189";
        state.mqttLovelaceStyle = style;
        const data = await api("/api/mqtt/lovelace", {
          method: "POST",
          body: JSON.stringify({ ...exportBody, style }),
        });
        out.value = data.yaml || "";
        if (note) {
          note.textContent = data.note
            ? `${data.note} (${data.entity_count ?? 0} entities in card.)`
            : "";
        }
        return;
      }
      const fmt = state.mqttHaFormat === "yaml" ? "yaml" : "json";
      const data = await api("/api/mqtt/ha-config", {
        method: "POST",
        body: JSON.stringify({ ...exportBody, format: fmt }),
      });
      if (note) note.textContent = data.note || "";
      if (fmt === "yaml") {
        out.value = data.yaml || "";
      } else {
        out.value = JSON.stringify(data, null, 2);
      }
    } catch (err) {
      out.value = err.message;
      if (note) note.textContent = "";
    }
  }

  async function refreshMqttHaOutput() {
    return refreshMqttExportOutput();
  }

  async function loadMqttPage() {
    const banner = $("mqtt-banner");
    if (banner) banner.hidden = true;
    try {
      const settingsData = await api("/api/mqtt/settings");
      state.mqttSettings = settingsData.settings || {};
      state.mqttPresets = settingsData.presets || [];
      ensureMqttEnabledEntities();
      renderMqttPresetSelect();
      state.mqttLayout =
        state.mqttSettings.control_layout === "more"
          ? "more"
          : state.mqttSettings.control_layout === "both"
            ? "both"
            : "less";
      applyMqttForm(state.mqttSettings);
      renderMqttStatus(settingsData.status);
      await loadMqttCatalog(state.mqttLayout);
      await refreshMqttExportOutput();
    } catch (err) {
      if (banner) {
        banner.hidden = false;
        banner.textContent = err.message;
      }
    }
  }

  async function saveMqttPage() {
    const banner = $("mqtt-banner");
    try {
      syncMqttEntityChecksToState();
      const payload = collectMqttForm();
      const data = await api("/api/mqtt/settings", {
        method: "PUT",
        body: JSON.stringify({ settings: payload }),
      });
      state.mqttSettings = data.settings || payload;
      applyMqttForm(state.mqttSettings);
      renderMqttStatus(data.status);
      await loadMqttCatalog(state.mqttLayout);
      await refreshMqttExportOutput();
      if (banner) {
        banner.hidden = false;
        banner.textContent = "Saved";
      }
      state.mqttPresetPreviewId = null;
      setStatus("MQTT settings saved", "ok");
    } catch (err) {
      if (banner) {
        banner.hidden = false;
        banner.textContent = err.message;
      }
      setStatus(err.message, "err");
    }
  }

  async function resetMqttPage() {
    if (
      !window.confirm(
        "Reset all MQTT settings to defaults? Entity selections and broker config will be cleared."
      )
    ) {
      return;
    }
    const banner = $("mqtt-banner");
    try {
      const data = await api("/api/mqtt/settings/reset", { method: "POST" });
      state.mqttSettings = data.settings || {};
      applyMqttForm(state.mqttSettings);
      renderMqttStatus(data.status);
      setMqttEntitySelection("none");
      await refreshMqttExportOutput();
      if (banner) {
        banner.hidden = false;
        banner.textContent = "Defaults restored.";
      }
    } catch (err) {
      if (banner) {
        banner.hidden = false;
        banner.textContent = err.message;
      }
    }
  }

  async function testMqttConnection() {
    const banner = $("mqtt-banner");
    try {
      await saveMqttPage();
      const data = await api("/api/mqtt/test", { method: "POST" });
      renderMqttStatus(data);
      if (banner) {
        banner.hidden = false;
        banner.textContent = data.connected
          ? "Connected to MQTT broker."
          : `Connection failed: ${data.last_error || "unknown error"}`;
      }
    } catch (err) {
      if (banner) {
        banner.hidden = false;
        banner.textContent = err.message;
      }
    }
  }

  async function uploadMqttCertificate(kind, file) {
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`/api/mqtt/certificate?kind=${encodeURIComponent(kind)}`, {
      method: "POST",
      body: form,
    });
    const text = await res.text();
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = { detail: text };
    }
    if (!res.ok) {
      throw new Error(
        typeof data?.detail === "string" ? data.detail : res.statusText
      );
    }
    state.mqttSettings = data.settings || state.mqttSettings;
    applyMqttForm(state.mqttSettings);
    return data;
  }

  function wireMqttPage() {
    $("mqtt-save")?.addEventListener("click", () =>
      saveMqttPage().catch((err) => setStatus(err.message, "err"))
    );
    $("mqtt-reset")?.addEventListener("click", () =>
      resetMqttPage().catch((err) => setStatus(err.message, "err"))
    );
    $("mqtt-test")?.addEventListener("click", () =>
      testMqttConnection().catch((err) => setStatus(err.message, "err"))
    );
    $("mqtt-entities-featured")?.addEventListener("click", () =>
      setMqttEntitySelection("featured")
    );
    $("mqtt-preset-apply")?.addEventListener("click", () => applyMqttPreset());
    $("mqtt-preset-save-custom")?.addEventListener("click", () => {
      openMqttPresetForm(null);
      toggleMqttPresetManager(true);
    });
    $("mqtt-preset-duplicate")?.addEventListener("click", () =>
      duplicateMqttPreset().catch((err) => setStatus(err.message, "err"))
    );
    $("mqtt-preset-manage")?.addEventListener("click", () => toggleMqttPresetManager());
    $("mqtt-preset-form")?.addEventListener("submit", (ev) =>
      saveMqttCustomPreset(ev).catch((err) => setStatus(err.message, "err"))
    );
    $("mqtt-preset-form-cancel")?.addEventListener("click", () => {
      resetMqttPresetForm();
      toggleMqttPresetManager(false);
    });
    $("mqtt-preset-export-file")?.addEventListener("click", () =>
      exportMqttPresetsFile().catch((err) => setStatus(err.message, "err"))
    );
    $("mqtt-preset-import-file")?.addEventListener("change", (ev) => {
      const file = ev.target?.files?.[0];
      importMqttPresetsFile(file).catch((err) => setStatus(err.message, "err"));
      ev.target.value = "";
    });
    $("mqtt-preset-select")?.addEventListener("change", (ev) => {
      const id = ev.target?.value?.trim();
      if (id) void previewMqttPreset(id);
    });
    $("mqtt-export-mqtt")?.addEventListener("click", () => {
      state.mqttExportMode = "mqtt";
      updateMqttExportUi();
      void refreshMqttExportOutput();
    });
    $("mqtt-export-lovelace")?.addEventListener("click", () => {
      state.mqttExportMode = "lovelace";
      updateMqttExportUi();
      void refreshMqttExportOutput();
    });
    $("mqtt-lovelace-style")?.addEventListener("change", () => refreshMqttExportOutput());
    $("mqtt-entities-all")?.addEventListener("click", () => setMqttEntitySelection("all"));
    $("mqtt-entities-none")?.addEventListener("click", () => setMqttEntitySelection("none"));
    $("mqtt-layout-less")?.addEventListener("click", () =>
      setMqttLayout("less").catch((err) => setStatus(err.message, "err"))
    );
    $("mqtt-layout-more")?.addEventListener("click", () =>
      setMqttLayout("more").catch((err) => setStatus(err.message, "err"))
    );
    $("mqtt-layout-both")?.addEventListener("click", () =>
      setMqttLayout("both").catch((err) => setStatus(err.message, "err"))
    );
    mqttField("control_layout")?.addEventListener("change", (ev) => {
      setMqttLayout(ev.target.value).catch((err) => setStatus(err.message, "err"));
    });
    $("mqtt-ha-refresh")?.addEventListener("click", () =>
      refreshMqttExportOutput().catch((err) => setStatus(err.message, "err"))
    );
    $("mqtt-ha-format-json")?.addEventListener("click", () => {
      state.mqttHaFormat = "json";
      $("mqtt-ha-format-json")?.classList.add("active");
      $("mqtt-ha-format-yaml")?.classList.remove("active");
      refreshMqttExportOutput().catch(() => {});
    });
    $("mqtt-ha-format-yaml")?.addEventListener("click", () => {
      state.mqttHaFormat = "yaml";
      $("mqtt-ha-format-yaml")?.classList.add("active");
      $("mqtt-ha-format-json")?.classList.remove("active");
      refreshMqttExportOutput().catch(() => {});
    });
    $("mqtt-ha-copy")?.addEventListener("click", async () => {
      const text = $("mqtt-ha-output")?.value || "";
      try {
        await navigator.clipboard.writeText(text);
        setStatus("Copied HA config", "ok");
      } catch {
        $("mqtt-ha-output")?.select();
        document.execCommand("copy");
      }
    });
    const bindCert = (btnId, inputId, kind) => {
      $(btnId)?.addEventListener("click", () => $(inputId)?.click());
      $(inputId)?.addEventListener("change", (ev) => {
        const file = ev.target.files?.[0];
        uploadMqttCertificate(kind, file)
          .then(() => setStatus("Certificate uploaded", "ok"))
          .catch((err) => setStatus(err.message, "err"))
          .finally(() => {
            ev.target.value = "";
          });
      });
    };
    bindCert("mqtt-ca-upload", "mqtt-ca-file", "ca");
    bindCert("mqtt-cert-upload", "mqtt-cert-file", "cert");
    bindCert("mqtt-key-upload", "mqtt-key-file", "key");
  }

  async function softRefreshCurrentPage() {
    if (!state.endpointId || state.pageDirty) return;
    if (editorHasFocus()) return;
    if (state.endpointId === "audio_graphiceq_s_audio") {
      await softRefreshManualEq();
      return;
    }
    if (state.endpointId === "inputs_inputassign_s_inputassign") {
      await loadInputAssign();
      return;
    }
    if (
      state.selectedMenuId &&
      (INFO_ACTIONS.has(state.selectedMenuId) ||
        findMenuNode(state.selectedMenuId)?.action === "info")
    ) {
      return;
    }
    const data = await api(
      `/api/endpoints/${encodeURIComponent(state.endpointId)}/state`
    );
    if (state.pageDirty || editorHasFocus()) return;
    if (data.state?.fields) renderFields(data.state.fields);
    markAvrSyncTime({
      at: data.read_at || data.state?.read_at,
      changed: true,
    });
  }

  async function pollRemoteChanges() {
    if (!state.connected) return;
    if (document.visibilityState === "hidden") return;
    if (state.pollInFlight || state.realtimeBusy || state.eqBusy || state.eqLoading)
      return;
    const onEq = state.endpointId === "audio_graphiceq_s_audio";
    // Longer quiet window after local EQ writes so Set / channel never fights poll.
    const quietMs = onEq ? 8000 : 2500;
    if (Date.now() - state.lastLocalWriteAt < quietMs) return;
    if (["info", "settings", "mqtt", "help"].includes(state.route?.view)) return;
    if (state.route?.view === "control") {
      // Setup poll must not fight the shared telnet session. Power uses goform HTTP only.
      state.pollInFlight = true;
      try {
        if (!state.powerBusy) await refreshPower().catch(() => {});
      } finally {
        state.pollInFlight = false;
      }
      return;
    }

    state.pollInFlight = true;
    state.pollTick = (state.pollTick || 0) + 1;
    try {
      // Power is lightweight goform XML — refresh every poll tick.
      if (!state.powerBusy) {
        await refreshPower().catch(() => {});
      }
      if (!state.pageDirty) {
        await softRefreshCurrentPage();
      }
      // Menu greys ~ every 15s.
      const menuEvery = Math.max(1, Math.round(15000 / pollIntervalMs()));
      if (!onEq && state.pollTick % menuEvery === 0) {
        await refreshMenuAvailability({ immediate: true });
      }
    } catch {
      /* ignore transient poll errors */
    } finally {
      state.pollInFlight = false;
    }
  }

  async function loadMenu() {
    const data = await api("/api/menu");
    state.menu = data;
    if (!data.sections?.find((s) => s.id === state.sectionId) && data.sections?.length) {
      state.sectionId = data.sections[0].id;
    }
    renderSections();
    renderMenuItems();
    updateItemsCaption();
    if (data.context?.setup_lock) {
      setStatus("Setup Lock is On — settings frozen", "warn");
    }
  }

  /**
   * Re-scrape Denon menu greys (Restorer, Manual EQ, Front Speaker, …).
   * Debounced — live field posts can fire often; full /api/menu is relatively heavy.
   */
  async function refreshMenuAvailability(opts = {}) {
    const immediate = Boolean(opts.immediate);
    const run = async () => {
      const prevSelected = state.selectedMenuId;
      const prevSection = state.sectionId;
      await loadMenu();
      if (
        prevSection &&
        (state.menu?.sections || []).some((s) => s.id === prevSection)
      ) {
        state.sectionId = prevSection;
      }
      state.selectedMenuId = prevSelected;
      renderSections();
      renderMenuItems();
      updateItemsCaption();

      const node = findMenuNode(prevSelected);
      if (node?.inactive && node.id !== "general_lock" && state.endpointId) {
        $("editor-banner").hidden = false;
        $("editor-banner").textContent =
          cleanText(node.inactive_reason) ||
          "This item is greyed out until a required setting is enabled.";
      }
    };

    if (immediate) {
      clearTimeout(state.menuRefreshTimer);
      state.menuRefreshTimer = null;
      return run();
    }
    clearTimeout(state.menuRefreshTimer);
    return new Promise((resolve) => {
      state.menuRefreshTimer = setTimeout(() => {
        run().then(resolve).catch(resolve);
      }, 1000);
    });
  }

  async function refreshSetupLockState() {
    // Always refresh menu greys after a write; Setup Lock needs it immediately.
    const onLockPage = state.endpointId === "general_setuplock_s_general";
    await refreshMenuAvailability({ immediate: onLockPage });
    if (!onLockPage) return;
    if (state.menu?.context?.setup_lock) {
      state.sectionId = "general";
      renderSections();
      renderMenuItems();
      const lockNode = findMenuNode("general_lock");
      if (lockNode) {
        state.selectedMenuId = lockNode.id;
        renderMenuItems();
      }
      setStatus("Setup Lock is On — settings frozen", "warn");
    } else {
      setStatus("Setup Lock is Off", "ok");
    }
  }

  function currentSection() {
    return (state.menu?.sections || []).find((s) => s.id === state.sectionId);
  }

  function updateItemsCaption() {
    const section = currentSection();
    const el = $("items-caption");
    if (el) el.textContent = section ? section.label : "Items";
  }

  function renderSections() {
    const side = $("section-list");
    side.innerHTML = "";
    for (const s of state.menu?.sections || []) {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = s.label;
      b.className = s.id === state.sectionId ? "active" : "";
      b.addEventListener("click", () => {
        state.sectionId = s.id;
        state.selectedMenuId = null;
        state.endpointId = null;
        $("editor").hidden = true;
        $("editor-empty").hidden = false;
        renderSections();
        renderMenuItems();
        updateItemsCaption();
        showView("setup", { loadInfo: false }).catch(() => {});
      });
      side.appendChild(b);
    }
  }

  function isSetupInfoNode(node) {
    return (
      node.action === "setup_info" ||
      INFO_ACTIONS.has(node.action) ||
      Boolean(node.info_page) ||
      (Array.isArray(node.info_pages) && node.info_pages.length > 0)
    );
  }

  function appendMenuButton(list, node, nested = false) {
    const b = document.createElement("button");
    b.type = "button";
    const inactive = Boolean(node.inactive);
    b.className =
      (node.id === state.selectedMenuId ? "active " : "") +
      (nested ? "nested " : "") +
      (inactive ? "is-inactive" : "");
    b.title = inactive
      ? cleanText(node.inactive_reason || "Not available with current settings")
      : "";
    const locked =
      node.write_allowed === false ||
      (node.endpoint && node.endpoint.write_allowed === false);
    let badge = "";
    if (node.action === "audyssey_setup_engage") badge = "stub";
    else if (node.setup_lock_blocked) badge = "locked";
    else if (inactive) badge = "inactive";
    else if (isSetupInfoNode(node)) badge = "read-only";
    else if (locked) badge = "read-only";
    else if (node.extra) badge = "web-only";
    b.innerHTML = `${escapeHtml(node.label)}${
      badge ? `<div class="locked">${badge}</div>` : ""
    }`;
    b.addEventListener("click", () => openMenuNode(node));
    list.appendChild(b);
  }

  function renderMenuItems() {
    const list = $("endpoint-list");
    list.innerHTML = "";
    const section = currentSection();
    if (!section) {
      list.innerHTML = "<p class='status'>No section selected.</p>";
      return;
    }
    for (const node of section.children || []) {
      if (node.children?.length) {
        const group = document.createElement("div");
        group.className = "menu-group";
        const head = document.createElement("div");
        head.className = "menu-group-label";
        head.textContent = node.label;
        group.appendChild(head);
        list.appendChild(group);
        for (const child of node.children) appendMenuButton(list, child, true);
      } else {
        appendMenuButton(list, node);
      }
    }
  }

  function findMenuNode(menuId) {
    for (const section of state.menu?.sections || []) {
      for (const node of section.children || []) {
        if (node.id === menuId) return node;
        for (const child of node.children || []) {
          if (child.id === menuId) return child;
        }
      }
    }
    return null;
  }

  async function openMenuNode(node, { skipRouteSync = false } = {}) {
    try {
    const sec = findSectionForMenuId(node.id);
    if (sec && sec !== state.sectionId) {
      state.sectionId = sec;
      renderSections();
      renderMenuItems();
    }
    state.selectedMenuId = node.id;
    if (state.route.view !== "setup") {
      await showView("setup", { loadInfo: false, skipRouteSync: true });
    }

    // Setup Lock On → only Setup Lock is editable; redirect other clicks there
    if (
      state.menu?.context?.setup_lock &&
      node.id !== "general_lock" &&
      !node.children?.length
    ) {
      state.sectionId = "general";
      renderSections();
      const lockNode = findMenuNode("general_lock");
      if (lockNode && lockNode !== node) {
        setStatus("Setup Lock is On — redirected to Setup Lock", "warn");
        await openMenuNode(lockNode, { skipRouteSync: true });
        $("editor-banner").hidden = false;
        $("editor-banner").textContent =
          "Setup Lock is On. Set Lock to Off to edit other settings.";
        return;
      }
    }

    state.endpointId = node.endpoint_id || node.endpoint?.id || null;
    renderMenuItems();
    $("editor").hidden = false;
    $("editor-empty").hidden = true;
    $("field-form").innerHTML = "";
    $("action-panel").hidden = true;
    $("action-panel").innerHTML = "";
    $("editor-title").textContent = node.label;
    $("editor-meta").textContent = cleanText(node.note || "");
    $("editor-banner").hidden = true;
    syncEditorPrimaryBtn();

    if (node.inactive && node.id !== "general_lock") {
      $("editor-primary-btn").hidden = true;
      $("editor-banner").hidden = false;
      $("editor-banner").textContent =
        cleanText(node.inactive_reason) ||
        "This item is greyed out until a required setting is enabled.";
      $("field-form").innerHTML = `<p class="status">${escapeHtml(
        cleanText(node.inactive_reason) || "Not available with the current configuration."
      )}</p>`;
      return;
    }

    if (isSetupInfoNode(node)) {
      await openSetupInfo(node);
      return;
    }

    if (node.action === "audyssey_setup_engage") {
      $("editor-primary-btn").hidden = true;
      $("editor-banner").hidden = false;
      $("editor-banner").textContent =
        node.note || "Audyssey Setup wizard is never started from this API/UI.";
      const panel = $("action-panel");
      panel.hidden = false;
      panel.innerHTML = `
        <p class="action-copy">Engage is a stub only. Calibration stays on the AVR OSD / mic.</p>
        <button type="button" id="audyssey-engage" class="btn-primary">Engage stub</button>
        <p id="audyssey-status" class="status"></p>`;
      $("audyssey-engage").addEventListener("click", engageAudyssey);
      return;
    }

    if (node.action === "blocked") {
      $("editor-primary-btn").hidden = true;
      $("editor-banner").hidden = false;
      $("editor-banner").textContent = node.note || "This item is blocked.";
      return;
    }

    const eid = node.endpoint_id || node.endpoint?.id;
    if (!eid) {
      $("editor-primary-btn").hidden = true;
      $("editor-banner").hidden = false;
      $("editor-banner").textContent = node.note || "No page for this item.";
      return;
    }

    if (node.ui_hint === "manual-eq" || eid === "audio_graphiceq_s_audio") {
      await openManualEq(node);
      return;
    }

    if (node.ui_hint === "input-assign" || eid === "inputs_inputassign_s_inputassign") {
      await openInputAssign(node);
      return;
    }

    await openEndpoint(eid, node);
    } finally {
      if (!skipRouteSync) syncRouteToUrl();
    }
  }

  async function openEndpoint(id, menuNode) {
    state.endpointId = id;
    state.pageDirty = false;
    state.reloadAction = () => openEndpoint(id, menuNode);
    $("editor-title").textContent = menuNode?.label || "Loading…";
    $("field-form").innerHTML = "";
    $("action-panel").hidden = true;
    try {
      const data = await api(`/api/endpoints/${encodeURIComponent(id)}/state`);
      $("editor-title").textContent =
        menuNode?.label || cleanText(data.state?.title) || id;
      const isNetwork = NETWORK_EXPLICIT_SAVE.has(id);
      const help = PAGE_HELP[id];
      const saveMode = usesExplicitSave(id);
      $("editor-meta").textContent = help
        ? help
        : isNetwork
          ? "Explicit Save only — network will reset if you save changes (~60s)"
          : saveMode
            ? "Edit fields, then press Save"
            : "Live updates";
      const blocked =
        menuNode?.write_allowed === false || data.schema?.write_allowed === false;
      state.writeAllowed = !blocked;
      if (blocked) {
        $("editor-banner").hidden = false;
        $("editor-banner").textContent =
          cleanText(menuNode?.note || data.schema?.write_block_reason) ||
          "Writes blocked.";
      } else if (isNetwork) {
        $("editor-banner").hidden = false;
        $("editor-banner").textContent =
          cleanText(menuNode?.note) ||
          "Caution: do not Save unless you intend to change network settings. Browsing fields does not write to the AVR.";
      } else if (data.state?.page_inactive) {
        $("editor-banner").hidden = false;
        $("editor-banner").textContent =
          cleanText(data.state.page_inactive_reason) ||
          "No active controls for the current AVR configuration.";
        state.writeAllowed = false;
      } else {
        $("editor-banner").hidden = true;
      }
      renderFields(data.state?.fields || {});
      if (data.state?.page_inactive && !$("field-form").children.length) {
        $("field-form").innerHTML = `<p class="status">${escapeHtml(
          cleanText(data.state.page_inactive_reason) ||
            "This page is greyed out until a required setting / input is active."
        )}</p>`;
      }
      syncEditorPrimaryBtn();
    } catch (err) {
      $("editor-title").textContent = "Error";
      $("editor-banner").hidden = false;
      $("editor-banner").textContent = err.message;
    }
  }

  function fieldLabel(name, meta) {
    return cleanText(meta?.ui_label || meta?.label || name);
  }

  function optionLabel(opt) {
    if (opt && typeof opt === "object") {
      return cleanText(opt.display || opt.label || opt.value);
    }
    return cleanText(opt);
  }

  async function saveWithExtraFields(extra, btn) {
    if (!state.endpointId || !state.writeAllowed) return;
    if (!settingsWritable()) {
      setStatus("Main Zone Standby — settings locked", "warn");
      applyStandbySettingsLock();
      return;
    }
    if (state.realtimeBusy) return;
    const prev = btn ? btn.textContent : "";
    if (btn) {
      btn.disabled = true;
      btn.textContent = "Applying…";
    }
    state.realtimeBusy = true;
    try {
      const fields = mergeSubmitFields(extra);
      const result = await api(`/api/endpoints/${encodeURIComponent(state.endpointId)}`, {
        method: "POST",
        body: JSON.stringify({ fields, merge_defaults: true }),
      });
      setStatus("Applied", "ok");
      const afterFields = result?.after?.fields;
      if (afterFields) renderFields(afterFields);
      markLocalWrite();
      state.pageDirty = false;
      await refreshSetupLockState();
    } catch (err) {
      $("editor-banner").hidden = false;
      $("editor-banner").textContent = err.message;
      setStatus(err.message, "err");
    } finally {
      state.realtimeBusy = false;
      if (btn) {
        btn.disabled = false;
        btn.textContent = prev;
      }
    }
  }

  async function saveNetworkExplicit(kind, btn) {
    if (!state.endpointId || !state.writeAllowed) return;
    if (!settingsWritable()) {
      setStatus("Main Zone Standby — settings locked", "warn");
      applyStandbySettingsLock();
      return;
    }
    const isConnect = kind === "connect";
    const warning = isConnect
      ? "Run Connect on the AVR?\n\nThis can change Wi‑Fi association and drop your current network session."
      : "Save Network Settings to the AVR?\n\nDenon will RESET the network connection. Wait ~60 seconds, then reload.\n\nOnly continue if you intentionally changed DHCP/IP/Proxy.";
    if (state.appSettings.confirm_network_save !== false && !window.confirm(warning))
      return;
    const prev = btn.textContent;
    btn.disabled = true;
    btn.textContent = isConnect ? "Connecting…" : "Saving…";
    try {
      const result = await api(
        `/api/endpoints/${encodeURIComponent(state.endpointId)}`,
        {
          method: "POST",
          body: JSON.stringify({
            fields: collectFields(),
            merge_defaults: true,
            network_action: isConnect ? "connect" : "settings_save",
          }),
        }
      );
      setStatus(isConnect ? "Connect sent" : "Network settings saved", "ok");
      $("editor-banner").hidden = false;
      $("editor-banner").textContent = isConnect
        ? "Connect posted. If Wi‑Fi changes, wait and reload."
        : "Save posted. Wait ~60 seconds for the AVR network to return, then Reload.";
      if (result?.after?.fields) renderFields(result.after.fields);
    } catch (err) {
      $("editor-banner").hidden = false;
      $("editor-banner").textContent = err.message;
      setStatus(err.message, "err");
    } finally {
      btn.disabled = false;
      btn.textContent = prev;
    }
  }

  async function checkFirmwareUploadMode() {
    try {
      const st = await api("/api/firmware/local-upload/status");
      const ready = Boolean(st.bootloader_upload_ready);
      setStatus(
        ready ? "AVR local upload mode is ready" : "AVR not in upload mode yet",
        ready ? "ok" : "err"
      );
      $("editor-banner").hidden = false;
      $("editor-banner").textContent = ready
        ? `Bootloader upload UI active${
            st.airplay_firmware_version
              ? ` (AirPlay ${st.airplay_firmware_version})`
              : ""
          }.`
        : `Normal SETUP is ${
            st.normal_firmware_setup_available ? "available" : "unavailable"
          }. Upload will enter Web Update mode first if needed.`;
    } catch (err) {
      setStatus(err.message, "err");
      $("editor-banner").hidden = false;
      $("editor-banner").textContent = err.message;
    }
  }

  async function runLocalFirmwareUpload(fileInput, { dryRun, btn }) {
    const f = fileInput?.files?.[0];
    if (!f) {
      setStatus("Choose a firmware file first", "err");
      return;
    }
    if (!dryRun && !settingsWritable()) {
      setStatus("Main Zone Standby — settings locked", "warn");
      return;
    }
    if (!dryRun) {
      if (
        state.appSettings.confirm_firmware_actions !== false &&
        !window.confirm(
          `Upload “${f.name}” (${Math.round(f.size / 1024)} KB) to the AVR?\n\n` +
            `Use an official Denon AVR-X1200W package only. Wrong files can brick the unit.\n` +
            `Do not power off while uploading.`
        )
      ) {
        return;
      }
    }
    const prev = btn.textContent;
    btn.disabled = true;
    btn.textContent = dryRun ? "Validating…" : "Uploading…";
    $("editor-banner").hidden = true;
    try {
      const fd = new FormData();
      fd.append("file", f, f.name);
      fd.append("confirm", dryRun ? "false" : "true");
      fd.append("dry_run", dryRun ? "true" : "false");
      fd.append("enter_bootloader", "true");
      const res = await fetch("/api/firmware/local-upload", {
        method: "POST",
        body: fd,
      });
      const text = await res.text();
      let data = null;
      try {
        data = text ? JSON.parse(text) : null;
      } catch {
        data = { detail: text };
      }
      if (!res.ok) {
        const msg =
          data?.detail?.message ||
          (typeof data?.detail === "string" ? data.detail : null) ||
          data?.message ||
          res.statusText;
        throw new Error(
          typeof msg === "string" ? msg : JSON.stringify(data?.detail || msg)
        );
      }
      setStatus(
        data.dry_run
          ? `Validated ${data.filename} (${data.bytes} bytes) — not uploaded`
          : `Uploaded ${data.filename} (${data.bytes} bytes)`,
        data.uploaded || data.dry_run ? "ok" : "err"
      );
      $("editor-banner").hidden = false;
      $("editor-banner").textContent =
        cleanText(data.note || data.response_snippet || "") ||
        (data.dry_run ? "Dry run only — AVR unchanged." : "Upload sent.");
    } catch (err) {
      setStatus(err.message, "err");
      $("editor-banner").hidden = false;
      $("editor-banner").textContent = err.message;
    } finally {
      btn.disabled = false;
      btn.textContent = prev;
    }
  }

  async function runFirmwareAction(action, btn) {
    if (!settingsWritable()) {
      setStatus("Main Zone Standby — settings locked", "warn");
      return;
    }
    const labels = {
      update: "Update (check for firmware)",
      add_new_feature: "Add New Feature",
      web_update: "Web Update",
    };
    const title = labels[action] || action;
    if (
      state.appSettings.confirm_firmware_actions !== false &&
      !window.confirm(
        `Run “${title}” on the AVR?\n\nThis matches Denon’s Firmware button and may start a network check or update. Do not power off the receiver while it runs.`
      )
    ) {
      return;
    }
    const prev = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Working…";
    $("editor-banner").hidden = true;
    try {
      const result = await api(
        `/api/firmware/actions/${encodeURIComponent(action)}?confirm=true`,
        { method: "POST", body: "{}" }
      );
      const ok = result.trigger_ok || result.posted_start_flag;
      setStatus(
        ok
          ? `${title} sent to AVR`
          : `${title} finished with warnings`,
        ok ? "ok" : "err"
      );
      const snippet = cleanText(result.page_snippet || "");
      $("editor-banner").hidden = false;
      $("editor-banner").textContent = snippet
        ? `${title}: ${snippet.slice(0, 220)}`
        : result.trigger_error ||
          result.post_error ||
          `${title} triggered. Watch the AVR front display / OSD.`;
      if (result.after?.fields) renderFields(result.after.fields);
    } catch (err) {
      $("editor-banner").hidden = false;
      $("editor-banner").textContent = err.message;
      setStatus(err.message, "err");
    } finally {
      btn.disabled = false;
      btn.textContent = prev;
    }
  }

  function scheduleRealtimeApply() {
    if (!settingsWritable()) {
      applyStandbySettingsLock();
      return;
    }
    if (!state.writeAllowed || !state.endpointId) return;
    if (usesExplicitSave(state.endpointId)) {
      markPageDirty();
      applyLiveGates();
      return;
    }
    applyLiveGates();
    clearTimeout(state.realtimeTimer);
    state.realtimeTimer = setTimeout(() => saveEndpoint({ quiet: true }), 400);
  }

  function wireRealtime(el) {
    if (usesExplicitSave(state.endpointId)) {
      el.addEventListener("change", () => {
        markPageDirty();
        applyLiveGates();
      });
      if (
        el.tagName === "INPUT" &&
        (el.type === "text" || el.type === "number" || el.type === "range")
      ) {
        el.addEventListener("input", () => {
          markPageDirty();
          applyLiveGates();
        });
      }
      return;
    }
    el.addEventListener("change", scheduleRealtimeApply);
    if (
      el.tagName === "INPUT" &&
      (el.type === "text" || el.type === "number" || el.type === "range")
    ) {
      el.addEventListener("input", scheduleRealtimeApply);
    }
  }

  function renderFields(fields) {
    const form = $("field-form");
    form.innerHTML = "";
    form.classList.remove("eq-form", "assign-form");
    state.currentFields = fields;
    const names = Object.keys(fields);
    for (const name of names) {
      if (HIDDEN.has(name) || name.toLowerCase().startsWith("setbtn")) continue;
      const meta = fields[name] || {};
      if (meta.type === "hidden" || meta.type === "button" || meta.type === "submit")
        continue;

      if (meta.type === "heading" || name.startsWith("_heading_")) {
        const h = document.createElement("h3");
        h.className = "field-section-heading";
        h.textContent = fieldLabel(name, meta);
        form.appendChild(h);
        continue;
      }

      if (meta.type === "note" || name.startsWith("_note_")) {
        const note = document.createElement("div");
        note.className =
          "field-note" + (meta.note_style === "plain" ? " is-plain" : "");
        note.dataset.field = name;
        const title = document.createElement("strong");
        title.textContent = "Note:";
        note.appendChild(title);
        note.appendChild(document.createTextNode(" " + cleanText(meta.value || "")));
        form.appendChild(note);
        continue;
      }

      if (meta.type === "network_save") {
        const wrap = document.createElement("div");
        wrap.className = "field field-action";
        wrap.dataset.field = name;
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn-action";
        btn.textContent = fieldLabel(name, meta) || "Save";
        const kind = meta.network_save_kind || "settings";
        btn.addEventListener("click", () => saveNetworkExplicit(kind, btn));
        wrap.appendChild(btn);
        form.appendChild(wrap);
        continue;
      }

      if (meta.type === "firmware_upload") {
        const wrap = document.createElement("div");
        wrap.className = "field field-firmware-upload";
        wrap.dataset.field = name;
        const hint = document.createElement("p");
        hint.className = "field-inactive-hint";
        hint.textContent =
          cleanText(meta.inactive_reason) ||
          "Official Denon AVR-X1200W package only. Nothing is uploaded until you confirm.";
        wrap.appendChild(hint);
        const file = document.createElement("input");
        file.type = "file";
        file.className = "fw-file-input";
        wrap.appendChild(file);
        const row = document.createElement("div");
        row.className = "fw-upload-actions";
        const checkBtn = document.createElement("button");
        checkBtn.type = "button";
        checkBtn.className = "btn-ghost";
        checkBtn.textContent = "Check upload mode";
        checkBtn.addEventListener("click", () => checkFirmwareUploadMode());
        const dryBtn = document.createElement("button");
        dryBtn.type = "button";
        dryBtn.className = "btn-action";
        dryBtn.textContent = "Validate file only";
        dryBtn.addEventListener("click", () =>
          runLocalFirmwareUpload(file, { dryRun: true, btn: dryBtn })
        );
        const upBtn = document.createElement("button");
        upBtn.type = "button";
        upBtn.className = "btn-action";
        upBtn.textContent = fieldLabel(name, meta) || "Upload";
        upBtn.addEventListener("click", () =>
          runLocalFirmwareUpload(file, { dryRun: false, btn: upBtn })
        );
        row.appendChild(checkBtn);
        row.appendChild(dryBtn);
        row.appendChild(upBtn);
        wrap.appendChild(row);
        form.appendChild(wrap);
        continue;
      }

      if (meta.type === "action_button") {
        if (shouldHideMergedSetButton(name, meta)) {
          continue;
        }
        const wrap = document.createElement("div");
        const inactive = Boolean(meta.inactive) || Boolean(meta.disabled);
        wrap.className = "field field-action" + (inactive ? " is-inactive" : "");
        wrap.dataset.field = name;
        if (meta.inactive_reason) wrap.title = cleanText(meta.inactive_reason);
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = inactive ? "btn-blocked" : "btn-action";
        btn.textContent =
          fieldLabel(name, meta) || cleanText(meta.value) || "Action";
        btn.disabled = inactive;
        if (!inactive && meta.firmware_action) {
          btn.addEventListener("click", () =>
            runFirmwareAction(meta.firmware_action, btn)
          );
        } else if (!inactive && meta.form_post_fields) {
          btn.addEventListener("click", () =>
            saveWithExtraFields(meta.form_post_fields, btn)
          );
        }
        wrap.appendChild(btn);
        if (meta.inactive_reason) {
          const hint = document.createElement("p");
          hint.className = "field-inactive-hint";
          hint.textContent = cleanText(meta.inactive_reason);
          wrap.appendChild(hint);
        }
        form.appendChild(wrap);
        continue;
      }

      const inactive = Boolean(meta.inactive) || Boolean(meta.disabled);
      const wrap = document.createElement("div");
      wrap.className =
        "field" +
        (inactive ? " is-inactive" : "") +
        (meta.indent ? " is-indent" : "");
      wrap.dataset.field = name;
      if (inactive && meta.inactive_reason) wrap.title = cleanText(meta.inactive_reason);
      const label = document.createElement("label");
      label.textContent = fieldLabel(name, meta);
      wrap.appendChild(label);
      const type = meta.type || "text";

      if (type === "display" || name.startsWith("_zone2_") || name.startsWith("_display_") || name.startsWith("_info_")) {
        if (meta.type === "subheading" || meta.kind === "subheading") {
          const sub = document.createElement("h4");
          sub.className = "field-subheading";
          sub.textContent = fieldLabel(name, meta);
          form.appendChild(sub);
          continue;
        }
        const val = document.createElement("div");
        val.className = "field-display";
        const text = cleanText(meta.value);
        val.textContent = text || "";
        if (text) wrap.appendChild(val);
        // Label-only grey row (e.g. ZONE2 Auto Standby on Denon).
        if (inactive && meta.inactive_reason) {
          const hint = document.createElement("p");
          hint.className = "field-inactive-hint";
          hint.textContent = cleanText(meta.inactive_reason);
          wrap.appendChild(hint);
        }
        form.appendChild(wrap);
        continue;
      }

      if (meta.type === "subheading") {
        const sub = document.createElement("h4");
        sub.className = "field-subheading";
        sub.textContent = fieldLabel(name, meta);
        form.appendChild(sub);
        continue;
      }

      if (type === "radio" && Array.isArray(meta.options)) {
        const g = document.createElement("div");
        g.className =
          "radios" + (meta.layout === "vertical" ? " radios-vertical" : "");
        for (const opt of meta.options) {
          const raw = typeof opt === "object" ? opt.value : opt;
          const lab = document.createElement("label");
          const inp = document.createElement("input");
          inp.type = "radio";
          inp.name = name;
          inp.value = raw;
          if (radioOptionSelected(meta, opt, raw)) inp.checked = true;
          if (inactive && !isGateParent(name)) {
            inp.disabled = true;
          } else {
            if (name === "radioGuiFormat") {
              inp.addEventListener("change", () => {
                if (
                  !window.confirm(
                    "Change TV Format?\n\nThe network connection will reset. Wait ~60 seconds, then reload this page."
                  )
                ) {
                  // Revert to previous selection
                  for (const r of g.querySelectorAll('input[type="radio"]')) {
                    r.checked = String(r.value) === String(meta.value);
                  }
                  return;
                }
                scheduleRealtimeApply();
              });
              if (isGateParent(name)) {
                inp.addEventListener("change", () => applyLiveGates());
              }
            } else {
              wireRealtime(inp);
              if (isGateParent(name)) {
                inp.addEventListener("change", () => applyLiveGates());
              }
            }
          }
          lab.appendChild(inp);
          lab.appendChild(document.createTextNode(optionLabel(opt)));
          g.appendChild(lab);
        }
        wrap.appendChild(g);
      } else if (type === "select" && Array.isArray(meta.options)) {
        const sel = document.createElement("select");
        sel.name = name;
        sel.disabled = inactive;
        for (const opt of meta.options) {
          const o = document.createElement("option");
          o.value = opt.value ?? opt ?? "";
          o.textContent = optionLabel(opt);
          if (opt.selected || String(meta.value) === String(opt.value ?? opt)) {
            o.selected = true;
          }
          sel.appendChild(o);
        }
        if (!inactive) wireRealtime(sel);
        wrap.appendChild(sel);
      } else if (type === "range" || (type === "number" && name.startsWith("textCV"))) {
        const row = document.createElement("div");
        row.className = "level-row";
        const inp = document.createElement("input");
        inp.type = "range";
        inp.name = name;
        inp.min = meta.min != null ? String(meta.min) : "-12";
        inp.max = meta.max != null ? String(meta.max) : "12";
        inp.step = meta.step != null ? String(meta.step) : "0.5";
        inp.value = meta.value != null ? String(meta.value) : "0";
        inp.disabled = inactive;
        const val = document.createElement("span");
        val.className = "level-val";
        const unit = meta.unit || "dB";
        const sync = () => {
          // Live preview of the value that Set will push (Denon showRangeArea*).
          val.textContent = `${Number(inp.value).toFixed(1)} ${unit}`;
        };
        sync();
        inp.addEventListener("input", sync);
        // Levels / explicit-set ranges: preview only — never live-POST while dragging.
        if (!inactive && !meta.explicit_set) wireRealtime(inp);
        else if (!inactive && meta.explicit_set) {
          inp.addEventListener("input", markPageDirty);
        }
        row.appendChild(inp);
        row.appendChild(val);
        wrap.appendChild(row);
      } else {
        const row = document.createElement("div");
        row.className = "text-with-unit";
        const inp = document.createElement("input");
        inp.type = "text";
        inp.name = name;
        inp.value = meta.value ?? "";
        if (meta.max_length != null) inp.maxLength = Number(meta.max_length);
        else if (name.startsWith("textQuickSelectName")) inp.maxLength = 16;
        inp.disabled = inactive;
        if (!inactive && !meta.explicit_set) wireRealtime(inp);
        else if (!inactive && meta.explicit_set) {
          inp.addEventListener("input", markPageDirty);
        }
        row.appendChild(inp);
        if (meta.unit) {
          const u = document.createElement("span");
          u.className = "field-unit";
          u.textContent = cleanText(meta.unit);
          row.appendChild(u);
        }
        wrap.appendChild(row);
      }
      if (inactive && meta.inactive_reason) {
        const hint = document.createElement("p");
        hint.className = "field-inactive-hint";
        hint.textContent = cleanText(meta.inactive_reason);
        wrap.appendChild(hint);
      }
      form.appendChild(wrap);
    }
    if (!form.children.length) {
      form.innerHTML = "<p class='status'>No editable fields on this page.</p>";
    }
    applyLiveGates();
    applyStandbySettingsLock();
    syncPageSaveToolbar();
  }

  function isGateParent(name) {
    return [
      "radioCrossOvers",
      "radioMainPwOnLevel",
      "radioDialogLevelAdjust",
      "radioSWLevelAdjustment",
      "radioZone2VolLevel",
      "radioZone2PwOnLevel",
      "radioGraphicEQ",
      "radioNetworkSettingDHCP",
      "radioNetworkSettingProxy_OnOff",
      "radioWifi",
      "radioHdmiControl",
      "radioDynamicEq",
      "radioMainPwOnLevel",
      "radioLoudnessManagement",
    ].includes(name);
  }

  const LIVE_GATES = {
    listCrossFreqAdvFr: ["radioCrossOvers", ["IDV"]],
    listCrossFreqAdvC: ["radioCrossOvers", ["IDV"]],
    listCrossFreqAdvSr: ["radioCrossOvers", ["IDV"]],
    listCrossFreqAdvTopMiddle: ["radioCrossOvers", ["IDV"]],
    listCrossFreqAll: ["radioCrossOvers", ["ALL"]],
    textMainPwOnLevel: ["radioMainPwOnLevel", ["Level"]],
    _btn_pw_on_level_set: ["radioMainPwOnLevel", ["Level"]],
    listDialogLevelAdjust: ["radioDialogLevelAdjust", ["ON"]],
    listSWLevelAdjustment: ["radioSWLevelAdjustment", ["ON"]],
    textSWLevelAdjustment: ["radioSWLevelAdjustment", ["ON"]],
    textNetworkSettingIPAddress: ["radioNetworkSettingDHCP", ["OFF"]],
    textNetworkSettingSubnetMask: ["radioNetworkSettingDHCP", ["OFF"]],
    textNetworkSettingGateway: ["radioNetworkSettingDHCP", ["OFF"]],
    textNetworkSettingPrimaryDNS: ["radioNetworkSettingDHCP", ["OFF"]],
    textNetworkSettingSecondaryDNS: ["radioNetworkSettingDHCP", ["OFF"]],
    textNetworkSettingProxyPort: ["radioNetworkSettingProxy_OnOff", ["ADR", "NAM"]],
    radioHdmiStandbySrcControl: ["radioHdmiControl", ["ON"]],
    radioTVAudioSwitching: ["radioHdmiControl", ["ON"]],
    radioHdmiPwOffControl: ["radioHdmiControl", ["ON"]],
    radioPowerSaving: ["radioHdmiControl", ["ON"]],
    radioSmartMenu: ["radioHdmiControl", ["ON"]],
    listRefLevelOffset: ["radioDynamicEq", ["ON"]],
    radioDynamicComp: ["radioLoudnessManagement", ["ON"]],
    radioDynComp: ["radioLoudnessManagement", ["ON"]],
    listDynComp: ["radioLoudnessManagement", ["ON"]],
    listDynamicComp: ["radioLoudnessManagement", ["ON"]],
    radioDynamicCompression: ["radioLoudnessManagement", ["ON"]],
    radioDynamicRange: ["radioLoudnessManagement", ["ON"]],
    radioDynamicRangeComp: ["radioLoudnessManagement", ["ON"]],
    radioDRC: ["radioLoudnessManagement", ["ON"]],
    listDynamicRange: ["radioLoudnessManagement", ["ON"]],
  };

  function applyLiveGates() {
    const form = $("field-form");
    if (!form) return;
    const values = collectFields();
    for (const [child, [parent, allowed]] of Object.entries(LIVE_GATES)) {
      const wrap = form.querySelector(`[data-field="${child}"]`);
      if (!wrap) continue;
      const active = allowed.map(String).includes(String(values[parent] ?? ""));
      wrap.classList.toggle("is-inactive", !active);
      for (const el of wrap.querySelectorAll("input, select, textarea, button")) {
        if (!isGateParent(el.name)) el.disabled = !active;
      }
    }
  }

  function collectFields() {
    const form = $("field-form");
    const out = {};
    const fd = new FormData(form);
    for (const [k, v] of fd.entries()) out[k] = v;
    for (const inp of form.querySelectorAll('input[type="checkbox"]')) {
      if (inp.name) out[inp.name] = inp.checked ? "ON" : "OFF";
    }
    return out;
  }

  async function saveEndpoint(opts = {}) {
    if (!state.endpointId || !state.writeAllowed) return false;
    if (!settingsWritable()) {
      setStatus("Main Zone Standby — settings locked", "warn");
      applyStandbySettingsLock();
      return false;
    }
    if (state.realtimeBusy) return false;
    if (state.endpointId === "audio_graphiceq_s_audio") {
      await saveManualEq();
      return true;
    }
    if (state.endpointId === "inputs_inputassign_s_inputassign") {
      if (!isSaveEditMode() && !opts.fromPrimary) return false;
      state.realtimeBusy = true;
      try {
        const result = await api(
          `/api/endpoints/${encodeURIComponent(state.endpointId)}`,
          {
            method: "POST",
            body: JSON.stringify({
              fields: collectAssignFields(),
              merge_defaults: true,
            }),
          }
        );
        setStatus("Saved", "ok");
        if (result?.after?.fields) renderInputAssign(result.after.fields);
        else await loadInputAssign();
        markLocalWrite();
        return true;
      } catch (err) {
        $("editor-banner").hidden = false;
        $("editor-banner").textContent = err.message;
        setStatus(err.message, "err");
        return false;
      } finally {
        state.realtimeBusy = false;
      }
    }
    state.realtimeBusy = true;
    try {
      const extra = opts.fromPrimary ? primarySaveActionFields(state.endpointId) : {};
      const result = await api(`/api/endpoints/${encodeURIComponent(state.endpointId)}`, {
        method: "POST",
        body: JSON.stringify({
          fields: mergeSubmitFields(extra),
          merge_defaults: true,
        }),
      });
      setStatus(opts.quiet && !isSaveEditMode() ? "Live update" : "Saved", "ok");
      const afterFields = result?.after?.fields;
      if (afterFields) renderFields(afterFields);
      markLocalWrite();
      state.pageDirty = false;
      await refreshSetupLockState();
      syncPageSaveToolbar();
      return true;
    } catch (err) {
      $("editor-banner").hidden = false;
      $("editor-banner").textContent = err.message;
      setStatus(err.message, "err");
      return false;
    } finally {
      state.realtimeBusy = false;
    }
  }

  async function openSetupInfo(node) {
    state.endpointId = null;
    state.writeAllowed = false;
    state.reloadAction = () => openSetupInfo(node);
    syncEditorPrimaryBtn();
    $("editor-banner").hidden = true;
    $("editor-title").textContent = node.label;
    $("editor-meta").textContent = cleanText(node.note || "Read-only information");
    const form = $("field-form");
    form.classList.remove("eq-form", "assign-form");
    form.innerHTML = `<p class="status">Loading…</p>`;
    try {
      if (!state.infoLoaded || !state.infoCards.length) {
        const data = await api("/api/info/dashboard");
        state.infoCards = data.cards || [];
        state.infoLoaded = true;
      }
      // General → Information: include Firmware (as on Denon), exclude Network
      // (Network has its own Information page). Preserve info_pages order.
      const EXCLUDE_FROM_GENERAL_INFO = new Set(["network"]);
      let cards = state.infoCards;
      if (Array.isArray(node.info_pages) && node.info_pages.length) {
        const byId = new Map(state.infoCards.map((c) => [c.id, c]));
        cards = node.info_pages.map((id) => byId.get(id)).filter(Boolean);
      } else if (
        node.id === "general_info" ||
        node.info_page === "general"
      ) {
        const preferred = ["audio", "video", "zones", "firmware", "alerts"];
        const byId = new Map(state.infoCards.map((c) => [c.id, c]));
        cards = preferred
          .map((id) => byId.get(id))
          .filter((c) => c && !EXCLUDE_FROM_GENERAL_INFO.has(c.id));
        for (const c of state.infoCards) {
          if (
            !EXCLUDE_FROM_GENERAL_INFO.has(c.id) &&
            !cards.some((x) => x.id === c.id)
          ) {
            cards.push(c);
          }
        }
      } else {
        const page = node.info_page || "all";
        if (page && page !== "all") {
          cards = state.infoCards.filter((c) => c.id === page);
          if (!cards.length) cards = state.infoCards;
        }
      }
      form.innerHTML = "";
      if (!cards.length) {
        form.innerHTML = `<p class="status">No information available.</p>`;
        return;
      }
      for (const card of cards) {
        const section = document.createElement("section");
        section.className = "info-section setup-info-section";
        const h = document.createElement("h3");
        h.className = "info-heading";
        h.textContent = cleanText(card.title || card.id);
        section.appendChild(h);
        const items = card.items || [];
        if (!items.length) {
          const empty = document.createElement("p");
          empty.className = "info-empty";
          empty.textContent = "No data for this section.";
          section.appendChild(empty);
        } else {
          const list = document.createElement("div");
          list.className = "info-kv";
          for (const item of items) {
            const row = document.createElement("div");
            row.className =
              "info-kv-row" +
              (item.kind === "subheading" ? " is-subheading" : "");
            const name = document.createElement("span");
            name.className = "info-kv-name";
            name.textContent = cleanText(item.label) || "—";
            row.appendChild(name);
            if (item.kind !== "subheading") {
              const value = document.createElement("span");
              value.className = "info-kv-value";
              value.textContent = cleanText(item.value) || "—";
              row.appendChild(value);
            }
            list.appendChild(row);
          }
          section.appendChild(list);
        }
        form.appendChild(section);
      }
      setStatus("Information loaded", "ok");
    } catch (err) {
      form.innerHTML = `<p class="status err">${escapeHtml(err.message)}</p>`;
      setStatus(err.message, "err");
    }
  }

  /* ---------- Input Assign grid (Denon layout) ---------- */

  const ASSIGN_COLS = [
    { key: "hdmi", prefix: "listHdmiAssign", title: "HDMI" },
    { key: "digital", prefix: "listDigitalAssign", title: "DIGITAL" },
    { key: "analog", prefix: "listAnalogAssign", title: "ANALOG" },
    { key: "comp", prefix: "listCompAssign", title: "COMPONENT" },
    { key: "video", prefix: "listVideoAssign", title: "VIDEO" },
  ];

  const ASSIGN_SOURCE_ORDER = [
    "PHONO",
    "CD",
    "TUNER",
    "DVD",
    "BD",
    "TV",
    "SATCBL",
    "CBL",
    "SAT",
    "GAME",
    "GAME2",
    "AUX1",
    "AUX2",
    "MPLAY",
    "NET",
    "BT",
  ];

  const ASSIGN_SOURCE_NAMES = {
    BD: "Blu-ray",
    MPLAY: "Media Player",
    DVD: "DVD",
    TV: "TV Audio",
    SATCBL: "CBL/SAT",
    CBL: "CBL/SAT",
    SAT: "SAT",
    GAME: "Game",
    GAME2: "Game 2",
    AUX1: "AUX1",
    AUX2: "AUX2",
    CD: "CD",
    PHONO: "Phono",
    TUNER: "Tuner",
    NET: "Online Music",
    BT: "Bluetooth",
  };

  async function openInputAssign(node) {
    state.endpointId = "inputs_inputassign_s_inputassign";
    state.writeAllowed = true;
    state.pageDirty = false;
    state.reloadAction = () => openInputAssign(node);
    $("editor-banner").hidden = true;
    $("editor-title").textContent = "Input Assign";
    $("editor-meta").textContent = "Assigns AVR inputs to source devices by name.";
    $("action-panel").hidden = false;
    $("action-panel").innerHTML = `
      <div class="assign-toolbar">
        <button type="button" id="assign-defaults" class="btn-ghost">Set Defaults</button>
      </div>`;
    $("assign-defaults").addEventListener("click", setInputAssignDefaults);
    await loadInputAssign();
  }

  function parseAssignRows(fields) {
    const bySource = new Map();
    for (const [name, meta] of Object.entries(fields || {})) {
      for (const col of ASSIGN_COLS) {
        if (!name.startsWith(col.prefix)) continue;
        const code = name.slice(col.prefix.length);
        if (!code) continue;
        if (!bySource.has(code)) {
          bySource.set(code, {
            code,
            label: cleanText(meta.ui_label || meta.label) || ASSIGN_SOURCE_NAMES[code] || code,
            cells: {},
          });
        }
        const row = bySource.get(code);
        if ((!row.label || row.label === code) && (meta.ui_label || meta.label)) {
          row.label = cleanText(meta.ui_label || meta.label);
        }
        row.cells[col.key] = { name, meta };
      }
    }
    const rows = [...bySource.values()];
    rows.sort((a, b) => {
      const ia = ASSIGN_SOURCE_ORDER.indexOf(a.code);
      const ib = ASSIGN_SOURCE_ORDER.indexOf(b.code);
      if (ia === -1 && ib === -1) return a.label.localeCompare(b.label);
      if (ia === -1) return 1;
      if (ib === -1) return -1;
      return ia - ib;
    });
    return rows;
  }

  function activeAssignColumns(rows) {
    return ASSIGN_COLS.filter((col) => rows.some((r) => r.cells[col.key]));
  }

  function renderInputAssign(fields) {
    const form = $("field-form");
    form.classList.remove("eq-form");
    form.classList.add("assign-form");
    const rows = parseAssignRows(fields);
    const cols = activeAssignColumns(rows);
    if (!rows.length) {
      form.innerHTML = `<p class="status">No Input Assign rows from the AVR.</p>`;
      return;
    }

    const table = document.createElement("table");
    table.className = "assign-table";
    const thead = document.createElement("thead");
    const hr = document.createElement("tr");
    hr.appendChild(document.createElement("th"));
    for (const col of cols) {
      const th = document.createElement("th");
      th.textContent = col.title;
      hr.appendChild(th);
    }
    thead.appendChild(hr);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    for (const row of rows) {
      const tr = document.createElement("tr");
      const nameTd = document.createElement("th");
      nameTd.scope = "row";
      nameTd.textContent = row.label;
      tr.appendChild(nameTd);
      for (const col of cols) {
        const td = document.createElement("td");
        const cell = row.cells[col.key];
        if (!cell) {
          td.textContent = "—";
          tr.appendChild(td);
          continue;
        }
        const sel = document.createElement("select");
        sel.name = cell.name;
        sel.dataset.assignColumn = col.key;
        for (const opt of cell.meta.options || []) {
          const o = document.createElement("option");
          o.value = opt.value ?? "";
          let lab = optionLabel(opt);
          if ((!lab || lab.toLowerCase() === "off") && String(opt.value).toUpperCase() === "OFF") {
            lab = "-";
          }
          o.textContent = lab;
          if (opt.selected || String(cell.meta.value) === String(opt.value)) o.selected = true;
          sel.appendChild(o);
        }
        sel.addEventListener("change", () => {
          if (isSaveEditMode()) {
            markPageDirty();
            return;
          }
          saveInputAssignColumn(col.key);
        });
        td.appendChild(sel);
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
    table.appendChild(tbody);
    form.innerHTML = "";
    form.appendChild(table);
  }

  async function loadInputAssign() {
    try {
      const data = await api(
        `/api/endpoints/${encodeURIComponent(state.endpointId)}/state`
      );
      state.writeAllowed = data.schema?.write_allowed !== false;
      renderInputAssign(data.state?.fields || {});
      setStatus("Input Assign loaded · live", "ok");
    } catch (err) {
      $("editor-banner").hidden = false;
      $("editor-banner").textContent = err.message;
      setStatus(err.message, "err");
    }
  }

  function collectAssignFields() {
    const form = $("field-form");
    const out = {};
    for (const sel of form.querySelectorAll("select[name]")) {
      out[sel.name] = sel.value;
    }
    return out;
  }

  async function saveInputAssignColumn(column) {
    if (!state.writeAllowed || state.realtimeBusy) return;
    if (!settingsWritable()) {
      setStatus("Main Zone Standby — settings locked", "warn");
      applyStandbySettingsLock();
      return;
    }
    state.realtimeBusy = true;
    try {
      const result = await api(
        `/api/endpoints/${encodeURIComponent(state.endpointId)}`,
        {
          method: "POST",
          body: JSON.stringify({
            fields: collectAssignFields(),
            merge_defaults: true,
            assign_column: column,
          }),
        }
      );
      setStatus(`Input Assign · ${column.toUpperCase()} updated`, "ok");
      if (result?.after?.fields) renderInputAssign(result.after.fields);
      else await loadInputAssign();
      markLocalWrite();
      refreshMenuAvailability().catch(() => {});
    } catch (err) {
      $("editor-banner").hidden = false;
      $("editor-banner").textContent = err.message;
      setStatus(err.message, "err");
      await loadInputAssign();
    } finally {
      state.realtimeBusy = false;
    }
  }

  async function setInputAssignDefaults() {
    if (
      !confirm(
        "Reset Input Assign to Denon factory defaults for all sources?"
      )
    ) {
      return;
    }
    if (state.realtimeBusy) return;
    state.realtimeBusy = true;
    try {
      const result = await api(
        `/api/endpoints/${encodeURIComponent(state.endpointId)}`,
        {
          method: "POST",
          body: JSON.stringify({
            fields: {
              ...collectAssignFields(),
              defBtnInputAssign: "Set Defaults",
            },
            merge_defaults: true,
            assign_column: "defaults",
          }),
        }
      );
      setStatus("Input Assign defaults applied", "ok");
      if (result?.after?.fields) renderInputAssign(result.after.fields);
      else await loadInputAssign();
      refreshMenuAvailability().catch(() => {});
    } catch (err) {
      $("editor-banner").hidden = false;
      $("editor-banner").textContent = err.message;
      setStatus(err.message, "err");
    } finally {
      state.realtimeBusy = false;
    }
  }

  /* ---------- Manual EQ (Denon-faithful: hidden textGEQ* + Set) ---------- */

  async function openManualEq(node) {
    state.endpointId = "audio_graphiceq_s_audio";
    state.writeAllowed = true;
    state.pageDirty = false;
    state.reloadAction = () => openManualEq(node);
    $("editor-banner").hidden = true;
    $("editor-title").textContent = "Manual EQ";
    $("editor-meta").textContent =
      PAGE_HELP.audio_graphiceq_s_audio ||
      "Adjusts the tonal quality for each speaker using a graphic equalizer";
    buildManualEqForm();
    await loadManualEq();
  }

  function syncEqHiddenFromValue(label, formName, v) {
    const n = Number.isFinite(v) ? v : 0;
    const asText = n.toFixed(1);
    state.lastEqBands[label] = n;
    const hidden = document.querySelector(`input[name="${formName}"]`);
    const range = document.querySelector(`input[data-band="${label}"]`);
    const db = document.querySelector(`[data-band-db="${label}"]`);
    // Hidden textGEQ* is what Denon POSTs — treat it as the signed source of truth.
    if (hidden) hidden.value = asText;
    const signed = hidden?.value ?? asText;
    if (range) {
      const wasDisabled = range.disabled;
      range.disabled = false;
      range.value = signed;
      range.setAttribute("value", signed);
      range.disabled = wasDisabled;
    }
    if (db) db.textContent = formatDb(signed);
    return signed;
  }

  function fillEqSelect(selectEl, meta) {
    if (!selectEl || !meta || typeof meta !== "object") return;
    const opts = Array.isArray(meta.options) ? meta.options : [];
    const prev = selectEl.value;
    const want =
      meta.value != null && String(meta.value) !== ""
        ? String(meta.value)
        : prev;
    if (opts.length) {
      selectEl.innerHTML = "";
      for (const opt of opts) {
        const value =
          typeof opt === "object" ? String(opt.value ?? "").trim() : String(opt).trim();
        if (!value) continue;
        const label =
          typeof opt === "object"
            ? String(opt.label || opt.display || value).trim() || value
            : value;
        const o = document.createElement("option");
        o.value = value;
        o.textContent = label;
        selectEl.appendChild(o);
      }
    }
    if (want && [...selectEl.options].some((o) => o.value === want)) {
      selectEl.value = want;
    }
  }

  function buildManualEqForm() {
    const form = $("field-form");
    form.classList.add("eq-form");
    form.innerHTML = `
      <div class="field">
        <label>Manual EQ</label>
        <div class="radios">
          <label><input type="radio" name="radioGraphicEQ" value="ON" /><span>On</span></label>
          <label><input type="radio" name="radioGraphicEQ" value="OFF" checked /><span>Off</span></label>
        </div>
      </div>
      <div class="field" id="eq-sp-field">
        <label>Speaker Selection</label>
        <select id="eq-sp" name="listGEQSpSelection"></select>
      </div>
      <div class="field" id="eq-ch-field">
        <label>Adjust EQ</label>
        <select id="eq-channel" name="listGEQAdjustEQ"></select>
      </div>
      <div id="eq-bands" class="eq-bands is-inactive"></div>
      <div class="field field-action" id="eq-actions">
        <button type="button" class="btn-action" id="eq-set" disabled>Set</button>
        <button type="button" class="btn-action" id="eq-curve-copy" disabled>Curve Copy</button>
        <button type="button" class="btn-action" id="eq-defaults" disabled>Set Defaults</button>
      </div>
      <div class="field field-action" id="eq-backup-actions">
        <button type="button" class="btn-action" id="eq-export">Export all channels</button>
        <button type="button" class="btn-action" id="eq-import">Import…</button>
        <input type="file" id="eq-import-file" accept="application/json,.json" hidden />
      </div>
      <p id="eq-backup-msg" class="status" hidden></p>
      <p id="eq-hint" class="status">Turn Manual EQ On to activate the band sliders.</p>
      <p id="eq-sync" class="meta sync-stamp">Last AVR check: —</p>
    `;
    const bands = $("eq-bands");
    for (const [label, formName] of BANDS) {
      const d = document.createElement("div");
      d.className = "eq-band";
      const cached = Number(state.lastEqBands[label] ?? 0);
      const asText = cached.toFixed(1);
      d.innerHTML = `
        <span class="hz">${label} Hz</span>
        <input type="range" min="-20" max="6" step="0.5" value="${asText}" data-band="${label}" disabled />
        <input type="hidden" name="${formName}" value="${asText}" />
        <span class="db" data-band-db="${label}">${formatDb(asText)}</span>`;
      const range = d.querySelector("input[type='range']");
      const hidden = d.querySelector(`input[name="${formName}"]`);
      const db = d.querySelector("[data-band-db]");
      range.addEventListener("input", () => {
        // Mirror Denon showValueGEQ*: range → hidden textGEQ* (signed string).
        const v = Number(range.value);
        const text = Number.isFinite(v) ? v.toFixed(1) : "0.0";
        hidden.value = text;
        state.lastEqBands[label] = Number(text);
        db.textContent = formatDb(text);
        markPageDirty();
      });
      bands.appendChild(d);
    }
    for (const inp of form.querySelectorAll('input[name="radioGraphicEQ"]')) {
      inp.addEventListener("change", async () => {
        if (!inp.checked || state.eqLoading) return;
        const wantOn = inp.value === "ON";
        state.eqEnabled = wantOn;
        setEqControlsEnabled(wantOn);
        await applyEqEnable(wantOn);
      });
    }
    $("eq-channel").addEventListener("change", async () => {
      if (!state.eqEnabled || state.eqLoading || state.eqBusy) return;
      await selectEqChannel();
    });
    $("eq-sp").addEventListener("change", async () => {
      if (!state.eqEnabled || state.eqLoading || state.eqBusy) return;
      await selectEqChannel();
    });
    $("eq-set").addEventListener("click", () => saveManualEq());
    $("eq-curve-copy").addEventListener("click", () =>
      runManualEqAction("curve_copy")
    );
    $("eq-defaults").addEventListener("click", () =>
      runManualEqAction("set_defaults")
    );
    $("eq-export").addEventListener("click", () => exportManualEqBackup());
    $("eq-import").addEventListener("click", () => {
      const file = $("eq-import-file");
      if (file) {
        file.value = "";
        file.click();
      }
    });
    $("eq-import-file").addEventListener("change", () => importManualEqBackup());
  }

  function setEqBackupMsg(text, kind) {
    const el = $("eq-backup-msg");
    if (!el) return;
    if (!text) {
      el.hidden = true;
      el.textContent = "";
      el.classList.remove("ok", "err", "warn");
      return;
    }
    el.hidden = false;
    el.textContent = text;
    el.classList.remove("ok", "err", "warn");
    if (kind) el.classList.add(kind);
  }

  function ensureEqProgressModal() {
    let overlay = $("eq-progress-overlay");
    if (overlay) return overlay;
    overlay = document.createElement("div");
    overlay.id = "eq-progress-overlay";
    overlay.className = "eq-progress-overlay";
    overlay.hidden = true;
    overlay.innerHTML = `
      <div class="eq-progress-card" role="dialog" aria-modal="true" aria-labelledby="eq-progress-title">
        <h3 id="eq-progress-title">Working…</h3>
        <p id="eq-progress-detail" class="eq-progress-detail">Starting…</p>
        <div class="eq-progress-track" aria-hidden="true">
          <div id="eq-progress-bar" class="eq-progress-fill"></div>
        </div>
        <p id="eq-progress-pct" class="eq-progress-pct">0%</p>
        <p id="eq-progress-count" class="eq-progress-count"></p>
      </div>`;
    document.body.appendChild(overlay);
    return overlay;
  }

  function showEqProgress(title) {
    const overlay = ensureEqProgressModal();
    const t = $("eq-progress-title");
    if (t) t.textContent = title || "Working…";
    updateEqProgress({ percent: 0, message: "Starting…", current: 0, total: 0 });
    overlay.hidden = false;
    document.body.classList.add("eq-progress-open");
  }

  function updateEqProgress(evt) {
    const pct = Math.max(0, Math.min(100, Number(evt?.percent) || 0));
    const bar = $("eq-progress-bar");
    const pctEl = $("eq-progress-pct");
    const detail = $("eq-progress-detail");
    const count = $("eq-progress-count");
    if (bar) bar.style.width = `${pct}%`;
    if (pctEl) pctEl.textContent = `${pct}%`;
    if (detail) {
      const label = evt?.label || evt?.channel;
      detail.textContent =
        evt?.message ||
        (label ? `Working on ${label}…` : "Working…");
    }
    if (count) {
      const cur = Number(evt?.current);
      const tot = Number(evt?.total);
      count.textContent =
        Number.isFinite(tot) && tot > 0 && Number.isFinite(cur)
          ? `${cur} / ${tot}`
          : "";
    }
  }

  function hideEqProgress() {
    const overlay = $("eq-progress-overlay");
    if (overlay) overlay.hidden = true;
    document.body.classList.remove("eq-progress-open");
  }

  function downloadJson(filename, obj) {
    const blob = new Blob([JSON.stringify(obj, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function readNdjsonStream(res, onEvent) {
    if (!res.ok) {
      const text = await res.text();
      let data = null;
      try {
        data = text ? JSON.parse(text) : null;
      } catch {
        data = null;
      }
      const msg =
        data?.detail?.message ||
        (typeof data?.detail === "string" ? data.detail : null) ||
        data?.message ||
        text ||
        res.statusText;
      throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
    }
    if (!res.body || !res.body.getReader) {
      throw new Error("Streaming progress is not supported in this browser");
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    let finalEvent = null;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      let nl;
      while ((nl = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, nl).trim();
        buf = buf.slice(nl + 1);
        if (!line) continue;
        let evt;
        try {
          evt = JSON.parse(line);
        } catch {
          continue;
        }
        if (typeof onEvent === "function") onEvent(evt);
        if (evt?.event === "done" || evt?.event === "error") finalEvent = evt;
      }
    }
    const tail = buf.trim();
    if (tail) {
      try {
        const evt = JSON.parse(tail);
        if (typeof onEvent === "function") onEvent(evt);
        if (evt?.event === "done" || evt?.event === "error") finalEvent = evt;
      } catch {
        /* ignore trailing junk */
      }
    }
    return finalEvent;
  }

  async function exportManualEqBackup() {
    if (state.eqBusy || state.eqLoading) return;
    if (!settingsWritable()) {
      setStatus("Main Zone Standby — settings locked", "warn");
      applyStandbySettingsLock();
      return;
    }
    state.eqBusy = true;
    showEqProgress("Exporting Manual EQ");
    setEqBackupMsg("Exporting every channel from the AVR…", "warn");
    setStatus("Exporting Manual EQ…", "warn");
    try {
      const res = await fetch("/api/manual-eq/export/stream", {
        headers: { Accept: "application/x-ndjson" },
      });
      const finalEvt = await readNdjsonStream(res, (evt) => {
        if (evt?.event === "progress") updateEqProgress(evt);
        else if (evt?.event === "done") updateEqProgress({ percent: 100, message: "Finishing…" });
      });
      if (!finalEvt || finalEvt.event === "error") {
        throw new Error(finalEvt?.message || "Export failed");
      }
      const backup = finalEvt.backup || finalEvt;
      updateEqProgress({ percent: 100, message: "Download starting…", current: Object.keys(backup.channels || {}).length, total: Object.keys(backup.channels || {}).length });
      const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
      downloadJson(`denon-manual-eq-${stamp}.json`, backup);
      const n = Object.keys(backup.channels || {}).length;
      const warnN = (backup.warnings || []).length;
      const amp = backup.amp_assign?.label || backup.amp_assign?.value || "?";
      let msg = `Exported ${n} channel(s). Amp Assign: ${amp}.`;
      if (warnN) msg += ` ${warnN} channel read warning(s).`;
      setEqBackupMsg(msg, warnN ? "warn" : "ok");
      setStatus("Manual EQ exported", "ok");
    } catch (err) {
      setEqBackupMsg(err.message, "err");
      setStatus(err.message, "err");
    } finally {
      hideEqProgress();
      state.eqBusy = false;
    }
  }

  async function importManualEqBackup() {
    const fileEl = $("eq-import-file");
    const file = fileEl?.files?.[0];
    if (!file) return;
    if (state.eqBusy || state.eqLoading) return;
    if (!settingsWritable()) {
      setStatus("Main Zone Standby — settings locked", "warn");
      applyStandbySettingsLock();
      return;
    }
    let backup;
    try {
      backup = JSON.parse(await file.text());
    } catch {
      setEqBackupMsg("Invalid JSON file", "err");
      setStatus("Invalid JSON file", "err");
      return;
    }
    const chCount = Object.keys(backup.channels || {}).length;
    const ampLabel =
      backup.amp_assign?.label || backup.amp_assign?.value || "(unknown)";
    if (
      !confirm(
        `Import Manual EQ for ${chCount} channel(s)?\n\n` +
          `File Amp Assign: ${ampLabel}\n\n` +
          `Import is blocked if Amp Assign differs from the AVR.\n` +
          `Channels in the file that are not on the AVR are skipped with a warning.`
      )
    ) {
      return;
    }
    state.eqBusy = true;
    showEqProgress("Importing Manual EQ");
    setEqBackupMsg("Importing Manual EQ…", "warn");
    setStatus("Importing Manual EQ…", "warn");
    try {
      const res = await fetch("/api/manual-eq/import/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/x-ndjson",
        },
        body: JSON.stringify({ backup, dry_run: false }),
      });
      const finalEvt = await readNdjsonStream(res, (evt) => {
        if (evt?.event === "progress") updateEqProgress(evt);
        else if (evt?.event === "done") {
          updateEqProgress({
            percent: 100,
            message: evt.result?.message || "Finishing…",
          });
        }
      });
      if (!finalEvt || finalEvt.event === "error") {
        throw new Error(finalEvt?.message || "Import failed");
      }
      const result = finalEvt.result || finalEvt;
      const warnings = result.warnings || [];
      const parts = [result.message || "Import finished"];
      for (const w of warnings) {
        parts.push(w.message || `Skipped ${w.channel}`);
      }
      for (const f of result.failed || []) {
        parts.push(`Failed ${f.channel}: ${f.error}`);
      }
      const kind =
        result.ok === false || (result.failed || []).length
          ? "err"
          : warnings.length
            ? "warn"
            : "ok";
      setEqBackupMsg(parts.join(" "), kind);
      setStatus(
        result.message || "Manual EQ imported",
        kind === "err" ? "err" : "ok"
      );
      await loadManualEq();
    } catch (err) {
      setEqBackupMsg(err.message, "err");
      setStatus(err.message, "err");
    } finally {
      hideEqProgress();
      state.eqBusy = false;
      if (fileEl) fileEl.value = "";
    }
  }

  function setEqControlsEnabled(on) {
    const bands = $("eq-bands");
    if (!bands) return;
    bands.classList.toggle("is-active", on);
    bands.classList.toggle("is-inactive", !on);
    for (const input of bands.querySelectorAll("input[type='range']")) {
      input.disabled = !on;
    }
    const ch = $("eq-channel");
    const sp = $("eq-sp");
    if (ch) ch.disabled = !on;
    if (sp) sp.disabled = !on;
    const eqSet = $("eq-set");
    if (eqSet) {
      eqSet.hidden = false;
      eqSet.disabled = !on;
    }
    for (const id of ["eq-curve-copy", "eq-defaults"]) {
      const btn = $(id);
      if (btn) btn.disabled = !on;
    }
    const hint = $("eq-hint");
    if (hint) {
      hint.textContent = !on
        ? "Turn Manual EQ On to activate the band sliders."
        : "Adjust sliders, then press Set. Curve Copy / Set Defaults apply immediately.";
    }
    syncEditorPrimaryBtn();
  }

  function scheduleEqRealtime() {
    if (!state.eqEnabled || state.eqLoading) return;
    clearTimeout(state.eqTimer);
    state.eqTimer = setTimeout(() => saveManualEq(), 400);
  }

  async function postGraphicEq(fields) {
    if (!settingsWritable()) {
      throw new Error("Main Zone Standby — settings locked. Power On to change EQ.");
    }
    const result = await api(
      `/api/endpoints/${encodeURIComponent("audio_graphiceq_s_audio")}`,
      {
        method: "POST",
        body: JSON.stringify({ fields, merge_defaults: true }),
      }
    );
    markLocalWrite();
    // Manual EQ On/Off changes menu greying for related Audio items.
    refreshMenuAvailability().catch(() => {});
    return result;
  }

  async function applyEqEnable(enabled) {
    if (state.eqBusy) return;
    if (!settingsWritable()) {
      setStatus("Main Zone Standby — settings locked", "warn");
      applyStandbySettingsLock();
      for (const inp of document.querySelectorAll('input[name="radioGraphicEQ"]')) {
        inp.checked = inp.value === (state.eqEnabled ? "ON" : "OFF");
      }
      return;
    }
    state.eqBusy = true;
    try {
      await postGraphicEq({
        radioGraphicEQ: enabled ? "ON" : "OFF",
        setAdjustEQ: "off",
        setGEQCurveCopy: "off",
        setGEQSetDefaults: "off",
      });
      state.eqEnabled = enabled;
      setEqControlsEnabled(enabled);
      if (enabled) {
        await fetchEqBandsForCurrentChannel();
      }
      setStatus(enabled ? "Manual EQ On" : "Manual EQ Off", "ok");
    } catch (err) {
      $("editor-banner").hidden = false;
      $("editor-banner").textContent = err.message;
      setStatus(err.message, "err");
      for (const inp of document.querySelectorAll('input[name="radioGraphicEQ"]')) {
        inp.checked = inp.value === (state.eqEnabled ? "ON" : "OFF");
      }
      setEqControlsEnabled(state.eqEnabled);
    } finally {
      state.eqBusy = false;
    }
  }

  function parseDb(raw) {
    let s = String(raw ?? "")
      .trim()
      .replace(/[\u2013\u2014\u2212]/g, "-"); // en/em/unicode minus → ASCII
    const m = s.match(/-?\d+(?:\.\d+)?/);
    return m ? Number(m[0]) : NaN;
  }

  function parseDbSigned(raw, prev) {
    const s = String(raw ?? "")
      .trim()
      .replace(/[\u2013\u2014\u2212]/g, "-");
    const explicitNeg = /^-\s*\d/.test(s);
    const v = parseDb(s);
    if (!Number.isFinite(v)) return Number.isFinite(prev) ? prev : NaN;
    // AVR read-back sometimes drops the minus while magnitude stays the same.
    if (
      Number.isFinite(prev) &&
      prev < 0 &&
      v > 0 &&
      Math.abs(v - Math.abs(prev)) < 0.001 &&
      !explicitNeg
    ) {
      return prev;
    }
    return v;
  }

  function formatDb(n) {
    const v = parseDb(n);
    if (!Number.isFinite(v)) return "0.0 dB";
    return `${v.toFixed(1)} dB`;
  }

  function applyBandsToUi(fields, opts = {}) {
    const force = opts.force === true;
    for (const [label, formName] of BANDS) {
      const meta = fields[formName] || {};
      if (meta.value == null && typeof fields[formName] !== "string") continue;
      const raw =
        meta && typeof meta === "object" && meta.value != null
          ? meta.value
          : fields[formName];
      const hidden = document.querySelector(`input[name="${formName}"]`);
      const domVal = parseDb(hidden?.value);
      const prev = Number.isFinite(domVal) ? domVal : state.lastEqBands[label];
      const v = force ? parseDb(raw) : parseDbSigned(raw, prev);
      if (!Number.isFinite(v)) continue;
      // Don't let a background read flip sign on an already-synced negative band.
      if (
        !force &&
        Number.isFinite(domVal) &&
        domVal < 0 &&
        v > 0 &&
        Math.abs(v - Math.abs(domVal)) < 0.001
      ) {
        continue;
      }
      syncEqHiddenFromValue(label, formName, v);
    }
  }

  async function runManualEqAction(action) {
    if (!state.eqEnabled || state.eqBusy) return;
    if (!settingsWritable()) {
      setStatus("Main Zone Standby — settings locked", "warn");
      applyStandbySettingsLock();
      return;
    }
    state.eqBusy = true;
    try {
      await postGraphicEq({
        radioGraphicEQ: "ON",
        listGEQSpSelection: $("eq-sp").value,
        listGEQAdjustEQ: $("eq-channel").value,
        setAdjustEQ: "off",
        setGEQCurveCopy: action === "curve_copy" ? "Set" : "off",
        setGEQSetDefaults: action === "set_defaults" ? "Set" : "off",
      });
      setStatus(
        action === "curve_copy"
          ? "Curve Copy applied"
          : action === "set_defaults"
            ? "Defaults restored"
            : "Applied",
        "ok"
      );
      await fetchEqBandsForCurrentChannel();
    } catch (err) {
      $("editor-banner").hidden = false;
      $("editor-banner").textContent = err.message;
      setStatus(err.message, "err");
    } finally {
      state.eqBusy = false;
    }
  }

  async function selectEqChannel() {
    if (!state.eqEnabled || state.eqBusy) return;
    if (!settingsWritable()) {
      setStatus("Main Zone Standby — settings locked", "warn");
      applyStandbySettingsLock();
      return;
    }
    state.eqBusy = true;
    try {
      // Denon listBox(): POST selection without Set so AVR loads that channel's bands.
      const result = await postGraphicEq({
        radioGraphicEQ: "ON",
        listGEQSpSelection: $("eq-sp").value,
        listGEQAdjustEQ: $("eq-channel").value,
        setAdjustEQ: "off",
        setGEQCurveCopy: "off",
        setGEQSetDefaults: "off",
      });
      const fields = result?.after?.fields || {};
      if (Object.keys(fields).length) {
        applyBandsToUi(fields, { force: true });
        syncEqSelectsFromFields(fields);
        rememberEqFingerprint(fields);
      } else {
        await fetchEqBandsForCurrentChannel();
      }
      setStatus("EQ channel synced", "ok");
    } catch (err) {
      $("editor-banner").hidden = false;
      $("editor-banner").textContent = err.message;
      setStatus(err.message, "err");
      await fetchEqBandsForCurrentChannel();
    } finally {
      state.eqBusy = false;
    }
  }

  function syncEqSelectsFromFields(fields) {
    fillEqSelect($("eq-sp"), fields.listGEQSpSelection);
    fillEqSelect($("eq-channel"), fields.listGEQAdjustEQ);
  }

  function eqFingerprintFromFields(fields) {
    const on = String((fields.radioGraphicEQ || {}).value ?? "");
    const ch = String((fields.listGEQAdjustEQ || {}).value ?? "");
    const sp = String((fields.listGEQSpSelection || {}).value ?? "");
    const bands = BANDS.map(([, formName]) => {
      const meta = fields[formName];
      if (meta && typeof meta === "object" && meta.value != null) {
        return String(meta.value);
      }
      return "";
    });
    if (!bands.some((b) => b !== "")) return null;
    return [on, ch, sp, ...bands].join("|");
  }

  function eqFingerprintFromUi() {
    const on = state.eqEnabled ? "ON" : "OFF";
    const ch = $("eq-channel")?.value || "";
    const sp = $("eq-sp")?.value || "";
    const bands = BANDS.map(([label, formName]) => {
      const hidden = document.querySelector(`input[name="${formName}"]`);
      let v = parseDb(hidden?.value);
      if (!Number.isFinite(v)) v = parseDb(state.lastEqBands[label]);
      return Number.isFinite(v) ? v.toFixed(1) : "";
    });
    return [on, ch, sp, ...bands].join("|");
  }

  function rememberEqFingerprint(fields) {
    const fp = fields
      ? eqFingerprintFromFields(fields)
      : eqFingerprintFromUi();
    if (fp) {
      state.eqRemoteFingerprint = fp;
      state.eqPendingFingerprint = null;
      state.eqPendingSince = 0;
    }
  }

  function applyManualEqFields(fields, { forceBands = true } = {}) {
    const on = (fields.radioGraphicEQ || {}).value === "ON";
    state.eqEnabled = on;
    for (const inp of document.querySelectorAll('input[name="radioGraphicEQ"]')) {
      inp.checked = inp.value === (on ? "ON" : "OFF");
    }
    syncEqSelectsFromFields(fields);
    if (on && fields.textGEQ63 && fields.textGEQ63.value != null) {
      applyBandsToUi(fields, { force: forceBands });
    }
    setEqControlsEnabled(on);
    rememberEqFingerprint(fields);
  }

  /**
   * Safe remote/OSD sync for Manual EQ.
   * Polls for timestamps; applies UI only after the same new fingerprint
   * has been seen continuously for eq_confirm_sec.
   */
  async function softRefreshManualEq() {
    if (state.pageDirty || state.eqBusy || state.eqLoading) return;
    if (editorHasFocus()) return;
    if (Date.now() - state.lastLocalWriteAt < 8000) return;

    const data = await api(
      `/api/endpoints/${encodeURIComponent("audio_graphiceq_s_audio")}/state`
    );
    if (state.pageDirty || state.eqBusy || state.eqLoading) return;

    const readAt = data.read_at || data.state?.read_at;
    const fields = data.state?.fields || {};
    const fp = eqFingerprintFromFields(fields);
    if (!fp) {
      markAvrSyncTime({ at: readAt, changed: false });
      return;
    }

    if (fp === state.eqRemoteFingerprint || fp === eqFingerprintFromUi()) {
      state.eqPendingFingerprint = null;
      state.eqPendingSince = 0;
      state.eqRemoteFingerprint = fp;
      markAvrSyncTime({ at: readAt, changed: false });
      return;
    }

    const confirmMs = eqConfirmMs();
    // New or changed pending snapshot — restart the confirm window.
    if (fp !== state.eqPendingFingerprint) {
      state.eqPendingFingerprint = fp;
      state.eqPendingSince = Date.now();
      markAvrSyncTime({ at: readAt, changed: false });
      const pending = $("eq-sync");
      if (pending && state.appSettings.show_sync_timestamps !== false) {
        const secs = Math.max(1, Math.ceil(confirmMs / 1000));
        pending.textContent =
          confirmMs <= 0
            ? `Last AVR check: ${formatSyncClock(readAt)} · applying…`
            : `Last AVR check: ${formatSyncClock(readAt)} · confirming (${secs}s)…`;
      }
      if (confirmMs > 0) return;
    }

    const waited = Date.now() - (state.eqPendingSince || 0);
    if (confirmMs > 0 && waited < confirmMs) {
      markAvrSyncTime({ at: readAt, changed: false });
      const pending = $("eq-sync");
      if (pending && state.appSettings.show_sync_timestamps !== false) {
        const left = Math.max(1, Math.ceil((confirmMs - waited) / 1000));
        pending.textContent = `Last AVR check: ${formatSyncClock(readAt)} · confirming (${left}s)…`;
      }
      return;
    }

    state.eqPendingFingerprint = null;
    state.eqPendingSince = 0;
    applyManualEqFields(fields, { forceBands: true });
    markAvrSyncTime({ at: readAt, changed: true });
    setStatus("Manual EQ synced from AVR", "ok");
  }

  async function fetchEqBandsForCurrentChannel() {
    const data = await api(
      `/api/endpoints/${encodeURIComponent("audio_graphiceq_s_audio")}/state`
    );
    const fields = data.state?.fields || {};
    applyBandsToUi(fields, { force: true });
    syncEqSelectsFromFields(fields);
    rememberEqFingerprint(fields);
    markAvrSyncTime({
      at: data.read_at || data.state?.read_at,
      changed: true,
    });
    return fields;
  }

  async function loadManualEq() {
    state.eqLoading = true;
    state.eqPendingFingerprint = null;
    state.eqPendingSince = 0;
    try {
      const data = await api(
        `/api/endpoints/${encodeURIComponent("audio_graphiceq_s_audio")}/state`
      );
      const fields = data.state?.fields || {};
      const on = (fields.radioGraphicEQ || {}).value === "ON";
      state.eqEnabled = on;

      for (const inp of document.querySelectorAll('input[name="radioGraphicEQ"]')) {
        inp.checked = inp.value === (on ? "ON" : "OFF");
      }

      syncEqSelectsFromFields(fields);

      if (on && fields.textGEQ63 && fields.textGEQ63.value != null) {
        applyBandsToUi(fields, { force: true });
      } else {
        for (const [label, formName] of BANDS) {
          syncEqHiddenFromValue(label, formName, state.lastEqBands[label] ?? 0);
        }
      }
      setEqControlsEnabled(on);
      rememberEqFingerprint(on ? fields : null);
      markAvrSyncTime({
        at: data.read_at || data.state?.read_at,
        changed: true,
      });
      setStatus(on ? "Manual EQ On" : "Manual EQ Off", "ok");
      applyStandbySettingsLock();
    } catch (err) {
      $("editor-banner").hidden = false;
      $("editor-banner").textContent = err.message;
      setStatus(err.message, "err");
    } finally {
      state.eqLoading = false;
    }
  }

  async function saveManualEq(opts = {}) {
    if (state.eqBusy || state.eqLoading) return;
    if (!state.eqEnabled) return;
    if (!settingsWritable()) {
      setStatus("Main Zone Standby — settings locked", "warn");
      applyStandbySettingsLock();
      return;
    }
    state.eqBusy = true;
    try {
      // Keep hidden textGEQ* (signed strings) in sync — same pattern as Denon + Levels.
      for (const [label, formName] of BANDS) {
        const hidden = document.querySelector(`input[name="${formName}"]`);
        let v = parseDb(hidden?.value);
        if (!Number.isFinite(v)) v = parseDb(state.lastEqBands[label]);
        if (!Number.isFinite(v)) v = 0;
        syncEqHiddenFromValue(label, formName, v);
      }

      const fields = collectFields();
      fields.radioGraphicEQ = "ON";
      fields.setAdjustEQ = "Set";
      fields.setGEQCurveCopy = "off";
      fields.setGEQSetDefaults = "off";

      // Re-apply sent band values to the UI before POST (signed hidden fields).
      applyBandsToUi(
        Object.fromEntries(
          BANDS.map(([label, formName]) => [
            formName,
            { value: fields[formName] },
          ])
        )
      );

      const result = await postGraphicEq(fields);
      setStatus("EQ Set", "ok");
      // Fingerprint what we sent so the next poll does not treat it as remote drift.
      rememberEqFingerprint(null);
      markAvrSyncTime({
        at: result.read_at || result.after?.read_at,
        changed: true,
      });

      if (!opts.skipReload) {
        const after = result?.after?.fields;
        if (after) {
          syncEqSelectsFromFields(after);
          const on = (after.radioGraphicEQ || {}).value === "ON";
          state.eqEnabled = on;
          for (const inp of document.querySelectorAll(
            'input[name="radioGraphicEQ"]'
          )) {
            inp.checked = inp.value === (on ? "ON" : "OFF");
          }
          setEqControlsEnabled(on);
        }
        // Keep band sliders at what we sent — immediate read-back can drop minus signs.
        rememberEqFingerprint(null);
      }
    } catch (err) {
      $("editor-banner").hidden = false;
      $("editor-banner").textContent = err.message;
      setStatus(err.message, "err");
    } finally {
      state.eqBusy = false;
    }
  }

  async function engageAudyssey() {
    setStatus("Sending engage stub…");
    try {
      const data = await api(
        "/api/speakers/audyssey-setup/engage?confirm=true",
        { method: "POST" }
      );
      setStatus(data.message || "Engaged (wizard not started)", "ok");
      const st = $("audyssey-status");
      if (st) {
        st.textContent = data.message || "Engaged";
        st.classList.add("ok");
      }
    } catch (err) {
      setStatus(err.message, "err");
    }
  }

  /* ---------- Info (single page, all sections) ---------- */

  async function loadInfoDashboard(force = false) {
    const body = $("info-all-body");
    const note = $("info-note");
    if (!force && state.infoLoaded && state.infoCards.length) {
      renderInfoAll();
      return;
    }
    body.innerHTML = `<p class="info-empty">Loading…</p>`;
    try {
      const data = await api("/api/info/dashboard");
      state.infoCards = data.cards || [];
      state.infoLoaded = true;
      if (note) note.textContent = data.note || "Read-only status from the AVR.";
      renderInfoAll();
    } catch (err) {
      state.infoLoaded = false;
      body.innerHTML = `<p class="info-empty">${escapeHtml(err.message)}</p>`;
      if (note) note.textContent = "";
    }
  }

  function renderInfoAll() {
    const body = $("info-all-body");
    const cards = state.infoCards || [];
    if (!cards.length) {
      body.innerHTML = `<p class="info-empty">No information available.</p>`;
      return;
    }
    const frag = document.createDocumentFragment();
    for (const card of cards) {
      const section = document.createElement("section");
      section.className = "info-section";
      section.id = `info-${card.id || ""}`;

      const h = document.createElement("h3");
      h.className = "info-heading";
      h.textContent = cleanText(card.title || card.id || "Section");
      section.appendChild(h);

      const items = card.items || [];
      if (!items.length) {
        const empty = document.createElement("p");
        empty.className = "info-empty";
        empty.textContent = "No data for this section.";
        section.appendChild(empty);
      } else {
        const list = document.createElement("div");
        list.className = "info-kv";
        for (const item of items) {
          const row = document.createElement("div");
          row.className =
            "info-kv-row" + (item.kind === "subheading" ? " is-subheading" : "");
          const name = document.createElement("span");
          name.className = "info-kv-name";
          name.textContent = cleanText(item.label) || "—";
          row.appendChild(name);
          if (item.kind !== "subheading") {
            const value = document.createElement("span");
            value.className = "info-kv-value";
            value.textContent = cleanText(item.value) || "—";
            row.appendChild(value);
          }
          list.appendChild(row);
        }
        section.appendChild(list);
      }
      frag.appendChild(section);
    }
    body.innerHTML = "";
    body.appendChild(frag);
  }

  /* ---------- Control Panel (telnet) ---------- */

  function normalizeControlLayout(raw) {
    const s = String(raw || "")
      .trim()
      .toLowerCase()
      .replace(/_/g, " ");
    if (
      s === "more" ||
      s === "ungrouped" ||
      s === "more controls" ||
      s === "full"
    ) {
      return "more";
    }
    return "less";
  }

  function globalControlLayout() {
    return normalizeControlLayout(state.appSettings?.control_grouping);
  }

  function sectionControlLayout(sectionId) {
    const sid = sectionId || state.controlSectionId;
    const over = sid ? state.controlSectionLayout?.[sid] : null;
    if (over === "less" || over === "more") return over;
    return globalControlLayout();
  }

  function mappedSectionsFor(navSectionId, _targetLayout) {
    // less/more share the same section ids (full catalog sections)
    return [navSectionId];
  }

  function catalogForLayout(layout) {
    return state.controlCatalogByLayout?.[normalizeControlLayout(layout)] || null;
  }

  function controlBanner(text, kind, { sticky = false, log = true } = {}) {
    const el = $("control-banner");
    if (!el) return;
    if (!text) {
      el.hidden = true;
      el.textContent = "";
      el.classList.remove("ok", "err", "warn");
      return;
    }
    if (log) {
      pushActivity(text, kind || "info", { silent: true });
    }
    // Only surface errors / sticky progress on the page; success → activity bell.
    const show =
      sticky || kind === "err" || kind === "warn" ||
      /^(Loading AVR|Refreshing|Reading AVR|Updating|Connect)/i.test(text);
    if (!show) {
      el.hidden = true;
      el.textContent = "";
      el.classList.remove("ok", "err", "warn");
      return;
    }
    el.hidden = false;
    el.textContent = text;
    el.classList.remove("ok", "err", "warn");
    if (kind) el.classList.add(kind);
    if (state.activityBannerTimer) clearTimeout(state.activityBannerTimer);
    if (!sticky && kind !== "err") {
      state.activityBannerTimer = setTimeout(() => {
        if (el.textContent === text) {
          el.hidden = true;
          el.textContent = "";
          el.classList.remove("ok", "err", "warn");
        }
      }, 2500);
    }
  }

  function appendControlLog(entry) {
    state.controlLog.unshift(entry);
    if (state.controlLog.length > 80) state.controlLog.length = 80;
    const pre = $("control-log");
    const wrap = $("control-log-wrap");
    if (wrap) wrap.hidden = false;
    if (entry?.request) {
      const resp = (entry.responses || []).slice(0, 3).join(" | ");
      pushActivity(
        resp
          ? `${entry.request} → ${resp}`
          : String(entry.request),
        "ok",
        { silent: true }
      );
    }
    if (!pre) return;
    pre.textContent = state.controlLog
      .map((e) => {
        const resp = (e.responses || []).join(" | ") || "(no response lines)";
        return `[${e.transport || "?"}] ${e.request} → ${resp}`;
      })
      .join("\n");
  }

  function setControlTransport(name) {
    const el = $("control-transport");
    if (el) el.textContent = name ? `via ${name}` : "—";
  }

  function stopControlPoll() {
    if (state.controlPollTimer) {
      clearInterval(state.controlPollTimer);
      state.controlPollTimer = null;
    }
  }

  function startControlPoll() {
    stopControlPoll();
    // Cache-only poll — no AVR queries (protects the single telnet session).
    state.controlPollTimer = setInterval(() => {
      if (state.route.view !== "control") return;
      if (!state.controlSectionId) return;
      if (state.controlBusy) return;
      if (document.visibilityState === "hidden") return;
      refreshControlStatus({ quiet: true, refresh: false }).catch(() => {});
    }, 2000);
  }

  function controlEntity(id) {
    return state.controlEntities?.[id] || null;
  }

  function updateSectionLayoutButton() {
    const btn = $("control-section-layout");
    if (!btn || !state.controlSectionId) return;
    const effective = sectionControlLayout();
    const global = globalControlLayout();
    const overridden = effective !== global;
    if (effective === "less") {
      btn.textContent = "More +";
      btn.title =
        "Show every discrete control in this section (session only — does not change Settings)";
    } else {
      btn.textContent = "Less −";
      btn.title =
        "Collapse On/Off pairs to toggles for this section (session only — does not change Settings)";
    }
    btn.classList.toggle("is-override", overridden);
  }

  function renderControlNav() {
    const nav = $("control-section-nav");
    if (!nav || !state.controlCatalog) return;
    const sections = state.controlCatalog.sections || [];
    nav.innerHTML = "";
    for (const sec of sections) {
      const btn = document.createElement("button");
      btn.type = "button";
      const over = state.controlSectionLayout?.[sec.id];
      btn.textContent =
        over && over !== globalControlLayout()
          ? `${sec.label} · ${over === "more" ? "+" : "−"}`
          : sec.label;
      btn.dataset.section = sec.id;
      if (sec.id === state.controlSectionId) btn.classList.add("active");
      if (over && over !== globalControlLayout()) btn.classList.add("is-layout-override");
      btn.addEventListener("click", () => {
        selectControlSection(sec.id).catch((err) => controlBanner(err.message, "err"));
      });
      nav.appendChild(btn);
    }
  }

  async function selectControlSection(sectionId, { skipRouteSync = false } = {}) {
    state.controlSectionId = sectionId;
    renderControlNav();
    renderControlSectionPage();
    // Prefetched at server startup — section clicks use cache only (no AVR traffic).
    await refreshControlStatus({ quiet: true, refresh: false });
    startControlPoll();
    if (!skipRouteSync) syncRouteToUrl();
  }

  async function toggleSectionLayout() {
    if (!state.controlSectionId) return;
    const sid = state.controlSectionId;
    const current = sectionControlLayout(sid);
    const next = current === "less" ? "more" : "less";
    const global = globalControlLayout();
    if (next === global) {
      delete state.controlSectionLayout[sid];
    } else {
      state.controlSectionLayout[sid] = next;
    }
    await ensureControlCatalogs();
    renderControlNav();
    renderControlSectionPage();
    await refreshControlStatus({ quiet: false, refresh: false });
  }

  function renderControlSectionPage() {
    const editor = $("control-editor");
    const empty = $("control-empty");
    const grid = $("control-grid");
    const title = $("control-section-title");
    const meta = $("control-section-meta");
    if (!state.controlCatalog || !state.controlSectionId) {
      if (editor) editor.hidden = true;
      if (empty) empty.hidden = false;
      return;
    }
    const navSec = (state.controlCatalog.sections || []).find(
      (s) => s.id === state.controlSectionId
    );
    const layout = sectionControlLayout();
    const cat = catalogForLayout(layout) || state.controlCatalog;
    const sectionIds = mappedSectionsFor(state.controlSectionId, layout);
    const items = (cat.controls || []).filter((c) => sectionIds.includes(c.section));
    if (empty) empty.hidden = true;
    if (editor) editor.hidden = false;
    if (title) title.textContent = navSec?.label || state.controlSectionId;
    if (meta) {
      const model = state.appSettings?.avr_model || cat.model || "AVR";
      const global = globalControlLayout();
      const tag =
        layout !== global
          ? `${layout === "more" ? "more" : "less"} (this section)`
          : layout === "more"
            ? "more controls"
            : "less controls";
      meta.textContent = `${items.length} · ${model} · ${tag}`;
    }
    updateSectionLayoutButton();
    if (!grid) return;
    grid.innerHTML = "";
    grid.classList.remove("control-grid--main");
    for (const c of items) grid.appendChild(buildControlWidget(c));
    applyControlEntitiesToDom();
  }

  function buildControlWidget(c) {
    const wrap = document.createElement("div");
    wrap.className = "control-widget" + (c.featured ? " is-featured" : "");
    wrap.dataset.controlId = c.id;
    wrap.dataset.kind = c.kind || "";
    const head = document.createElement("div");
    head.className = "control-label-row";
    const label = document.createElement("label");
    label.className = "control-label";
    label.textContent = c.label;
    const cur = document.createElement("span");
    cur.className = "control-current";
    cur.dataset.role = "current";
    cur.textContent = "—";
    head.appendChild(label);
    head.appendChild(cur);
    wrap.appendChild(head);
    const kind = c.kind;
    if (kind === "toggle") {
      const row = document.createElement("div");
      row.className = "control-toggle-row";
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "control-switch";
      btn.dataset.role = "toggle";
      btn.setAttribute("aria-pressed", "false");
      const onL =
        c.on_label ||
        (String(c.id).includes("mute") ? "Muted" : "On");
      const offL =
        c.off_label ||
        (c.id === "pw_power"
          ? "Standby"
          : String(c.id).includes("mute")
            ? "Unmuted"
            : "Off");
      btn.innerHTML =
        `<span class="control-switch-off">${offL}</span>` +
        `<span class="control-switch-track" aria-hidden="true"><span class="control-switch-thumb"></span></span>` +
        `<span class="control-switch-on">${onL}</span>`;
      btn.addEventListener("click", () => {
        const ent = controlEntity(c.id);
        const currentlyOn = ent?.on === true || ent?.value === true;
        runControlCommand({
          id: c.id,
          value: !currentlyOn,
          confirm: Boolean(c.confirm),
          confirmMessage: c.confirm_message,
        });
      });
      row.appendChild(btn);
      wrap.appendChild(row);
    } else if (kind === "stepper") {
      const row = document.createElement("div");
      row.className = "control-stepper-row";
      const down = document.createElement("button");
      down.type = "button";
      down.className = "btn-ghost control-btn control-step-btn";
      down.textContent = "−";
      down.addEventListener("click", () => {
        if (c.down || c.up) {
          runControlCommand({ id: c.id, value: "down" });
          return;
        }
        const ent = controlEntity(c.id);
        const step = Number(c.step || (c.unit === "min" ? 10 : 1));
        const lo = c.min != null ? Number(c.min) : 0;
        let v = Number(ent?.value);
        if (Number.isNaN(v)) v = lo;
        runControlCommand({
          id: c.id,
          value: Math.max(lo, v - step),
          confirm: Boolean(c.confirm),
          confirmMessage: c.confirm_message,
        });
      });
      const mid = document.createElement("span");
      mid.className = "control-step-val";
      mid.dataset.role = "step-val";
      mid.textContent = "—";
      const up = document.createElement("button");
      up.type = "button";
      up.className = "btn-ghost control-btn control-step-btn";
      up.textContent = "+";
      up.addEventListener("click", () => {
        if (c.up || c.down) {
          runControlCommand({ id: c.id, value: "up" });
          return;
        }
        const ent = controlEntity(c.id);
        const step = Number(c.step || (c.unit === "min" ? 10 : 1));
        const hi = c.max != null ? Number(c.max) : 98;
        let v = Number(ent?.value);
        if (Number.isNaN(v)) v = Number(c.min || 0);
        runControlCommand({
          id: c.id,
          value: Math.min(hi, v + step),
          confirm: Boolean(c.confirm),
          confirmMessage: c.confirm_message,
        });
      });
      row.appendChild(down);
      row.appendChild(mid);
      row.appendChild(up);
      wrap.appendChild(row);
      // HA-style volume set: slider maps absolute level (0..98 ≈ −80..+18 dB)
      if (c.volume_slider || (c.featured && c.zero_db != null)) {
        const srow = document.createElement("div");
        srow.className = "control-slider-row control-volume-slider";
        const range = document.createElement("input");
        range.type = "range";
        range.min = String(c.min ?? 0);
        range.max = String(c.max ?? 98);
        range.step = "1";
        range.value = String(c.zero_db ?? 50);
        range.dataset.role = "range";
        const val = document.createElement("span");
        val.className = "control-slider-val";
        val.dataset.role = "range-val";
        const fmtDb = (n) => {
          const z = Number(c.zero_db || 80);
          return `${Number(n) - z} dB`;
        };
        val.textContent = fmtDb(range.value);
        range.addEventListener("input", () => {
          val.textContent = fmtDb(range.value);
        });
        range.addEventListener("change", () =>
          runControlCommand({
            id: c.id,
            value: Number(range.value),
            confirm: Boolean(c.confirm),
            confirmMessage: c.confirm_message,
          })
        );
        srow.appendChild(range);
        srow.appendChild(val);
        wrap.appendChild(srow);
      }
    } else if (kind === "action" || kind === "query") {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "btn-ghost control-btn";
      btn.dataset.role = "action";
      btn.textContent = kind === "query" ? "Query" : "Send";
      btn.addEventListener("click", () =>
        runControlCommand({
          id: c.id,
          confirm: Boolean(c.confirm),
          confirmMessage: c.confirm_message,
        })
      );
      wrap.appendChild(btn);
    } else if (kind === "enum") {
      const row = document.createElement("div");
      row.className = "control-enum-row";
      const sel = document.createElement("select");
      sel.className = "control-select";
      sel.dataset.role = "select";
      for (const opt of c.options || []) {
        const o = document.createElement("option");
        o.value = opt.command;
        o.textContent = opt.label;
        sel.appendChild(o);
      }
      sel.addEventListener("change", () =>
        runControlCommand({
          id: c.id,
          value: sel.value,
          confirm: Boolean(c.confirm),
          confirmMessage: c.confirm_message,
        })
      );
      row.appendChild(sel);
      wrap.appendChild(row);
    } else if (kind === "slider") {
      const row = document.createElement("div");
      row.className = "control-slider-row";
      const range = document.createElement("input");
      range.type = "range";
      range.min = String(c.min ?? 0);
      range.max = String(c.max ?? 98);
      range.step = "1";
      range.value = String(c.zero_db ?? c.min ?? 0);
      range.dataset.role = "range";
      const val = document.createElement("span");
      val.className = "control-slider-val";
      val.dataset.role = "range-val";
      val.textContent = range.value;
      range.addEventListener("input", () => {
        val.textContent = range.value;
      });
      range.addEventListener("change", () =>
        runControlCommand({
          id: c.id,
          value: Number(range.value),
          confirm: Boolean(c.confirm),
          confirmMessage: c.confirm_message,
        })
      );
      row.appendChild(range);
      row.appendChild(val);
      wrap.appendChild(row);
    } else if (kind === "raw") {
      const row = document.createElement("div");
      row.className = "control-raw-row";
      const input = document.createElement("input");
      input.type = "text";
      input.className = "control-raw-input";
      input.placeholder = "e.g. MV80 or MSSTEREO";
      input.maxLength = 40;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "btn-primary control-btn";
      btn.textContent = "Send";
      btn.addEventListener("click", () => {
        const cmd = input.value.trim();
        if (!cmd) return;
        runControlCommand({
          command: cmd,
          allow_raw: true,
          confirm: true,
          confirmMessage: `Send raw command ${cmd}?`,
        });
      });
      row.appendChild(input);
      row.appendChild(btn);
      wrap.appendChild(row);
    }
    return wrap;
  }

  function applyControlEntitiesToDom() {
    const roots = [
      $("control-grid"),
      $("dashboard-sections"),
    ].filter(Boolean);
    if (!roots.length) return;
    const widgets = [];
    for (const root of roots) {
      widgets.push(...root.querySelectorAll(".control-widget"));
    }
    for (const wrap of widgets) {
      const id = wrap.dataset.controlId;
      const ent = controlEntity(id);
      const cur = wrap.querySelector('[data-role="current"]');
      const sel = wrap.querySelector('[data-role="select"]');
      const range = wrap.querySelector('[data-role="range"]');
      const rangeVal = wrap.querySelector('[data-role="range-val"]');
      const stepVal = wrap.querySelector('[data-role="step-val"]');
      const toggle = wrap.querySelector('[data-role="toggle"]');
      const action = wrap.querySelector('[data-role="action"]');
      const inactive = Boolean(ent?.inactive);
      const hasValue = Boolean(
        ent && !inactive && (ent.display || ent.raw || ent.value != null || ent.on != null)
      );
      wrap.classList.toggle("is-current", hasValue || Boolean(ent?.active));
      wrap.classList.toggle("is-inactive", inactive);
      if (cur) {
        if (wrap.dataset.kind === "toggle" || wrap.dataset.kind === "stepper") {
          cur.textContent = "";
          cur.classList.remove("has-value");
        } else if (ent?.display) {
          cur.textContent = ent.display;
          cur.title = ent.raw || ent.command || "";
          cur.classList.add("has-value");
        } else if (ent?.raw) {
          cur.textContent = ent.raw;
          cur.classList.add("has-value");
        } else {
          cur.textContent = "—";
          cur.classList.remove("has-value");
        }
      }
      if (toggle) {
        const on = ent?.on === true || ent?.value === true;
        toggle.classList.toggle("is-on", on);
        toggle.classList.toggle("is-off", ent && !on && !inactive);
        toggle.setAttribute("aria-pressed", on ? "true" : "false");
      }
      const iconHost =
        wrap.querySelector('[data-role="dash-icon"]') ||
        wrap.closest?.(".dashboard-widget")?.querySelector('[data-role="dash-icon"]');
      if (iconHost) {
        const on =
          wrap.dataset.kind === "toggle"
            ? ent?.on === true || ent?.value === true
            : Boolean(ent && !inactive && (ent.on === true || ent.active || ent.value));
        iconHost.classList.toggle("is-on", on);
        iconHost.classList.toggle("is-off", !on);
      }
      if (stepVal) {
        stepVal.textContent = ent?.display || (ent?.value != null ? String(ent.value) : "—");
      }
      if (sel && ent?.command && document.activeElement !== sel) {
        const opt = [...sel.options].find((o) => o.value === ent.command);
        if (opt) sel.value = ent.command;
      }
      if (range && ent?.value != null && !Number.isNaN(Number(ent.value))) {
        if (document.activeElement !== range) {
          range.value = String(ent.value);
          if (rangeVal) rangeVal.textContent = String(ent.value);
        }
      }
      if (action) action.classList.toggle("is-active", Boolean(ent?.active));
      for (const el of wrap.querySelectorAll("input, select, button")) {
        el.disabled = inactive;
      }
    }
  }

  async function runControlCommand({
    id,
    command,
    value,
    confirm = false,
    confirmMessage,
    allow_raw = false,
  }) {
    if (confirm || confirmMessage) {
      const msg =
        confirmMessage ||
        `Send command${command ? ` ${command}` : ""}?`;
      if (!window.confirm(msg)) return;
    }
    const onDashboard = state.route?.view === "dashboard";
    state.controlBusy = true;
    if (onDashboard) dashboardBanner("Applying…");
    else controlBanner("Applying…");
    try {
      let layout = "less";
      let section;
      if (onDashboard) {
        const host = document.activeElement?.closest?.(".dashboard-widget");
        layout = host?.dataset?.controlLayout || "less";
      } else {
        layout = sectionControlLayout();
        const sectionIds = mappedSectionsFor(state.controlSectionId, layout);
        section = sectionIds.length === 1 ? sectionIds[0] : undefined;
      }
      const body = {
        confirm: Boolean(confirm || confirmMessage),
        allow_raw: Boolean(allow_raw),
        section,
        layout,
      };
      if (id) {
        body.id = id;
        if (value !== undefined) body.value = value;
      } else {
        body.command = command;
      }
      const result = await api("/api/control/command", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setControlTransport(result.transport);
      appendControlLog(result);
      if (result.entities && typeof result.entities === "object") {
        state.controlEntities = { ...state.controlEntities, ...result.entities };
        applyControlEntitiesToDom();
      }
      if (onDashboard) {
        dashboardBanner(`Applied: ${result.request}`, "ok", { log: false });
        refreshDashboardStatus({ quiet: true }).catch(() => {});
      } else {
        controlBanner(`Applied: ${result.request}`, "ok", { log: false });
        refreshControlStatus({ quiet: true, refresh: false }).catch(() => {});
      }
      setStatus(`Control: ${result.request}`, "ok");
    } catch (err) {
      if (onDashboard) dashboardBanner(err.message, "err");
      else controlBanner(err.message, "err");
      setStatus(err.message, "err");
    } finally {
      state.controlBusy = false;
    }
  }

  async function refreshControlStatus({
    quiet = false,
    refresh = false,
    full = false,
  } = {}) {
    if (!state.controlSectionId) return;
    if (!quiet) controlBanner(refresh ? "Reading AVR…" : "Updating…");
    try {
      const layout = sectionControlLayout();
      const sectionIds = mappedSectionsFor(state.controlSectionId, layout);
      const q = new URLSearchParams({
        refresh: refresh ? "true" : "false",
        layout,
      });
      if (full) {
        q.set("full", "true");
      } else if (sectionIds.length === 1) {
        q.set("section", sectionIds[0]);
      }
      // Multi-mapped sections (e.g. power+volume): read full cache entities
      const snap = await api(`/api/control/status?${q}`);
      setControlTransport(snap.from_cache ? "cache" : snap.transport);
      let entities = snap.entities || {};
      if (!full && sectionIds.length > 1) {
        const cat = catalogForLayout(layout);
        const allow = new Set(
          (cat?.controls || [])
            .filter((c) => sectionIds.includes(c.section))
            .map((c) => c.id)
        );
        entities = Object.fromEntries(
          Object.entries(entities).filter(([id]) => allow.has(id))
        );
      }
      state.controlEntities = entities;
      applyControlEntitiesToDom();
      if (refresh && snap.responses?.length) {
        appendControlLog({
          request: full
            ? "STATUS:all"
            : `STATUS:${state.controlSectionId}/${layout}`,
          transport: snap.transport,
          responses: snap.responses.slice(0, 40),
        });
      }
      const n = Object.keys(state.controlEntities).length;
      if (snap.errors?.length && !quiet) {
        controlBanner(`Status partial (${n} values, ${snap.errors.length} errors)`, "warn");
      } else if (!quiet) {
        controlBanner(
          n
            ? `Ready · ${n} values${snap.from_cache ? " (cached)" : ""}`
            : "Ready",
          "ok"
        );
      }
    } catch (err) {
      if (!quiet) controlBanner(err.message, "err");
    }
  }

  async function waitForControlPreload(maxMs = 20000) {
    const start = Date.now();
    while (Date.now() - start < maxMs) {
      try {
        const p = await api("/api/control/preload");
        if (p.status === "ready" || p.status === "error") return p;
      } catch (_) {
        /* ignore */
      }
      await new Promise((r) => setTimeout(r, 350));
    }
    return { status: "timeout" };
  }

  async function ensureControlCatalogs({ force = false } = {}) {
    if (force) {
      state.controlCatalogByLayout = { less: null, more: null };
    }
    const jobs = [];
    if (force || !state.controlCatalogByLayout.less) {
      jobs.push(
        api("/api/control/catalog?layout=less").then((d) => {
          state.controlCatalogByLayout.less = d;
        })
      );
    }
    if (force || !state.controlCatalogByLayout.more) {
      jobs.push(
        api("/api/control/catalog?layout=more").then((d) => {
          state.controlCatalogByLayout.more = d;
        })
      );
    }
    if (jobs.length) await Promise.all(jobs);
    state.controlCatalog =
      state.controlCatalogByLayout[globalControlLayout()] ||
      state.controlCatalogByLayout.less;
  }

  async function loadControlPanel({ force = false } = {}) {
    if (!state.connected) {
      controlBanner("Connect to AVR first", "warn");
      return;
    }
    try {
      await ensureControlCatalogs({ force: force || !state.controlCatalog });
      renderControlNav();
      const preload = state.controlCatalog?.preload || {};
      if (preload.status === "pending" || preload.status === "running") {
        controlBanner("Loading AVR status…", null, { sticky: true, log: false });
        await waitForControlPreload();
      }
      const sections = state.controlCatalog.sections || [];
      const first = state.controlSectionId || sections[0]?.id;
      if (first) await selectControlSection(first);
      else {
        if ($("control-editor")) $("control-editor").hidden = true;
        if ($("control-empty")) $("control-empty").hidden = false;
      }
    } catch (err) {
      controlBanner(err.message, "err");
    }
  }

  function wireControlPanel() {
    $("control-refresh")?.addEventListener("click", () =>
      refreshControlStatus({ quiet: false, refresh: true, full: true }).catch((e) =>
        controlBanner(e.message, "err")
      )
    );
    $("control-section-layout")?.addEventListener("click", () =>
      toggleSectionLayout().catch((e) => controlBanner(e.message, "err"))
    );
  }

  /* ---------- Dashboard (customisable favourites) ---------- */

  const DASH_DEFAULT_ICONS = {
    pw_power: { on: "mdi:power", off: "mdi:power-standby" },
    zm_main: { on: "mdi:amplifier", off: "mdi:amplifier-off" },
    z2_power: { on: "mdi:speaker", off: "mdi:speaker-off" },
    mu_mute: { on: "mdi:volume-off", off: "mdi:volume-high" },
    si_select: { on: "mdi:import", off: "mdi:import" },
    ms_select: { on: "mdi:surround-sound", off: "mdi:surround-sound" },
    mv_master: { on: "mdi:volume-high", off: "mdi:volume-medium" },
  };

  function dashboardBanner(text, kind, { sticky = false, log = true } = {}) {
    const el = $("dashboard-banner");
    if (!el) return;
    if (!text) {
      el.hidden = true;
      el.textContent = "";
      el.classList.remove("ok", "err", "warn");
      return;
    }
    if (log) {
      pushActivity(text, kind || "info", { silent: true });
    }
    const show =
      sticky || kind === "err" || kind === "warn" ||
      /^(Loading AVR|Refreshing|Connect)/i.test(text);
    if (!show) {
      el.hidden = true;
      el.textContent = "";
      el.classList.remove("ok", "err", "warn");
      return;
    }
    el.hidden = false;
    el.textContent = text;
    el.classList.remove("ok", "err", "warn");
    if (kind) el.classList.add(kind);
    if (state.activityBannerTimer) clearTimeout(state.activityBannerTimer);
    if (!sticky && kind !== "err") {
      state.activityBannerTimer = setTimeout(() => {
        if (el.textContent === text) {
          el.hidden = true;
          el.textContent = "";
          el.classList.remove("ok", "err", "warn");
        }
      }, 2500);
    }
  }

  function setDashboardEdit(on) {
    state.dashboardEdit = Boolean(on);
    document.body.classList.toggle("dashboard-editing", state.dashboardEdit);
    $("dashboard-customize")?.classList.toggle("is-active", state.dashboardEdit);
    $("dashboard-customize").textContent = state.dashboardEdit
      ? "Done"
      : "Customize";
    if ($("dashboard-add-section")) {
      $("dashboard-add-section").hidden = !state.dashboardEdit;
    }
    if ($("dashboard-add-layout")) {
      $("dashboard-add-layout").hidden = !state.dashboardEdit;
    }
    if ($("dashboard-raw-yaml")) {
      $("dashboard-raw-yaml").hidden = !state.dashboardEdit;
    }
    if (state.dashboardEdit) {
      dashboardBanner(
        "Edit mode: drag ⠿ to move. Click a card to open its settings. Raw YAML is available in the toolbar.",
        "ok"
      );
    }
    renderDashboard();
  }

  function dashIconRef(ref) {
    const raw = String(ref || "").trim();
    if (!raw) return null;
    if (raw.startsWith("custom:")) {
      const id = raw.slice(7);
      const hit = (state.dashboardIcons?.custom || []).find((c) => c.id === id);
      if (hit) return { type: "custom", url: hit.url, ref: hit.ref };
      return { type: "custom", url: "", ref: raw };
    }
    let name = raw;
    if (name.startsWith("mdi:")) name = name.slice(4);
    if (!name.startsWith("mdi-")) name = `mdi-${name}`;
    return { type: "mdi", class: name, ref: `mdi:${name.replace(/^mdi-/, "")}` };
  }

  function renderIconNode(resolved, layer) {
    const span = document.createElement("span");
    span.className = "dash-icon-layer";
    span.dataset.layer = layer;
    if (!resolved) {
      span.innerHTML = `<i class="mdi mdi-tune" aria-hidden="true"></i>`;
      return span;
    }
    if (resolved.type === "custom" && resolved.url) {
      const img = document.createElement("img");
      img.src = resolved.url;
      img.alt = "";
      img.className = "dash-icon-img";
      span.appendChild(img);
    } else {
      const i = document.createElement("i");
      i.className = `mdi ${resolved.class || "mdi-tune"}`;
      i.setAttribute("aria-hidden", "true");
      span.appendChild(i);
    }
    return span;
  }

  function buildDashIconHost(w) {
    const host = document.createElement("div");
    host.className = "dash-icon is-off";
    host.dataset.role = "dash-icon";
    const defaults = DASH_DEFAULT_ICONS[w.control_id] || {
      on: "mdi:tune",
      off: "mdi:tune",
    };
    const onRef = w.icon_on || defaults.on;
    const offRef = w.icon_off || defaults.off;
    host.appendChild(
      renderIconNode(w.icon_on_resolved || dashIconRef(onRef), "on")
    );
    host.appendChild(
      renderIconNode(w.icon_off_resolved || dashIconRef(offRef), "off")
    );
    return host;
  }

  async function ensureDashboardIcons({ force = false } = {}) {
    if (!force && state.dashboardIcons) return state.dashboardIcons;
    state.dashboardIcons = await api("/api/dashboard/icons");
    return state.dashboardIcons;
  }

  async function loadDashboard({ force = false } = {}) {
    if (!state.connected) {
      dashboardBanner("Connect to AVR first", "warn");
      return;
    }
    try {
      let waitingPreload = false;
      try {
        const preload = await api("/api/control/preload");
        if (preload.status === "pending" || preload.status === "running") {
          waitingPreload = true;
          dashboardBanner("Loading AVR status…", null, {
            sticky: true,
            log: false,
          });
          await waitForControlPreload();
        }
      } catch (_) {
        /* ignore */
      }
      if (force && !waitingPreload) {
        dashboardBanner("Refreshing…", null, { sticky: true, log: false });
      }
      if (force || !state.dashboard) {
        state.dashboard = await api("/api/dashboard");
      }
      if (force || !state.dashboardCatalog) {
        state.dashboardCatalog = await api("/api/dashboard/catalog");
      }
      await ensureDashboardIcons({ force });
      await refreshDashboardStatus({ quiet: true, refresh: force });
      state.dashboardStatusReady = true;
      renderDashboard();
      dashboardBanner("");
    } catch (err) {
      dashboardBanner(err.message, "err");
    }
  }

  async function refreshDashboardStatus({ quiet = false, refresh = false } = {}) {
    try {
      const q = refresh ? "refresh=true" : "refresh=false";
      const snap = await api(`/api/control/status?${q}&layout=more`);
      state.controlEntities = {
        ...(state.controlEntities || {}),
        ...(snap.entities || {}),
      };
      // Prefer live goform power when present (header already uses /api/power).
      const pwr = (snap.power?.power || "").toLowerCase();
      if (pwr === "on" || pwr === "standby") {
        const on = pwr === "on";
        state.controlEntities.pw_power = {
          ...(state.controlEntities.pw_power || {}),
          kind: "toggle",
          value: on,
          on,
          raw: on ? "PWON" : "PWSTANDBY",
          display: on ? "On" : "Standby",
          source: "goform",
          inactive: false,
        };
      }
      applyDashboardEntities();
      if (!quiet) dashboardBanner("Dashboard updated", "ok");
    } catch (err) {
      if (!quiet) dashboardBanner(err.message, "err");
    }
  }

  function dashWidgetLabel(w) {
    const custom = String(w.custom_name || "").trim();
    if (custom) return custom;
    return w.control?.label || w.control_id || "Card";
  }

  function applyDashboardEntities() {
    const root = $("dashboard-sections");
    if (!root) return;
    applyControlEntitiesToDom();
    for (const shell of root.querySelectorAll(".dashboard-widget")) {
      const id = shell.dataset.controlId;
      const ent = controlEntity(id);
      const kind = shell.dataset.kind || "";
      const icon = shell.querySelector('[data-role="dash-icon"]');
      const stateEl = shell.querySelector('[data-role="dash-state"]');
      const inactive = Boolean(ent?.inactive);
      let on = false;
      if (kind === "toggle") {
        on = ent?.on === true || ent?.value === true;
      } else {
        on = Boolean(
          ent &&
            !inactive &&
            (ent.on === true || ent.active || ent.display || ent.raw)
        );
      }
      if (icon) {
        icon.classList.toggle("is-on", on);
        icon.classList.toggle("is-off", !on);
      }
      shell.classList.toggle("is-entity-on", on);
      shell.classList.toggle("is-entity-off", !on);
      shell.classList.toggle("is-inactive", inactive);
      if (stateEl) {
        if (kind === "toggle") {
          const onL =
            shell.dataset.onLabel ||
            (String(id).includes("mute") ? "Muted" : "On");
          const offL =
            shell.dataset.offLabel ||
            (id === "pw_power"
              ? "Standby"
              : String(id).includes("mute")
                ? "Unmuted"
                : "Off");
          stateEl.textContent = inactive
            ? "—"
            : on
              ? onL
              : offL;
        } else if (ent?.display) {
          stateEl.textContent = ent.display;
        } else if (ent?.raw) {
          stateEl.textContent = ent.raw;
        } else {
          stateEl.textContent = "—";
        }
      }
      const range = shell.querySelector('[data-role="dash-inline-range"]');
      const rangeVal = shell.querySelector('[data-role="dash-inline-value"]');
      if (range && document.activeElement !== range) {
        if (ent?.value != null && !Number.isNaN(Number(ent.value))) {
          range.value = String(ent.value);
          if (rangeVal) {
            const label =
              ent.display ||
              formatDashSliderLabel(
                {
                  min: shell.dataset.sliderMin,
                  max: shell.dataset.sliderMax,
                  zero_db: shell.dataset.sliderZero,
                },
                ent.value
              );
            rangeVal.textContent = label;
          }
        }
      }
      const valueBadge = shell.querySelector('[data-role="dash-value-badge"]');
      if (valueBadge) {
        let label = "";
        if (kind === "slider" || kind === "stepper") {
          label = ent?.display || "";
          if (!label && ent?.value != null && !Number.isNaN(Number(ent.value))) {
            label = formatDashSliderLabel(
              {
                min: shell.dataset.sliderMin,
                max: shell.dataset.sliderMax,
                zero_db: shell.dataset.sliderZero,
              },
              ent.value
            );
          }
        } else if (kind === "enum") {
          label = ent?.display || ent?.command || ent?.raw || "";
        } else if (kind === "toggle") {
          label = inactive ? "—" : on
            ? (shell.dataset.onLabel || (String(id).includes("mute") ? "Muted" : "On"))
            : (shell.dataset.offLabel || (id === "pw_power" ? "Standby" : String(id).includes("mute") ? "Unmuted" : "Off"));
        }
        valueBadge.textContent = label || "—";
        valueBadge.hidden = Boolean(inactive && !label);
      }
      const sel = shell.querySelector('[data-role="dash-inline-select"]');
      if (sel && document.activeElement !== sel) {
        const cur = ent?.command || ent?.raw || "";
        if (cur && [...sel.options].some((o) => o.value === cur)) {
          sel.value = cur;
        }
      }
    }
  }

  function dashboardPayloadFromDom() {
    const root = $("dashboard-sections");
    const layouts = [];
    if (!root) return { layouts, sections: [] };
    for (const layoutEl of root.querySelectorAll(":scope > .dashboard-layout")) {
      const lid = layoutEl.dataset.layoutId || "";
      const sections = [];
      for (const secEl of layoutEl.querySelectorAll(
        ":scope > .dashboard-layout-body > .dashboard-section"
      )) {
        const sid = secEl.dataset.sectionId;
        const title =
          secEl.querySelector(".dashboard-section-title")?.textContent?.trim() ||
          "Section";
        const widgets = [];
        for (const wEl of secEl.querySelectorAll(".dashboard-widget")) {
          widgets.push({
            id: wEl.dataset.widgetId,
            control_id: wEl.dataset.controlId,
            control_layout: wEl.dataset.controlLayout || "less",
            sort_order: widgets.length,
            shape: wEl.dataset.shape || "square",
            size: wEl.dataset.size || "md",
            width_px: Number(wEl.dataset.widthPx || 0) || 0,
            height_px: Number(wEl.dataset.heightPx || 0) || 0,
            control_ui: wEl.dataset.controlUi || "auto",
            icon_on: wEl.dataset.iconOn || "",
            icon_off: wEl.dataset.iconOff || "",
            color_on: wEl.dataset.colorOn || "",
            color_off: wEl.dataset.colorOff || "",
            custom_name: wEl.dataset.customName || "",
            card_mod: wEl.dataset.cardMod
              ? { style: wEl.dataset.cardMod }
              : null,
          });
        }
        sections.push({
          id: sid,
          title,
          sort_order: sections.length,
          collapsed: secEl.classList.contains("is-collapsed"),
          stack: "horizontal",
          size: "custom",
          width_px: Number(secEl.dataset.widthPx || 0) || 0,
          height_px: Number(secEl.dataset.heightPx || 0) || 0,
          layout_id: lid,
          card_mod: secEl.dataset.cardMod
            ? { style: secEl.dataset.cardMod }
            : null,
          widgets,
        });
      }
      layouts.push({
        id: lid,
        stack: layoutEl.dataset.stack || "horizontal",
        sort_order: layouts.length,
        sections,
      });
    }
    const sections = layouts.flatMap((ly) => ly.sections);
    return { layouts, sections };
  }

  async function persistDashboardFromDom() {
    const body = dashboardPayloadFromDom();
    state.dashboard = await api("/api/dashboard", {
      method: "PUT",
      body: JSON.stringify(body),
    });
    renderDashboard();
  }

  function patchWidgetFields(widgetId, fields) {
    return api(`/api/dashboard/widgets/${widgetId}`, {
      method: "PATCH",
      body: JSON.stringify(fields),
    }).then((d) => {
      state.dashboard = d;
      renderDashboard();
    });
  }

  function patchSectionFields(sectionId, fields) {
    return api(`/api/dashboard/sections/${sectionId}`, {
      method: "PATCH",
      body: JSON.stringify(fields),
    }).then((d) => {
      state.dashboard = d;
      renderDashboard();
    });
  }

  function renderDashboard() {
    const root = $("dashboard-sections");
    const empty = $("dashboard-empty");
    const meta = $("dashboard-meta");
    if (!root) return;
    let layouts = state.dashboard?.layouts || [];
    const sections = state.dashboard?.sections || [];
    if (!layouts.length && sections.length) {
      layouts = [
        {
          id: "",
          stack: "horizontal",
          sort_order: 0,
          sections,
        },
      ];
    }
    if (meta) {
      const n = sections.reduce((a, s) => a + (s.widgets?.length || 0), 0);
      meta.textContent = state.dashboardEdit
        ? `Editing · ${layouts.length} layouts · ${sections.length} sections · ${n} widgets`
        : `${layouts.length} layouts · ${sections.length} sections · ${n} widgets · stored in SQLite`;
    }
    root.innerHTML = "";
    if (!layouts.length && !sections.length) {
      if (empty) empty.hidden = false;
      return;
    }
    if (empty) empty.hidden = true;
    for (const ly of layouts) {
      root.appendChild(buildDashboardLayout(ly));
    }
    applyDashboardEntities();
  }

  function buildDashboardLayout(ly) {
    const wrap = document.createElement("div");
    const stack = ly.stack || "horizontal";
    wrap.className = `dashboard-layout stack-${stack}`;
    wrap.dataset.layoutId = ly.id || "";
    wrap.dataset.stack = stack;

    if (state.dashboardEdit) {
      const head = document.createElement("header");
      head.className = "dashboard-layout-head";

      const handle = document.createElement("span");
      handle.className = "dashboard-drag-handle";
      handle.title = "Drag layout";
      handle.textContent = "⠿";
      handle.draggable = true;
      handle.addEventListener("dragstart", (ev) => {
        state.dashboardDrag = { type: "layout", id: ly.id || "" };
        wrap.classList.add("is-dragging");
        ev.dataTransfer.effectAllowed = "move";
        ev.stopPropagation();
      });
      handle.addEventListener("dragend", () => {
        wrap.classList.remove("is-dragging");
        state.dashboardDrag = null;
        clearDashDragOver();
      });
      head.appendChild(handle);

      const label = document.createElement("span");
      label.className = "dashboard-layout-label";
      label.textContent = "Layout stack";
      head.appendChild(label);
      const stackSel = buildStackSelect(stack, (v) => {
        if (!ly.id) {
          wrap.dataset.stack = v;
          wrap.className = `dashboard-layout stack-${v}`;
          const bodyEl = wrap.querySelector(".dashboard-layout-body");
          if (bodyEl) bodyEl.className = `dashboard-layout-body stack-${v}`;
          return;
        }
        api(`/api/dashboard/layouts/${ly.id}`, {
          method: "PATCH",
          body: JSON.stringify({ stack: v }),
        })
          .then((d) => {
            state.dashboard = d;
            renderDashboard();
          })
          .catch((e) => dashboardBanner(e.message, "err"));
      });
      stackSel.title = "Horizontal or vertical arrangement of sections in this layout";
      head.appendChild(stackSel);

      const addSec = document.createElement("button");
      addSec.type = "button";
      addSec.className = "btn-ghost";
      addSec.textContent = "Add section";
      addSec.addEventListener("click", () => {
        const title = window.prompt("Section title", "New section");
        if (title == null) return;
        api("/api/dashboard/sections", {
          method: "POST",
          body: JSON.stringify({
            title: title.trim() || "New section",
            layout_id: ly.id || null,
          }),
        })
          .then((d) => {
            state.dashboard = d;
            renderDashboard();
          })
          .catch((e) => dashboardBanner(e.message, "err"));
      });
      head.appendChild(addSec);
      if (ly.id) {
        const del = document.createElement("button");
        del.type = "button";
        del.className = "btn-ghost";
        del.textContent = "Delete layout";
        del.addEventListener("click", () => {
          if (
            !window.confirm(
              "Delete this layout and all sections inside it?"
            )
          )
            return;
          api(`/api/dashboard/layouts/${ly.id}`, { method: "DELETE" })
            .then((d) => {
              state.dashboard = d;
              renderDashboard();
            })
            .catch((e) => dashboardBanner(e.message, "err"));
        });
        head.appendChild(del);
      }
      wrap.appendChild(head);

      wrap.addEventListener("dragover", (ev) => {
        const drag = state.dashboardDrag;
        if (!drag || (drag.type !== "layout" && drag.type !== "section")) return;
        ev.preventDefault();
        wrap.classList.add("drag-over");
      });
      wrap.addEventListener("dragleave", (ev) => {
        if (!wrap.contains(ev.relatedTarget)) wrap.classList.remove("drag-over");
      });
      wrap.addEventListener("drop", (ev) => {
        ev.preventDefault();
        wrap.classList.remove("drag-over");
        const drag = state.dashboardDrag;
        if (!drag) return;
        if (drag.type === "layout") {
          const root = $("dashboard-sections");
          const from = root?.querySelector(
            `.dashboard-layout[data-layout-id="${CSS.escape(drag.id)}"]`
          );
          if (from && from !== wrap) root.insertBefore(from, wrap);
          persistDashboardFromDom().catch((e) =>
            dashboardBanner(e.message, "err")
          );
        }
      });
    }

    const body = document.createElement("div");
    body.className = `dashboard-layout-body stack-${stack}`;
    if (state.dashboardEdit) {
      body.addEventListener("dragover", (ev) => {
        if (state.dashboardDrag?.type !== "section") return;
        ev.preventDefault();
        body.classList.add("drag-over");
      });
      body.addEventListener("dragleave", (ev) => {
        if (!body.contains(ev.relatedTarget)) body.classList.remove("drag-over");
      });
      body.addEventListener("drop", (ev) => {
        ev.preventDefault();
        body.classList.remove("drag-over");
        const drag = state.dashboardDrag;
        if (!drag || drag.type !== "section") return;
        const from = document.querySelector(
          `.dashboard-section[data-section-id="${CSS.escape(drag.id)}"]`
        );
        if (from) body.appendChild(from);
        persistDashboardFromDom().catch((e) =>
          dashboardBanner(e.message, "err")
        );
      });
    }
    const secs = ly.sections || [];
    if (!secs.length) {
      const empty = document.createElement("div");
      empty.className = "dashboard-layout-empty";
      empty.textContent = state.dashboardEdit
        ? "Empty layout — press Add section (or drop a section here)"
        : "Empty layout";
      if (state.dashboardEdit) {
        empty.addEventListener("click", () => {
          const title = window.prompt("Section title", "New section");
          if (title == null) return;
          api("/api/dashboard/sections", {
            method: "POST",
            body: JSON.stringify({
              title: title.trim() || "New section",
              layout_id: ly.id || null,
            }),
          })
            .then((d) => {
              state.dashboard = d;
              renderDashboard();
            })
            .catch((e) => dashboardBanner(e.message, "err"));
        });
      }
      body.appendChild(empty);
    } else {
      for (const sec of secs) {
        body.appendChild(buildDashboardSection(sec));
      }
    }
    wrap.appendChild(body);
    return wrap;
  }

  function clearDashDragOver() {
    document
      .querySelectorAll(
        ".dashboard-layout.drag-over, .dashboard-layout-body.drag-over, .dashboard-section.drag-over, .dashboard-grid.drag-over, .dashboard-widget.drag-over"
      )
      .forEach((el) => el.classList.remove("drag-over"));
  }

  function buildSizeSelect(options, value, onChange) {
    const sel = document.createElement("select");
    sel.className = "dash-style-select";
    sel.title = "Size";
    for (const [val, label] of options) {
      const o = document.createElement("option");
      o.value = val;
      o.textContent = label;
      if (val === value) o.selected = true;
      sel.appendChild(o);
    }
    sel.addEventListener("change", () => onChange(sel.value));
    sel.addEventListener("mousedown", (e) => e.stopPropagation());
    sel.addEventListener("click", (e) => e.stopPropagation());
    return sel;
  }

  function buildStackSelect(value, onChange) {
    return buildSizeSelect(
      [
        ["horizontal", "Horizontal stack"],
        ["vertical", "Vertical stack"],
      ],
      value || "horizontal",
      onChange
    );
  }

  function contrastInk(hex) {
    const h = String(hex || "").replace("#", "");
    if (h.length !== 3 && h.length !== 6) return "#f8fafc";
    const full =
      h.length === 3
        ? h
            .split("")
            .map((c) => c + c)
            .join("")
        : h;
    const r = parseInt(full.slice(0, 2), 16);
    const g = parseInt(full.slice(2, 4), 16);
    const b = parseInt(full.slice(4, 6), 16);
    const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return lum > 0.55 ? "#1e293b" : "#f8fafc";
  }

  function applyDashCardColors(shell, w) {
    const on = w.color_on || "#e8eef2";
    const off = w.color_off || "#3a4248";
    shell.style.setProperty("--dash-on-bg", on);
    shell.style.setProperty("--dash-off-bg", off);
    shell.style.setProperty("--dash-on-fg", contrastInk(on));
    shell.style.setProperty("--dash-off-fg", contrastInk(off));
    shell.dataset.colorOn = on;
    shell.dataset.colorOff = off;
  }

  function buildColorInput(value, title, onChange) {
    const wrap = document.createElement("label");
    wrap.className = "dash-color-field";
    wrap.title = title;
    const lab = document.createElement("span");
    lab.textContent = title;
    const input = document.createElement("input");
    input.type = "color";
    input.value = value && /^#[0-9a-fA-F]{6}$/.test(value) ? value : "#3a4248";
    input.addEventListener("mousedown", (e) => e.stopPropagation());
    input.addEventListener("click", (e) => e.stopPropagation());
    input.addEventListener("change", () => onChange(input.value));
    wrap.appendChild(lab);
    wrap.appendChild(input);
    return wrap;
  }

  function buildDashboardSection(sec) {
    const wrap = document.createElement("section");
    const widthPx = Number(sec.width_px) || 0;
    const heightPx = Number(sec.height_px) || 0;
    wrap.className = "dashboard-section stack-horizontal size-custom";
    wrap.dataset.sectionId = sec.id;
    wrap.dataset.stack = "horizontal";
    wrap.dataset.size = "custom";
    wrap.dataset.widthPx = String(widthPx);
    wrap.dataset.heightPx = String(heightPx);
    const secMod = cardModStyleText(sec.card_mod);
    if (secMod) wrap.dataset.cardMod = secMod;
    else delete wrap.dataset.cardMod;
    if (widthPx > 0) {
      wrap.style.width = `${widthPx}px`;
      wrap.style.flex = `0 0 ${widthPx}px`;
      wrap.style.maxWidth = "100%";
    }
    if (heightPx > 0) {
      wrap.style.minHeight = `${heightPx}px`;
    }
    if (sec.collapsed) wrap.classList.add("is-collapsed");
    if (state.dashboardEdit) {
      wrap.addEventListener("dragover", (ev) => {
        if (state.dashboardDrag?.type !== "section") return;
        ev.preventDefault();
        wrap.classList.add("drag-over");
      });
      wrap.addEventListener("dragleave", (ev) => {
        if (!wrap.contains(ev.relatedTarget)) wrap.classList.remove("drag-over");
      });
      wrap.addEventListener("drop", (ev) => {
        ev.preventDefault();
        wrap.classList.remove("drag-over");
        const drag = state.dashboardDrag;
        if (!drag || drag.type !== "section" || drag.id === sec.id) return;
        const parent = wrap.parentElement;
        const from = document.querySelector(
          `.dashboard-section[data-section-id="${CSS.escape(drag.id)}"]`
        );
        if (from && parent) parent.insertBefore(from, wrap);
        persistDashboardFromDom().catch((e) => dashboardBanner(e.message, "err"));
      });
    }

    const head = document.createElement("header");
    head.className = "dashboard-section-head";
    if (state.dashboardEdit) {
      const handle = document.createElement("span");
      handle.className = "dashboard-drag-handle";
      handle.title = "Drag section";
      handle.textContent = "⠿";
      handle.draggable = true;
      handle.addEventListener("dragstart", (ev) => {
        state.dashboardDrag = { type: "section", id: sec.id };
        wrap.classList.add("is-dragging");
        ev.dataTransfer.effectAllowed = "move";
        ev.stopPropagation();
      });
      handle.addEventListener("dragend", () => {
        wrap.classList.remove("is-dragging");
        state.dashboardDrag = null;
        clearDashDragOver();
      });
      head.appendChild(handle);
    }
    const title = document.createElement("h3");
    title.className = "dashboard-section-title";
    title.textContent = sec.title || "Section";
    if (state.dashboardEdit) {
      title.contentEditable = "true";
      title.spellcheck = false;
      title.addEventListener("blur", () => {
        const t = title.textContent.trim() || "Section";
        title.textContent = t;
        patchSectionFields(sec.id, { title: t }).catch((e) =>
          dashboardBanner(e.message, "err")
        );
      });
    }
    head.appendChild(title);
    if (state.dashboardEdit) {
      const actions = document.createElement("div");
      actions.className = "dashboard-section-actions";
      const settingsBtn = document.createElement("button");
      settingsBtn.type = "button";
      settingsBtn.className = "btn-ghost";
      settingsBtn.textContent = "Settings";
      settingsBtn.title = "Section size and title";
      settingsBtn.addEventListener("click", (ev) => {
        ev.stopPropagation();
        openSectionSettings(sec);
      });
      const addBtn = document.createElement("button");
      addBtn.type = "button";
      addBtn.className = "btn-ghost";
      addBtn.textContent = "Add widget";
      addBtn.addEventListener("click", () => openDashboardPicker(sec.id));
      const delBtn = document.createElement("button");
      delBtn.type = "button";
      delBtn.className = "btn-ghost";
      delBtn.textContent = "Delete";
      delBtn.addEventListener("click", () => {
        if (!window.confirm(`Delete section “${sec.title}”?`)) return;
        api(`/api/dashboard/sections/${sec.id}`, { method: "DELETE" })
          .then((d) => {
            state.dashboard = d;
            renderDashboard();
          })
          .catch((e) => dashboardBanner(e.message, "err"));
      });
      actions.appendChild(settingsBtn);
      actions.appendChild(addBtn);
      actions.appendChild(delBtn);
      head.appendChild(actions);
    }
    wrap.appendChild(head);

    const grid = document.createElement("div");
    grid.className = "dashboard-grid stack-horizontal";
    grid.dataset.sectionId = sec.id;
    if (state.dashboardEdit) {
      grid.addEventListener("dragover", (ev) => {
        if (state.dashboardDrag?.type !== "widget") return;
        ev.preventDefault();
        ev.stopPropagation();
        grid.classList.add("drag-over");
      });
      grid.addEventListener("dragleave", (ev) => {
        if (!grid.contains(ev.relatedTarget)) grid.classList.remove("drag-over");
      });
      grid.addEventListener("drop", (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        grid.classList.remove("drag-over");
        const drag = state.dashboardDrag;
        if (!drag || drag.type !== "widget") return;
        const from = document.querySelector(
          `.dashboard-widget[data-widget-id="${CSS.escape(drag.id)}"]`
        );
        if (from) grid.appendChild(from);
        persistDashboardFromDom().catch((e) => dashboardBanner(e.message, "err"));
      });
    }
    for (const w of sec.widgets || []) {
      grid.appendChild(buildDashboardWidget(w));
    }
    if (!(sec.widgets || []).length) {
      const hint = document.createElement("p");
      hint.className = "dashboard-section-empty";
      hint.textContent = state.dashboardEdit
        ? "Drop widgets here or press Add widget"
        : "No widgets in this section";
      grid.appendChild(hint);
    }
    wrap.appendChild(grid);
    applyCardMod(wrap, sec.card_mod, sec.id);
    return wrap;
  }

  function bounceDashCard(el) {
    if (!el) return;
    el.classList.remove("dash-bounce");
    // force reflow so animation can replay
    void el.offsetWidth;
    el.classList.add("dash-bounce");
    window.setTimeout(() => el.classList.remove("dash-bounce"), 500);
  }

  function openEnumPopup(control) {
    const dlg = $("dashboard-enum-popup");
    const title = $("dashboard-enum-title");
    const list = $("dashboard-enum-list");
    if (!dlg || !list || !control) return;
    if (title) title.textContent = control.label || "Select";
    list.innerHTML = "";
    const ent = controlEntity(control.id);
    const current = ent?.command || ent?.raw || "";
    const options = control.options || [];
    if (!options.length) {
      list.innerHTML = "<p class='meta'>No options</p>";
    }
    for (const opt of options) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className =
        "dashboard-enum-option" +
        (opt.command === current ? " is-selected" : "");
      btn.innerHTML = `<strong>${opt.label || opt.command}</strong>`;
      if (opt.command && opt.command !== opt.label) {
        const code = document.createElement("span");
        code.textContent = opt.command;
        btn.appendChild(code);
      }
      btn.addEventListener("click", () => {
        runControlCommand({
          id: control.id,
          value: opt.command,
          confirm: Boolean(control.confirm),
          confirmMessage: control.confirm_message,
        });
        if (typeof dlg.close === "function") dlg.close();
        else dlg.removeAttribute("open");
      });
      list.appendChild(btn);
    }
    if (typeof dlg.showModal === "function") dlg.showModal();
    else dlg.setAttribute("open", "open");
  }

  /**
   * Slider popup for stepper/slider controls on Dashboard.
   * Range input applies instantly (debounced) — no Apply button.
   */
  function formatDashSliderLabel(control, raw) {
    const n = Number(raw);
    if (Number.isNaN(n)) return String(raw ?? "");
    if (control?.zero_db != null && !Number.isNaN(Number(control.zero_db))) {
      const db = n - Number(control.zero_db);
      const sign = db > 0 ? "+" : "";
      return `${sign}${db} dB`;
    }
    return String(n);
  }

  function openSliderPopup(control, _widgetId) {
    const dlg = $("dashboard-slider-popup");
    const title = $("dashboard-slider-title");
    const body = $("dashboard-slider-body");
    if (!dlg || !body || !control) return;
    if (title) title.textContent = control.label || "Adjust";
    const ent = controlEntity(control.id);
    const lo = control.min != null ? Number(control.min) : 0;
    const hi = control.max != null ? Number(control.max) : 100;
    const step = Number(control.step || 1) || 1;
    let val =
      ent?.value != null && !Number.isNaN(Number(ent.value))
        ? Number(ent.value)
        : Math.round((lo + hi) / 2);
    val = Math.max(lo, Math.min(hi, val));

    body.innerHTML = "";
    const range = document.createElement("input");
    range.type = "range";
    range.min = String(lo);
    range.max = String(hi);
    range.step = String(step);
    range.value = String(val);
    range.className = "dashboard-slider-range";
    const valEl = document.createElement("span");
    valEl.className = "dashboard-slider-value";
    valEl.textContent = formatDashSliderLabel(control, val);
    let timer = null;
    function sendNow() {
      runControlCommand({
        id: control.id,
        value: Number(range.value),
        confirm: Boolean(control.confirm),
        confirmMessage: control.confirm_message,
      });
    }
    range.addEventListener("input", () => {
      valEl.textContent = formatDashSliderLabel(control, range.value);
      clearTimeout(timer);
      timer = setTimeout(sendNow, 120);
    });
    range.addEventListener("change", () => {
      clearTimeout(timer);
      sendNow();
    });
    body.appendChild(range);
    body.appendChild(valEl);
    if (typeof dlg.showModal === "function") dlg.showModal();
    else dlg.setAttribute("open", "open");
  }

  function wantsInlineControl(w) {
    const mode = String(w.control_ui || "auto").toLowerCase();
    if (mode === "inline") return true;
    if (mode === "popup") return false;
    const ww = Number(w.width_px) || 120;
    const hh = Number(w.height_px) || 120;
    return ww >= 200 || hh >= 180;
  }

  function cardModStyleText(cardMod) {
    if (!cardMod) return "";
    if (typeof cardMod === "string") return cardMod;
    return String(cardMod.style || "");
  }

  function sanitizeCardModCss(css) {
    return String(css || "")
      .replace(/<\/style/gi, "")
      .replace(/<script/gi, "")
      .replace(/ha-card/g, ".dash-card")
      .trim();
  }

  function applyCardMod(host, cardMod, scopePrefix) {
    if (!host) return;
    host.querySelectorAll("style[data-card-mod]").forEach((el) => el.remove());
    const raw = sanitizeCardModCss(cardModStyleText(cardMod));
    if (!raw) return;
    const id = String(scopePrefix || host.dataset.widgetId || host.dataset.sectionId || "x")
      .replace(/[^a-zA-Z0-9_-]/g, "")
      .slice(0, 40);
    const scope = `dash-mod-${id || "x"}`;
    host.classList.add(scope);
    const style = document.createElement("style");
    style.dataset.cardMod = "1";
    const withHost = raw.replace(/:host\b/g, `.${scope}`);
    style.textContent = withHost.replace(
      /(^|})\s*([^@}/{][^{]*)\{/g,
      (m, brace, sel) => {
        const parts = String(sel)
          .split(",")
          .map((s) => {
            const t = s.trim();
            if (!t) return t;
            if (t.startsWith(`.${scope}`)) return t;
            return `.${scope} ${t}`;
          });
        return `${brace}\n${parts.join(", ")} {`;
      }
    );
    host.appendChild(style);
  }

  function mountInlineSlider(card, control) {
    const wrap = document.createElement("div");
    wrap.className = "dash-inline-control dash-inline-slider";
    wrap.addEventListener("click", (e) => e.stopPropagation());
    wrap.addEventListener("pointerdown", (e) => e.stopPropagation());
    const lo = control.min != null ? Number(control.min) : 0;
    const hi = control.max != null ? Number(control.max) : 100;
    const step = Number(control.step || 1) || 1;
    const ent = controlEntity(control.id);
    let val =
      ent?.value != null && !Number.isNaN(Number(ent.value))
        ? Number(ent.value)
        : Math.round((lo + hi) / 2);
    val = Math.max(lo, Math.min(hi, val));
    const range = document.createElement("input");
    range.type = "range";
    range.min = String(lo);
    range.max = String(hi);
    range.step = String(step);
    range.value = String(val);
    range.className = "dashboard-slider-range";
    range.dataset.role = "dash-inline-range";
    const valEl = document.createElement("span");
    valEl.className = "dashboard-slider-value dash-inline-value";
    valEl.dataset.role = "dash-inline-value";
    valEl.textContent = formatDashSliderLabel(control, val);
    const badge = card.querySelector('[data-role="dash-value-badge"]');
    let timer = null;
    function sendNow() {
      runControlCommand({
        id: control.id,
        value: Number(range.value),
        confirm: Boolean(control.confirm),
        confirmMessage: control.confirm_message,
      });
    }
    range.addEventListener("input", () => {
      const label = formatDashSliderLabel(control, range.value);
      valEl.textContent = label;
      if (badge) badge.textContent = label;
      clearTimeout(timer);
      timer = setTimeout(sendNow, 120);
    });
    range.addEventListener("change", () => {
      clearTimeout(timer);
      sendNow();
    });
    card.appendChild(range);
    card.appendChild(valEl);
  }

  function mountInlineEnum(card, control) {
    const sel = document.createElement("select");
    sel.className = "dash-inline-control dash-inline-select";
    sel.dataset.role = "dash-inline-select";
    sel.addEventListener("click", (e) => e.stopPropagation());
    sel.addEventListener("pointerdown", (e) => e.stopPropagation());
    const ent = controlEntity(control.id);
    const current = ent?.command || ent?.raw || "";
    const blank = document.createElement("option");
    blank.value = "";
    blank.textContent = "Select…";
    blank.disabled = true;
    if (!current) blank.selected = true;
    sel.appendChild(blank);
    for (const opt of control.options || []) {
      const o = document.createElement("option");
      o.value = opt.command;
      o.textContent = opt.label || opt.command;
      if (opt.command === current) o.selected = true;
      sel.appendChild(o);
    }
    sel.addEventListener("change", () => {
      if (!sel.value) return;
      runControlCommand({
        id: control.id,
        value: sel.value,
        confirm: Boolean(control.confirm),
        confirmMessage: control.confirm_message,
      });
    });
    card.appendChild(sel);
  }

  function openSettingsPopup({ title, fields, onSave }) {
    const dlg = $("dashboard-settings-popup");
    const titleEl = $("dashboard-settings-title");
    const body = $("dashboard-settings-body");
    const saveBtn = $("dashboard-settings-save");
    if (!dlg || !body || !saveBtn) return;
    if (titleEl) titleEl.textContent = title || "Settings";
    body.innerHTML = "";
    const values = { ...fields };
    const makeRow = (label, input) => {
      const row = document.createElement("label");
      row.className = "dashboard-settings-row";
      const lab = document.createElement("span");
      lab.textContent = label;
      row.appendChild(lab);
      row.appendChild(input);
      body.appendChild(row);
      return input;
    };
    for (const f of fields._schema || []) {
      if (f.type === "text" || f.type === "hex") {
        const inp = document.createElement("input");
        inp.type = "text";
        inp.value = String(values[f.key] ?? "");
        inp.placeholder = f.placeholder || (f.type === "hex" ? "#rrggbb" : "");
        inp.spellcheck = false;
        if (f.type === "hex") {
          inp.pattern = "^#?[0-9A-Fa-f]{3}([0-9A-Fa-f]{3})?$";
          inp.title = "HTML hex color, e.g. #e8eef2";
        }
        inp.addEventListener("input", () => {
          values[f.key] = inp.value;
        });
        makeRow(f.label, inp);
      } else if (f.type === "number") {
        const inp = document.createElement("input");
        inp.type = "number";
        inp.min = String(f.min ?? 0);
        inp.max = String(f.max ?? 4000);
        inp.step = String(f.step ?? 1);
        inp.value = String(values[f.key] ?? 0);
        inp.addEventListener("input", () => {
          values[f.key] = Number(inp.value) || 0;
        });
        makeRow(f.label, inp);
      } else if (f.type === "select") {
        const sel = document.createElement("select");
        for (const [val, lab] of f.options || []) {
          const o = document.createElement("option");
          o.value = val;
          o.textContent = lab;
          if (String(values[f.key]) === String(val)) o.selected = true;
          sel.appendChild(o);
        }
        sel.addEventListener("change", () => {
          values[f.key] = sel.value;
        });
        makeRow(f.label, sel);
      } else if (f.type === "textarea") {
        const inp = document.createElement("textarea");
        inp.value = String(values[f.key] ?? "");
        inp.placeholder = f.placeholder || "";
        inp.spellcheck = false;
        inp.rows = f.rows || 6;
        inp.addEventListener("input", () => {
          values[f.key] = inp.value;
        });
        makeRow(f.label, inp);
      }
    }
    saveBtn.onclick = async () => {
      try {
        const payload = { ...values };
        delete payload._schema;
        for (const f of fields._schema || []) {
          if (f.type !== "hex") continue;
          let hex = String(payload[f.key] || "").trim();
          if (!hex) continue;
          if (!hex.startsWith("#")) hex = `#${hex}`;
          if (/^#[0-9A-Fa-f]{3}$/.test(hex)) {
            hex = `#${hex[1]}${hex[1]}${hex[2]}${hex[2]}${hex[3]}${hex[3]}`;
          }
          if (!/^#[0-9A-Fa-f]{6}$/.test(hex)) {
            throw new Error(`${f.label}: use a hex color like #e8eef2`);
          }
          payload[f.key] = hex.toLowerCase();
        }
        await onSave(payload);
        if (typeof dlg.close === "function") dlg.close();
        else dlg.removeAttribute("open");
      } catch (e) {
        dashboardBanner(e.message, "err");
      }
    };
    if (typeof dlg.showModal === "function") dlg.showModal();
    else dlg.setAttribute("open", "open");
  }

  function openSectionSettings(sec) {
    openSettingsPopup({
      title: `Section · ${sec.title || "Settings"}`,
      fields: {
        title: sec.title || "Section",
        width_px: Number(sec.width_px) || 0,
        height_px: Number(sec.height_px) || 0,
        card_mod_style: cardModStyleText(sec.card_mod),
        _schema: [
          { key: "title", label: "Title", type: "text" },
          {
            key: "width_px",
            label: "Width (px, 0 = auto)",
            type: "number",
            min: 0,
            max: 4000,
          },
          {
            key: "height_px",
            label: "Height (px, 0 = auto)",
            type: "number",
            min: 0,
            max: 4000,
          },
          {
            key: "card_mod_style",
            label: "card_mod CSS",
            type: "textarea",
            rows: 7,
            placeholder: ".dash-card {\n  /* or ha-card */\n}",
          },
        ],
      },
      onSave: (payload) =>
        patchSectionFields(sec.id, {
          title: payload.title,
          width_px: payload.width_px,
          height_px: payload.height_px,
          card_mod: { style: payload.card_mod_style || "" },
        }),
    });
  }

  function openWidgetSettings(w) {
    const defaultName = w.control?.label || w.control_id || "Card";
    openSettingsPopup({
      title: `Card · ${dashWidgetLabel(w)}`,
      fields: {
        custom_name: w.custom_name || "",
        width_px: Number(w.width_px) || 120,
        height_px: Number(w.height_px) || 120,
        color_on: w.color_on || "#e8eef2",
        color_off: w.color_off || "#3a4248",
        control_ui: w.control_ui || "auto",
        icon_on: w.icon_on || "",
        icon_off: w.icon_off || "",
        card_mod_style: cardModStyleText(w.card_mod),
        _schema: [
          {
            key: "custom_name",
            label: "Custom name",
            type: "text",
            placeholder: defaultName,
          },
          {
            key: "width_px",
            label: "Width (px)",
            type: "number",
            min: 48,
            max: 4000,
          },
          {
            key: "height_px",
            label: "Height (px)",
            type: "number",
            min: 48,
            max: 4000,
          },
          {
            key: "color_on",
            label: "On color (hex)",
            type: "hex",
            placeholder: "#e8eef2",
          },
          {
            key: "color_off",
            label: "Off color (hex)",
            type: "hex",
            placeholder: "#3a4248",
          },
          {
            key: "control_ui",
            label: "Slider / dropdown",
            type: "select",
            options: [
              ["auto", "Auto (inline when large)"],
              ["inline", "Always on card"],
              ["popup", "Always popup"],
            ],
          },
          { key: "icon_on", label: "On icon (mdi:…)", type: "text" },
          { key: "icon_off", label: "Off icon (mdi:…)", type: "text" },
          {
            key: "card_mod_style",
            label: "card_mod CSS (custom design)",
            type: "textarea",
            rows: 8,
            placeholder:
              ".dash-card {\n  background: linear-gradient(...);\n}\n.dash-card-name {\n  font-size: 1.1rem;\n}",
          },
        ],
      },
      onSave: (payload) =>
        patchWidgetFields(w.id, {
          custom_name: payload.custom_name || "",
          width_px: payload.width_px,
          height_px: payload.height_px,
          color_on: payload.color_on,
          color_off: payload.color_off,
          control_ui: payload.control_ui,
          icon_on: payload.icon_on,
          icon_off: payload.icon_off,
          card_mod: { style: payload.card_mod_style || "" },
        }),
    });
    // Extra icon pickers after schema rows
    const body = $("dashboard-settings-body");
    if (body) {
      const row = document.createElement("div");
      row.className = "dashboard-settings-row";
      row.style.flexDirection = "row";
      row.style.flexWrap = "wrap";
      row.style.gap = "0.4rem";
      const mk = (layer, label, current) => {
        const b = document.createElement("button");
        b.type = "button";
        b.className = "btn-ghost";
        b.textContent = label;
        b.addEventListener("click", () => {
          openIconPicker({ widgetId: w.id, layer, current });
        });
        return b;
      };
      row.appendChild(mk("on", "Pick on icon", w.icon_on));
      row.appendChild(mk("off", "Pick off icon", w.icon_off));
      body.appendChild(row);
    }
  }

  function buildDashboardWidget(w) {
    const control = w.control;
    const shell = document.createElement("article");
    const shape = w.shape || "square";
    const size = w.size || "md";
    const kind = control?.kind || "";
    const widthPx = Number(w.width_px) || 120;
    const heightPx = Number(w.height_px) || 120;
    const controlUi = w.control_ui || "auto";
    shell.className = `dashboard-widget dash-button shape-${shape} size-custom`;
    shell.dataset.widgetId = w.id;
    shell.dataset.controlId = w.control_id;
    shell.dataset.controlLayout = w.control_layout || "less";
    shell.dataset.shape = shape;
    shell.dataset.size = size;
    shell.dataset.widthPx = String(widthPx);
    shell.dataset.heightPx = String(heightPx);
    shell.dataset.controlUi = controlUi;
    shell.dataset.kind = kind;
    shell.dataset.iconOn = w.icon_on || "";
    shell.dataset.iconOff = w.icon_off || "";
    shell.dataset.customName = w.custom_name || "";
    shell.dataset.defaultLabel = control?.label || w.control_id || "Card";
    const wMod = cardModStyleText(w.card_mod);
    if (wMod) shell.dataset.cardMod = wMod;
    else delete shell.dataset.cardMod;
    shell.style.width = `${widthPx}px`;
    shell.style.height = `${heightPx}px`;
    shell.style.flex = `0 0 ${widthPx}px`;
    applyDashCardColors(shell, w);
    if (control) {
      shell.dataset.onLabel =
        control.on_label ||
        (String(control.id).includes("mute") ? "Muted" : "On");
      shell.dataset.offLabel =
        control.off_label ||
        (control.id === "pw_power"
          ? "Standby"
          : String(control.id).includes("mute")
            ? "Unmuted"
            : "Off");
    }

    if (state.dashboardEdit) {
      shell.addEventListener("dragover", (ev) => {
        if (state.dashboardDrag?.type !== "widget") return;
        ev.preventDefault();
        ev.stopPropagation();
        shell.classList.add("drag-over");
      });
      shell.addEventListener("dragleave", (ev) => {
        if (!shell.contains(ev.relatedTarget)) shell.classList.remove("drag-over");
      });
      shell.addEventListener("drop", (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        shell.classList.remove("drag-over");
        const drag = state.dashboardDrag;
        if (!drag || drag.type !== "widget" || drag.id === w.id) return;
        const from = document.querySelector(
          `.dashboard-widget[data-widget-id="${CSS.escape(drag.id)}"]`
        );
        if (from && shell.parentElement) {
          shell.parentElement.insertBefore(from, shell);
          persistDashboardFromDom().catch((e) => dashboardBanner(e.message, "err"));
        }
      });

      const toolbar = document.createElement("div");
      toolbar.className = "dashboard-widget-toolbar";
      const handle = document.createElement("span");
      handle.className = "dashboard-drag-handle";
      handle.title = "Drag widget";
      handle.textContent = "⠿";
      handle.draggable = true;
      handle.addEventListener("dragstart", (ev) => {
        state.dashboardDrag = { type: "widget", id: w.id };
        shell.classList.add("is-dragging");
        ev.dataTransfer.effectAllowed = "move";
        ev.stopPropagation();
      });
      handle.addEventListener("dragend", () => {
        shell.classList.remove("is-dragging");
        state.dashboardDrag = null;
        clearDashDragOver();
      });
      toolbar.appendChild(handle);
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "dashboard-widget-remove";
      remove.textContent = "×";
      remove.title = "Remove widget";
      remove.addEventListener("click", (ev) => {
        ev.stopPropagation();
        api(`/api/dashboard/widgets/${w.id}`, { method: "DELETE" })
          .then((d) => {
            state.dashboard = d;
            renderDashboard();
          })
          .catch((e) => dashboardBanner(e.message, "err"));
      });
      shell.appendChild(toolbar);
      shell.appendChild(remove);
    }

    // HA button-card style body (matt8707/hass-config inspiration)
    const card = document.createElement(state.dashboardEdit ? "div" : "button");
    card.className = "dash-card";
    card.dataset.role = "dash-card";
    if (card.tagName === "BUTTON") card.type = "button";

    const canSlide =
      control &&
      (kind === "stepper" || kind === "slider") &&
      control.min != null &&
      control.max != null &&
      !Number.isNaN(Number(control.min)) &&
      !Number.isNaN(Number(control.max));
    if (canSlide) {
      shell.dataset.sliderMin = String(control.min);
      shell.dataset.sliderMax = String(control.max);
      if (control.zero_db != null) {
        shell.dataset.sliderZero = String(control.zero_db);
      }
    }

    const icon = buildDashIconHost(w);
    icon.classList.add("dash-card-icon");
    const name = document.createElement("span");
    name.className = "dash-card-name";
    name.textContent = dashWidgetLabel(w);
    const stateEl = document.createElement("span");
    stateEl.className = "dash-card-state";
    stateEl.dataset.role = "dash-state";

    card.appendChild(icon);
    card.appendChild(name);
    card.appendChild(stateEl);

    const hasBadge = canSlide || kind === "enum" || kind === "toggle";
    if (hasBadge) {
      const valueBadge = document.createElement("span");
      valueBadge.className = "dash-card-value";
      valueBadge.dataset.role = "dash-value-badge";
      valueBadge.textContent = "—";
      card.appendChild(valueBadge);
      card.classList.add("has-value-badge");
    }

    if (state.dashboardEdit) {
      card.classList.add("dash-card-edit");
      card.title = "Click to edit card settings";
      card.addEventListener("click", (ev) => {
        ev.stopPropagation();
        openWidgetSettings(w);
      });
    } else if (control) {
      const inline = wantsInlineControl(w);
      if (kind === "toggle") {
        card.title = `Toggle ${control.label}`;
        card.addEventListener("click", () => {
          bounceDashCard(shell);
          const ent = controlEntity(control.id);
          const currentlyOn = ent?.on === true || ent?.value === true;
          runControlCommand({
            id: control.id,
            value: !currentlyOn,
            confirm: Boolean(control.confirm),
            confirmMessage: control.confirm_message,
          });
        });
      } else if (kind === "enum") {
        if (inline) {
          card.title = control.label || "Select";
          card.classList.add("has-inline-control");
          mountInlineEnum(card, control);
        } else {
          card.title = `Choose ${control.label}`;
          card.classList.add("has-popup");
          card.addEventListener("click", () => {
            bounceDashCard(shell);
            openEnumPopup(control);
          });
        }
      } else if (kind === "action" || kind === "query") {
        card.addEventListener("click", () => {
          bounceDashCard(shell);
          runControlCommand({
            id: control.id,
            confirm: Boolean(control.confirm),
            confirmMessage: control.confirm_message,
          });
        });
      } else if (kind === "stepper" || kind === "slider") {
        if (canSlide && inline) {
          card.title = control.label || "Adjust";
          card.classList.add("has-inline-control", "has-slider");
          mountInlineSlider(card, control);
        } else if (canSlide) {
          card.title = `Adjust ${control.label} (slider)`;
          card.classList.add("has-popup", "has-slider");
          card.addEventListener("click", () => {
            bounceDashCard(shell);
            openSliderPopup(control, w.id);
          });
        } else {
          card.title = control.label || "Control";
          card.addEventListener("click", () => bounceDashCard(shell));
        }
      } else {
        card.addEventListener("click", () => bounceDashCard(shell));
      }
    }

    if (!control) {
      stateEl.textContent = "Missing";
      card.disabled = true;
    }

    shell.appendChild(card);
    applyCardMod(shell, w.card_mod, w.id);
    return shell;
  }

  async function loadDashboardYamlEditor() {
    const ta = $("dashboard-yaml-text");
    if (!ta) return;
    const data = await api("/api/dashboard/yaml");
    ta.value = data.yaml || "";
  }

  async function openDashboardYamlEditor() {
    if (!state.dashboardEdit) {
      dashboardBanner("Turn on Customize to edit YAML", "warn");
      return;
    }
    const dlg = $("dashboard-yaml-editor");
    if (!dlg) return;
    try {
      await loadDashboardYamlEditor();
      if (typeof dlg.showModal === "function") dlg.showModal();
      else dlg.setAttribute("open", "open");
    } catch (e) {
      dashboardBanner(e.message, "err");
    }
  }

  async function saveDashboardYamlEditor() {
    const ta = $("dashboard-yaml-text");
    const dlg = $("dashboard-yaml-editor");
    if (!ta) return;
    try {
      const data = await api("/api/dashboard/yaml", {
        method: "PUT",
        body: JSON.stringify({ yaml: ta.value }),
      });
      state.dashboard = data;
      renderDashboard();
      dashboardBanner("Dashboard YAML saved", "ok");
      if (dlg) {
        if (typeof dlg.close === "function") dlg.close();
        else dlg.removeAttribute("open");
      }
    } catch (e) {
      dashboardBanner(e.message, "err");
    }
  }

  function openDashboardPicker(sectionId) {
    const dlg = $("dashboard-picker");
    const secSel = $("dashboard-picker-section");
    const layoutSel = $("dashboard-picker-layout");
    const search = $("dashboard-picker-search");
    if (!dlg || !secSel) return;
    secSel.innerHTML = "";
    for (const sec of state.dashboard?.sections || []) {
      const o = document.createElement("option");
      o.value = sec.id;
      o.textContent = sec.title;
      if (sec.id === sectionId) o.selected = true;
      secSel.appendChild(o);
    }
    const refreshList = () => renderDashboardPickerList();
    layoutSel.onchange = refreshList;
    search.oninput = refreshList;
    renderDashboardPickerList();
    if (typeof dlg.showModal === "function") dlg.showModal();
    else dlg.setAttribute("open", "open");
  }

  function renderDashboardPickerList() {
    const list = $("dashboard-picker-list");
    const layout = $("dashboard-picker-layout")?.value || "less";
    const q = ($("dashboard-picker-search")?.value || "").trim().toLowerCase();
    const cat = state.dashboardCatalog?.[layout];
    if (!list || !cat) return;
    list.innerHTML = "";
    const controls = (cat.controls || []).filter((c) => {
      if (!q) return true;
      return (
        String(c.label || "").toLowerCase().includes(q) ||
        String(c.id || "").toLowerCase().includes(q) ||
        String(c.section || "").toLowerCase().includes(q)
      );
    });
    for (const c of controls) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "dashboard-picker-item";
      btn.innerHTML = `<strong>${c.label}</strong><span>${c.section} · ${c.kind} · ${layout}</span>`;
      btn.addEventListener("click", () => {
        const sectionId = $("dashboard-picker-section")?.value;
        if (!sectionId) return;
        const defaults = DASH_DEFAULT_ICONS[c.id] || {
          on: "mdi:tune",
          off: "mdi:tune",
        };
        api("/api/dashboard/widgets", {
          method: "POST",
          body: JSON.stringify({
            section_id: sectionId,
            control_id: c.id,
            control_layout: layout,
            icon_on: defaults.on,
            icon_off: defaults.off,
          }),
        })
          .then((d) => {
            state.dashboard = d;
            renderDashboard();
            dashboardBanner(`Added ${c.label}`, "ok");
          })
          .catch((e) => dashboardBanner(e.message, "err"));
      });
      list.appendChild(btn);
    }
    if (!controls.length) {
      list.innerHTML = "<p class='meta'>No matching controls</p>";
    }
  }

  function setIconPickerStatus(text, kind) {
    const el = $("icon-picker-status");
    if (!el) return;
    if (!text) {
      el.hidden = true;
      el.textContent = "";
      return;
    }
    el.hidden = false;
    el.textContent = text;
    el.classList.toggle("err", kind === "err");
  }

  async function openIconPicker({ widgetId, layer, current }) {
    await ensureDashboardIcons({ force: true });
    state.dashboardIconTarget = {
      widgetId,
      layer,
      selected: current || "",
    };
    const dlg = $("dashboard-icon-picker");
    const search = $("icon-picker-search");
    const manual = $("icon-picker-manual");
    if (search) search.value = "";
    if (manual) manual.value = current || "";
    setIconPickerStatus(`Pick ${layer === "on" ? "On" : "Off"} icon`);
    renderIconPickerList();
    if (typeof dlg.showModal === "function") dlg.showModal();
    else dlg.setAttribute("open", "open");
  }

  function renderIconPickerList() {
    const list = $("icon-picker-list");
    if (!list) return;
    const q = ($("icon-picker-search")?.value || "").trim().toLowerCase();
    const selected = state.dashboardIconTarget?.selected || "";
    list.innerHTML = "";

    const custom = state.dashboardIcons?.custom || [];
    for (const c of custom) {
      if (q && !String(c.name || "").toLowerCase().includes(q)) continue;
      list.appendChild(
        buildIconPickerItem({
          ref: c.ref,
          label: c.name,
          preview: { type: "custom", url: c.url },
          selected: selected === c.ref,
        })
      );
    }

    const suggestions = state.dashboardIcons?.mdi_suggestions || [];
    for (const ref of suggestions) {
      const name = ref.replace(/^mdi:/, "");
      if (q && !name.includes(q) && !ref.includes(q)) continue;
      list.appendChild(
        buildIconPickerItem({
          ref,
          label: name,
          preview: dashIconRef(ref),
          selected: selected === ref,
        })
      );
    }

    if (q && /^[a-z0-9-]+$/i.test(q) && !suggestions.some((r) => r.includes(q))) {
      const ref = q.startsWith("mdi:") ? q : `mdi:${q}`;
      list.appendChild(
        buildIconPickerItem({
          ref,
          label: `Use ${ref}`,
          preview: dashIconRef(ref),
          selected: selected === ref,
        })
      );
    }
  }

  function buildIconPickerItem({ ref, label, preview, selected }) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "icon-picker-item" + (selected ? " is-selected" : "");
    btn.dataset.ref = ref;
    const previewEl = document.createElement("span");
    previewEl.className = "icon-picker-preview";
    if (preview?.type === "custom" && preview.url) {
      const img = document.createElement("img");
      img.src = preview.url;
      img.alt = "";
      previewEl.appendChild(img);
    } else {
      const i = document.createElement("i");
      i.className = `mdi ${preview?.class || "mdi-tune"}`;
      previewEl.appendChild(i);
    }
    const text = document.createElement("span");
    text.textContent = label;
    btn.appendChild(previewEl);
    btn.appendChild(text);
    btn.addEventListener("click", () => {
      if (state.dashboardIconTarget) {
        state.dashboardIconTarget.selected = ref;
      }
      if ($("icon-picker-manual")) $("icon-picker-manual").value = ref;
      renderIconPickerList();
    });
    return btn;
  }

  async function applyIconPickerSelection() {
    const target = state.dashboardIconTarget;
    if (!target?.widgetId) return;
    let ref =
      ($("icon-picker-manual")?.value || "").trim() || target.selected || "";
    if (!ref) {
      setIconPickerStatus("Select or type an icon ref", "err");
      return;
    }
    if (!ref.startsWith("mdi:") && !ref.startsWith("custom:")) {
      ref = `mdi:${ref.replace(/^mdi-/, "")}`;
    }
    const fields =
      target.layer === "on" ? { icon_on: ref } : { icon_off: ref };
    try {
      await patchWidgetFields(target.widgetId, fields);
      const dlg = $("dashboard-icon-picker");
      if (dlg?.open) dlg.close();
      dashboardBanner("Icon updated", "ok");
    } catch (e) {
      setIconPickerStatus(e.message, "err");
    }
  }

  async function uploadIconFile(file) {
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    fd.append("name", file.name.replace(/\.[^.]+$/, "") || "icon");
    setIconPickerStatus("Uploading…");
    try {
      const res = await fetch("/api/dashboard/icons/upload", {
        method: "POST",
        body: fd,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || res.statusText);
      await ensureDashboardIcons({ force: true });
      if (state.dashboardIconTarget) {
        state.dashboardIconTarget.selected = data.icon.ref;
      }
      if ($("icon-picker-manual")) $("icon-picker-manual").value = data.icon.ref;
      renderIconPickerList();
      setIconPickerStatus(`Stored ${data.icon.name} locally`);
    } catch (e) {
      setIconPickerStatus(e.message, "err");
    }
  }

  async function fetchIconFromUrl() {
    const url = ($("icon-picker-url")?.value || "").trim();
    if (!url) {
      setIconPickerStatus("Enter a URL", "err");
      return;
    }
    setIconPickerStatus("Fetching…");
    try {
      const data = await api("/api/dashboard/icons/from-url", {
        method: "POST",
        body: JSON.stringify({ url }),
      });
      await ensureDashboardIcons({ force: true });
      if (state.dashboardIconTarget) {
        state.dashboardIconTarget.selected = data.icon.ref;
      }
      if ($("icon-picker-manual")) $("icon-picker-manual").value = data.icon.ref;
      renderIconPickerList();
      setIconPickerStatus(`Stored ${data.icon.name} locally`);
    } catch (e) {
      setIconPickerStatus(e.message, "err");
    }
  }

  function wireDashboard() {
    $("dashboard-customize")?.addEventListener("click", () =>
      setDashboardEdit(!state.dashboardEdit)
    );
    $("dashboard-raw-yaml")?.addEventListener("click", () => openDashboardYamlEditor());
    $("dashboard-yaml-reload")?.addEventListener("click", () =>
      loadDashboardYamlEditor().catch((e) => dashboardBanner(e.message, "err"))
    );
    $("dashboard-yaml-save")?.addEventListener("click", () => saveDashboardYamlEditor());
    $("dashboard-add-section")?.addEventListener("click", () => {
      const title = window.prompt("Section title", "New section");
      if (title == null) return;
      const layoutId =
        state.dashboard?.layouts?.[0]?.id ||
        null;
      api("/api/dashboard/sections", {
        method: "POST",
        body: JSON.stringify({
          title: title.trim() || "New section",
          layout_id: layoutId,
        }),
      })
        .then((d) => {
          state.dashboard = d;
          renderDashboard();
        })
        .catch((e) => dashboardBanner(e.message, "err"));
    });
    $("dashboard-add-layout")?.addEventListener("click", () => {
      const stack =
        window.prompt("Layout stack: horizontal or vertical", "horizontal") ||
        "horizontal";
      api("/api/dashboard/layouts", {
        method: "POST",
        body: JSON.stringify({
          stack: /vert/i.test(stack) ? "vertical" : "horizontal",
        }),
      })
        .then((d) => {
          state.dashboard = d;
          renderDashboard();
        })
        .catch((e) => dashboardBanner(e.message, "err"));
    });
    $("dashboard-refresh")?.addEventListener("click", () =>
      loadDashboard({ force: true }).catch((e) => dashboardBanner(e.message, "err"))
    );
    $("icon-picker-search")?.addEventListener("input", () => renderIconPickerList());
    $("icon-picker-apply")?.addEventListener("click", () =>
      applyIconPickerSelection()
    );
    $("icon-picker-file")?.addEventListener("change", (ev) => {
      const file = ev.target.files?.[0];
      uploadIconFile(file).finally(() => {
        ev.target.value = "";
      });
    });
    $("icon-picker-url-btn")?.addEventListener("click", () => fetchIconFromUrl());
  }

  initTheme();
  wireTabs();
  wireMqttPage();
  $("field-form")?.addEventListener("submit", (ev) => ev.preventDefault());
  wireControlPanel();
  wireDashboard();
  wireActivity();
  wireEditModeToggle();
  renderActivityBadge();
  $("reconnect-btn").addEventListener("click", () => boot({ preserveNav: true }));
  $("editor-primary-btn").addEventListener("click", () => {
    onEditorPrimaryClick().catch((err) => setStatus(err.message, "err"));
  });
  $("info-refresh").addEventListener("click", () => loadInfoDashboard(true));
  $("power-btn")?.addEventListener("click", () => togglePower());
  $("settings-save")?.addEventListener("click", () => saveSettingsPage());
  $("settings-reset")?.addEventListener("click", () => resetSettingsPage());

  window.addEventListener("hashchange", () => {
    if (_routeFromCode || !state.connected) return;
    applyRouteFromHash().catch((err) => setStatus(err.message, "err"));
  });

  boot();
})();
