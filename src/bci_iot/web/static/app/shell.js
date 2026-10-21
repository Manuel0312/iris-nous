(() => {
  const PHOTO_SRC = [
    { src: "/static/product/headset.jpg", alt: "Cuffia" },
    { src: "/static/product/phone.jpg", alt: "Telefono" },
    { src: "/static/product/music.jpg", alt: "Musica" },
    { src: "/static/product/home.jpg", alt: "Casa" },
    { src: "/static/product/connect.jpg", alt: "Connessione" },
  ];

  const INTERVAL_MS = 7000;
  const THEME_KEY = "iris-app-theme";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  function loadI18n() {
    const el = document.getElementById("shell-i18n");
    if (!el) return {};
    try {
      return JSON.parse(el.textContent || "{}");
    } catch (_) {
      return {};
    }
  }
  const I18N = loadI18n();
  const msg = (key, fallback) => (I18N[key] != null && I18N[key] !== "" ? I18N[key] : fallback);

  const SLIDE_TITLES = Array.isArray(I18N.slideTitles) ? I18N.slideTitles : [];
  const SLIDE_BODIES = Array.isArray(I18N.slideBodies) ? I18N.slideBodies : [];
  const PHOTOS = PHOTO_SRC.map((p, i) => ({
    ...p,
    title: SLIDE_TITLES[i] || "",
    body: SLIDE_BODIES[i] || "",
  }));

  let index = 0;
  let timer = null;
  let carouselOn = false;
  let profile = null;
  let accountMode = "view";

  function genderLabel(code) {
    if (code === "female") return msg("genderFemale", "Donna");
    if (code === "male") return msg("genderMale", "Uomo");
    if (code === "non_binary") return msg("genderNonBinary", "Non binario");
    return msg("notSet", "Non impostato");
  }

  function phoneLabel(data) {
    const display = String((data && data.phone_display) || "").trim();
    if (display) return display;
    const dial = String((data && data.phone_dial) || "").trim();
    const national = String((data && data.phone_national) || "").replace(/\D+/g, "");
    if (dial && national) return dial + " " + national;
    if (national) return national;
    return msg("notSet", "Non impostato");
  }

  function setAccountMode(mode, { justSaved } = {}) {
    accountMode = mode === "edit" ? "edit" : "view";
    const root = $("#account-user");
    const summary = $("#account-summary");
    const edit = $("#account-edit");
    const banner = $("#saved-banner");
    if (root) root.dataset.mode = accountMode;
    if (summary) summary.hidden = accountMode !== "view";
    if (edit) edit.hidden = accountMode !== "edit";
    if (banner) {
      if (justSaved && accountMode === "view") {
        banner.hidden = false;
        banner.textContent = msg("profileUpdated", "Profilo aggiornato. Ecco i tuoi dati.");
      } else if (accountMode === "edit") {
        banner.hidden = true;
      }
    }
    if (accountMode === "edit") setHint($("#profile-hint"));
  }

  function renderSummary(data) {
    if (!data) return;
    const first = String(data.first_name || "").trim();
    const last = String(data.last_name || "").trim();
    const full = [first, last].filter(Boolean).join(" ") || String(data.username || "").trim() || "—";
    const nameEl = $("#summary-name");
    const userEl = $("#summary-username");
    const emailEl = $("#summary-email");
    const phoneEl = $("#summary-phone");
    const genderEl = $("#summary-gender");
    if (nameEl) nameEl.textContent = full;
    if (userEl) userEl.textContent = data.username ? "@" + data.username : "";
    if (emailEl) emailEl.textContent = String(data.email || "").trim() || msg("notSet", "Non impostato");
    if (phoneEl) phoneEl.textContent = phoneLabel(data);
    if (genderEl) genderEl.textContent = genderLabel(data.gender);
  }

  function themeFromHour() {
    const h = new Date().getHours();
    return h >= 7 && h < 20 ? "light" : "dark";
  }

  function getThemeChoice() {
    try {
      const v = localStorage.getItem(THEME_KEY);
      if (v === "light" || v === "dark" || v === "auto") return v;
    } catch (_) {}
    return "auto";
  }

  function themeLabel(mode) {
    if (mode === "light") return msg("themeLight", "Chiaro");
    if (mode === "dark") return msg("themeDark", "Scuro");
    return msg("themeAuto", "Automatico (ora)");
  }

  function applyTheme(choice) {
    const mode = choice || getThemeChoice();
    const resolved = mode === "auto" ? themeFromHour() : mode;
    const root = document.documentElement;
    root.setAttribute("data-theme", mode);
    root.setAttribute("data-theme-resolved", resolved);
    root.style.colorScheme = resolved;
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", resolved === "dark" ? "#0b0b0d" : "#f5f5f7");
    $$(".theme-choice").forEach((btn) => {
      btn.classList.toggle("on", btn.getAttribute("data-theme-choice") === mode);
    });
    const cur = $("#settings-theme-current");
    if (cur) cur.textContent = themeLabel(mode);
  }

  function show(name) {
    $$(".screen").forEach((el) => el.classList.toggle("on", el.dataset.screen === name));
    $$(".shell-tabs .tab").forEach((el) =>
      el.classList.toggle("on", el.getAttribute("data-go") === name)
    );
    if (name === "iris") startCarousel();
    else stopCarousel();
    if (name === "account") refreshAccount();
  }

  function renderSlide(i, animate) {
    const slide = PHOTOS[i];
    const img = $("#iris-photo-img");
    const titleEl = $("#explain-title");
    const bodyEl = $("#explain-body");
    const card = $("#explain-card");
    if (!img || !slide) return;
    if (animate) {
      img.classList.remove("is-swap");
      void img.offsetWidth;
      img.classList.add("is-swap");
      if (card) {
        card.classList.remove("is-swap");
        void card.offsetWidth;
        card.classList.add("is-swap");
      }
    }
    img.src = slide.src;
    img.alt = slide.alt;
    if (titleEl && slide.title) titleEl.textContent = slide.title;
    if (bodyEl && slide.body) bodyEl.textContent = slide.body;
    $$("#popup-dots button").forEach((btn, n) => {
      btn.classList.toggle("on", n === i);
      btn.setAttribute("aria-current", n === i ? "true" : "false");
    });
  }

  function go(i, animate = true) {
    index = (i + PHOTOS.length) % PHOTOS.length;
    renderSlide(index, animate);
  }

  function next() {
    go(index + 1, true);
  }

  function prev() {
    go(index - 1, true);
  }

  function stopCarousel() {
    carouselOn = false;
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
  }

  function startCarousel() {
    stopCarousel();
    carouselOn = true;
    go(index, false);
    timer = setInterval(() => {
      if (carouselOn) next();
    }, INTERVAL_MS);
  }

  function buildDots() {
    const host = $("#popup-dots");
    if (!host) return;
    host.innerHTML = "";
    PHOTOS.forEach((_, n) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.setAttribute("aria-label", `Foto ${n + 1}`);
      btn.addEventListener("click", () => {
        go(n, true);
        if (carouselOn) startCarousel();
      });
      host.appendChild(btn);
    });
  }

  function bindIrisSwipe() {
    const stage = $(".iris-stage");
    if (!stage) return;
    let startX = 0;
    let startY = 0;
    let tracking = false;

    const onStart = (x, y) => {
      startX = x;
      startY = y;
      tracking = true;
    };
    const onEnd = (x, y) => {
      if (!tracking) return;
      tracking = false;
      const dx = x - startX;
      const dy = y - startY;
      if (Math.abs(dx) < 48 || Math.abs(dx) < Math.abs(dy)) return;
      if (dx < 0) next();
      else prev();
      if (carouselOn) startCarousel();
    };

    stage.addEventListener(
      "touchstart",
      (e) => {
        const t = e.changedTouches[0];
        if (t) onStart(t.clientX, t.clientY);
      },
      { passive: true }
    );
    stage.addEventListener(
      "touchend",
      (e) => {
        const t = e.changedTouches[0];
        if (t) onEnd(t.clientX, t.clientY);
      },
      { passive: true }
    );

    let mouseDown = false;
    stage.addEventListener("mousedown", (e) => {
      mouseDown = true;
      onStart(e.clientX, e.clientY);
    });
    stage.addEventListener("mouseup", (e) => {
      if (!mouseDown) return;
      mouseDown = false;
      onEnd(e.clientX, e.clientY);
    });
    stage.addEventListener("mouseleave", () => {
      mouseDown = false;
      tracking = false;
    });
  }

  function setDropdownOpen(kind, open) {
    const block = kind === "theme" ? $(".settings-theme-block") : $(".settings-lang-block");
    const list = kind === "theme" ? $("#settings-themes") : $("#settings-langs");
    const toggle = kind === "theme" ? $("#settings-theme-toggle") : $("#settings-lang-toggle");
    if (block) block.dataset.open = open ? "1" : "0";
    if (list) {
      list.hidden = !open;
      if (!open) list.setAttribute("hidden", "");
      else list.removeAttribute("hidden");
    }
    if (toggle) toggle.setAttribute("aria-expanded", open ? "true" : "false");
  }

  function closeAllDropdowns() {
    setDropdownOpen("theme", false);
    setDropdownOpen("lang", false);
  }

  function openSettings() {
    const panel = $("#settings-panel");
    const backdrop = $("#settings-backdrop");
    if (!panel) return;
    closeAllDropdowns();
    panel.hidden = false;
    if (backdrop) backdrop.hidden = false;
    document.body.classList.add("settings-open");
  }

  function closeSettings() {
    const panel = $("#settings-panel");
    const backdrop = $("#settings-backdrop");
    if (panel) panel.hidden = true;
    if (backdrop) backdrop.hidden = true;
    document.body.classList.remove("settings-open");
    closeAllDropdowns();
  }

  function bindSettings() {
    $("#settings-open")?.addEventListener("click", openSettings);
    $("#settings-close")?.addEventListener("click", closeSettings);
    $("#settings-backdrop")?.addEventListener("click", closeSettings);

    $("#settings-theme-toggle")?.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      const block = $(".settings-theme-block");
      const open = !(block && block.dataset.open === "1");
      setDropdownOpen("lang", false);
      setDropdownOpen("theme", open);
    });

    $("#settings-lang-toggle")?.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      const block = $(".settings-lang-block");
      const open = !(block && block.dataset.open === "1");
      setDropdownOpen("theme", false);
      setDropdownOpen("lang", open);
    });

    document.addEventListener("click", (e) => {
      const t = e.target;
      const themeBlock = $(".settings-theme-block");
      const langBlock = $(".settings-lang-block");
      if (themeBlock && themeBlock.dataset.open === "1" && !(t instanceof Node && themeBlock.contains(t))) {
        setDropdownOpen("theme", false);
      }
      if (langBlock && langBlock.dataset.open === "1" && !(t instanceof Node && langBlock.contains(t))) {
        setDropdownOpen("lang", false);
      }
    });

    $$(".theme-choice").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        const choice = btn.getAttribute("data-theme-choice");
        try {
          localStorage.setItem(THEME_KEY, choice);
        } catch (_) {}
        applyTheme(choice);
        setDropdownOpen("theme", false);
      });
    });

    // Re-evaluate auto theme every minute (hour boundary).
    setInterval(() => {
      if (getThemeChoice() === "auto") applyTheme("auto");
    }, 60_000);
  }

  function bindWhatsNew() {
    const newsOpen = $("#whats-new-open");
    const newsOverlay = $("#whats-new-overlay");
    const newsDialog = $("#whats-new-dialog");
    const newsClose = $("#whats-new-close");
    const newsDot = $("#whats-new-dot");
    const newsVersion = String(I18N.version || "");
    const newsSeenKey = "iris_whats_new_seen_" + newsVersion;

    function newsSeen() {
      try {
        return localStorage.getItem(newsSeenKey) === "1";
      } catch (_) {
        return false;
      }
    }
    function markNewsSeen() {
      try {
        localStorage.setItem(newsSeenKey, "1");
      } catch (_) {}
      if (newsDot) newsDot.hidden = true;
    }
    function openNews() {
      if (!newsOverlay) return;
      closeSettings();
      newsOverlay.hidden = false;
      document.body.classList.add("whats-new-open");
      if (newsDialog) newsDialog.focus();
      markNewsSeen();
    }
    function closeNews() {
      if (!newsOverlay) return;
      newsOverlay.hidden = true;
      document.body.classList.remove("whats-new-open");
    }
    if (newsDot && !newsSeen()) newsDot.hidden = false;
    newsOpen?.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      openNews();
    });
    newsClose?.addEventListener("click", (e) => {
      e.preventDefault();
      closeNews();
    });
    newsOverlay?.addEventListener("click", (e) => {
      if (e.target === newsOverlay) closeNews();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && newsOverlay && !newsOverlay.hidden) closeNews();
    });
  }

  function setHint(el, text, kind) {
    if (!el) return;
    if (!text) {
      el.hidden = true;
      el.textContent = "";
      el.classList.remove("ok", "err");
      return;
    }
    el.hidden = false;
    el.textContent = text;
    el.classList.toggle("ok", kind === "ok");
    el.classList.toggle("err", kind === "err");
  }

  function showAccountState(name) {
    ["account-loading", "account-guest", "account-user"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.hidden = id !== name;
    });
  }

  function setProfilePhoto(url) {
    const hero = $("#profile-hero");
    const img = $("#profile-photo");
    const fallback = $("#profile-photo-fallback");
    const cta = $("#photo-cta-label");
    const has = Boolean(url);
    if (hero) hero.dataset.hasPhoto = has ? "1" : "0";
    if (cta) cta.textContent = has ? msg("changePhoto", "Cambia foto") : msg("choosePhoto", "Scegli una foto");
    if (!img) return;
    img.onload = () => {
      img.hidden = false;
      if (fallback) fallback.hidden = true;
    };
    img.onerror = () => {
      img.hidden = true;
      img.removeAttribute("src");
      if (fallback) fallback.hidden = false;
      if (hero) hero.dataset.hasPhoto = "0";
      if (cta) cta.textContent = msg("choosePhoto", "Scegli una foto");
    };
    if (has) {
      img.src = url + (url.includes("?") ? "&" : "?") + "t=" + Date.now();
    } else {
      img.hidden = true;
      img.removeAttribute("src");
      if (fallback) fallback.hidden = false;
    }
  }

  function findCountryOption(iso) {
    if (!iso) return null;
    return $$("#phone-cc-list .phone-cc-option").find((el) => el.dataset.iso === iso) || null;
  }

  function applyPhoneCountry(iso, dial, flagSrc, minLen, maxLen, { focus } = {}) {
    const row = $("#phone-row");
    const btn = $("#phone-cc-btn");
    const isoInput = $("#phone-country");
    const national = $("#phone-national");
    const flagEl = $("#phone-cc-flag");
    const dialEl = $("#phone-cc-dial");
    const hint = $("#phone-hint");
    const menu = $("#phone-cc-menu");
    if (!isoInput || !national || !dialEl) return;
    if (!iso) {
      isoInput.value = "";
      if (flagEl) {
        flagEl.src = "/flags/un.svg";
        flagEl.alt = "";
      }
      dialEl.textContent = msg("prefisso", "Prefisso");
      national.value = "";
      national.disabled = true;
      if (row) row.dataset.locked = "0";
      btn?.classList.remove("is-locked");
      if (hint) hint.textContent = msg("phoneHint", "Scegli la bandiera/prefisso, poi digita solo le cifre. Il telefono è opzionale.");
      return;
    }
    isoInput.value = iso;
    if (flagEl && flagSrc) {
      flagEl.src = flagSrc;
      flagEl.alt = iso;
    }
    dialEl.textContent = dial || iso;
    national.disabled = false;
    if (row) row.dataset.locked = "1";
    btn?.classList.add("is-locked");
    if (menu) {
      menu.hidden = true;
      btn?.setAttribute("aria-expanded", "false");
    }
    if (hint && minLen && maxLen) {
      hint.textContent =
        msg("prefissoFissato", "Prefisso fissato") +
        " (" +
        dial +
        "). " +
        msg("digita", "Digita") +
        " " +
        minLen +
        "–" +
        maxLen +
        " " +
        msg("cifreDelNumero", "cifre del numero.");
    }
    if (focus) national.focus();
  }

  function fillProfile(data, { mode, justSaved } = {}) {
    profile = data;
    const form = $("#form-profile");
    if (form) {
      form.first_name.value = data.first_name || "";
      form.last_name.value = data.last_name || "";
      form.email.value = data.email || "";
      const gender = data.gender || "";
      $$('input[name="gender"]', form).forEach((r) => {
        r.checked = r.value === gender;
      });

      const iso = String(data.phone_country || "").trim().toUpperCase();
      const national = $("#phone-national");
      if (iso) {
        const opt = findCountryOption(iso);
        applyPhoneCountry(
          iso,
          data.phone_dial || (opt && opt.dataset.dial) || "",
          (opt && opt.dataset.flagSrc) || `/flags/${iso.toLowerCase() === "uk" ? "gb" : iso.toLowerCase()}.svg`,
          opt && opt.dataset.min,
          opt && opt.dataset.max
        );
        if (national) national.value = String(data.phone_national || "").replace(/\D+/g, "");
      } else {
        applyPhoneCountry("", "", "");
      }
    }

    setProfilePhoto(data.photo_url || "");
    renderSummary(data);

    const nextMode =
      mode ||
      (data.anagrafica_complete || (data.first_name && data.email && data.gender) ? "view" : "edit");
    setAccountMode(nextMode, { justSaved: Boolean(justSaved) });
  }

  function bindPhonePicker() {
    const row = $("#phone-row");
    const btn = $("#phone-cc-btn");
    const menu = $("#phone-cc-menu");
    const filter = $("#phone-cc-filter");
    const list = $("#phone-cc-list");
    const national = $("#phone-national");
    if (!btn || !menu || !list || !national) return;

    btn.addEventListener("click", (e) => {
      e.preventDefault();
      if (row && row.dataset.locked === "1") {
        row.dataset.locked = "0";
        btn.classList.remove("is-locked");
      }
      const open = menu.hidden;
      menu.hidden = !open;
      btn.setAttribute("aria-expanded", open ? "true" : "false");
      if (open && filter) filter.focus();
    });

    list.querySelectorAll(".phone-cc-option").forEach((opt) => {
      opt.addEventListener("click", () => {
        applyPhoneCountry(opt.dataset.iso, opt.dataset.dial, opt.dataset.flagSrc, opt.dataset.min, opt.dataset.max, {
          focus: true,
        });
      });
    });

    filter?.addEventListener("input", () => {
      const q = filter.value.trim().toLowerCase();
      list.querySelectorAll(".phone-cc-option").forEach((opt) => {
        const text = (opt.textContent || "").toLowerCase();
        opt.hidden = Boolean(q) && !text.includes(q);
      });
    });

    national.addEventListener("beforeinput", (e) => {
      if (e.data && /\D/.test(e.data)) e.preventDefault();
    });
    national.addEventListener("keydown", (e) => {
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      if (e.key.length === 1 && /\D/.test(e.key)) e.preventDefault();
    });
    national.addEventListener("paste", (e) => {
      e.preventDefault();
      const pasted = (e.clipboardData || window.clipboardData).getData("text") || "";
      national.value = pasted.replace(/\D+/g, "").slice(0, 15);
    });
    national.addEventListener("input", () => {
      national.value = national.value.replace(/\D+/g, "");
    });

    document.addEventListener("click", (e) => {
      if (menu.hidden) return;
      const t = e.target;
      if (t instanceof Node && (menu.contains(t) || btn.contains(t))) return;
      menu.hidden = true;
      btn.setAttribute("aria-expanded", "false");
    });
  }

  async function api(path, options = {}) {
    const opts = {
      credentials: "include",
      headers: { Accept: "application/json", ...(options.headers || {}) },
      ...options,
    };
    if (opts.body && typeof opts.body === "object" && !(opts.body instanceof FormData)) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(opts.body);
    }
    const res = await fetch(path, opts);
    let data = null;
    try {
      data = await res.json();
    } catch (_) {
      data = null;
    }
    return { res, data };
  }

  async function refreshAccount() {
    showAccountState("account-loading");
    setHint($("#auth-hint"));
    setHint($("#profile-hint"));
    const { res, data } = await api("/api/me");
    if (res.status === 401) {
      profile = null;
      showAccountState("account-guest");
      return;
    }
    if (!res.ok) {
      showAccountState("account-guest");
      setHint($("#auth-hint"), (data && data.detail) || msg("loadAccountFailed", "Non riesco a caricare l’account."), "err");
      return;
    }
    fillProfile(data);
    showAccountState("account-user");
  }

  function bindAuth() {
    $$(".auth-tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        const mode = btn.getAttribute("data-auth");
        $$(".auth-tab").forEach((b) => b.classList.toggle("on", b === btn));
        $("#form-login").hidden = mode !== "login";
        $("#form-register").hidden = mode !== "register";
        setHint($("#auth-hint"));
      });
    });

    $("#form-login")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      setHint($("#auth-hint"), msg("accessInProgress", "Accesso in corso…"));
      const { res, data } = await api("/api/auth/login", {
        method: "POST",
        body: {
          username: String(fd.get("username") || "").trim(),
          password: String(fd.get("password") || ""),
        },
      });
      if (!res.ok) {
        setHint($("#auth-hint"), (data && data.detail) || msg("invalidCredentials", "Credenziali non valide."), "err");
        return;
      }
      fillProfile(data);
      showAccountState("account-user");
    });

    $("#form-register")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      setHint($("#auth-hint"), msg("creatingAccount", "Creazione account…"));
      const { res, data } = await api("/api/auth/register", {
        method: "POST",
        body: {
          username: String(fd.get("username") || "").trim(),
          email: String(fd.get("email") || "").trim(),
          password: String(fd.get("password") || ""),
        },
      });
      if (!res.ok) {
        const detail = data && (data.detail || data.message);
        setHint($("#auth-hint"), typeof detail === "string" ? detail : msg("registerFailed", "Registrazione non riuscita."), "err");
        return;
      }
      fillProfile(data, { mode: "edit" });
      showAccountState("account-user");
      setHint($("#profile-hint"), msg("accountCreated", "Account creato."), "ok");
    });

    $("#form-profile")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const gender = fd.get("gender");
      if (!gender) {
        setHint($("#profile-hint"), msg("chooseGender", "Scegli come ti senti."), "err");
        return;
      }
      const phoneNational = String(fd.get("phone_national") || "").replace(/\D+/g, "").trim();
      const phoneCountry = phoneNational ? String(fd.get("phone_country") || "").trim() : "";
      setHint($("#profile-hint"), msg("saving", "Salvataggio…"));
      const { res, data } = await api("/api/me/anagrafica", {
        method: "PUT",
        body: {
          first_name: String(fd.get("first_name") || "").trim(),
          last_name: String(fd.get("last_name") || "").trim(),
          email: String(fd.get("email") || "").trim(),
          phone_country: phoneCountry,
          phone_national: phoneNational,
          gender: String(gender),
        },
      });
      if (!res.ok) {
        setHint($("#profile-hint"), (data && data.detail) || msg("saveFailed", "Salvataggio non riuscito."), "err");
        return;
      }
      fillProfile(data, { mode: "view", justSaved: true });
      setHint($("#profile-hint"));
      const summary = $("#account-summary");
      if (summary) summary.scrollIntoView({ behavior: "smooth", block: "start" });
    });

    $("#btn-edit-profile")?.addEventListener("click", () => {
      if (profile) fillProfile(profile, { mode: "edit" });
      else setAccountMode("edit");
      setHint($("#profile-hint"));
    });

    $("#btn-cancel-edit")?.addEventListener("click", () => {
      if (profile && (profile.anagrafica_complete || profile.first_name)) {
        fillProfile(profile, { mode: "view" });
      } else {
        setAccountMode("view");
      }
      setHint($("#profile-hint"));
    });

    $("#btn-logout")?.addEventListener("click", async () => {
      await api("/api/auth/logout", { method: "POST" });
      profile = null;
      showAccountState("account-guest");
      setHint($("#auth-hint"), msg("loggedOut", "Sei uscito."), "ok");
    });

    $("#profile-avatar-btn")?.addEventListener("click", () => {
      $("#photo-input")?.click();
    });

    $("#photo-input")?.addEventListener("change", async (e) => {
      const file = e.target.files && e.target.files[0];
      if (!file) return;
      const body = new FormData();
      body.append("photo", file);
      const hintTarget = accountMode === "edit" ? $("#profile-hint") : $("#saved-banner");
      if (accountMode === "edit") setHint($("#profile-hint"), msg("uploadPhoto", "Carico la foto…"));
      const { res, data } = await api("/anagrafica/foto", {
        method: "POST",
        body,
        headers: { Accept: "application/json" },
      });
      e.target.value = "";
      if (!res.ok) {
        if (accountMode === "edit") {
          setHint($("#profile-hint"), (data && data.detail) || msg("photoFailed", "Foto non caricata."), "err");
        }
        return;
      }
      if (data && data.url) {
        setProfilePhoto(data.url);
        if (profile) profile.photo_url = data.url;
      } else {
        const me = await api("/api/me");
        if (me.res.ok) fillProfile(me.data, { mode: accountMode });
      }
      if (accountMode === "edit") {
        setHint($("#profile-hint"), msg("photoUpdated", "Foto aggiornata."), "ok");
      } else if (hintTarget) {
        hintTarget.hidden = false;
        hintTarget.textContent = msg("photoUpdated", "Foto aggiornata.");
      }
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    applyTheme();
    buildDots();
    bindIrisSwipe();
    bindSettings();
    bindWhatsNew();
    bindPhonePicker();
    bindAuth();
    setTimeout(() => show("iris"), 700);

    $$(".shell-tabs [data-go]").forEach((btn) => {
      btn.addEventListener("click", () => show(btn.getAttribute("data-go")));
    });
  });
})();
