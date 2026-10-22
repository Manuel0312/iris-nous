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
  let slideToken = 0;
  let profile = null;
  let accountMode = "view";

  function preloadIrisPhotos() {
    PHOTO_SRC.forEach((p) => {
      const im = new Image();
      im.decoding = "async";
      im.src = p.src;
    });
  }

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

  function needsEmailGate(p) {
    return Boolean(p) && !p.is_admin && p.email_verified === false;
  }

  function maskEmail(email) {
    const s = String(email || "").trim();
    const at = s.indexOf("@");
    if (at < 1) return s;
    const local = s.slice(0, at);
    const domain = s.slice(at);
    if (local.length <= 1) return `${local}***${domain}`;
    return `${local[0]}***${domain}`;
  }

  function showDevOtp(code) {
    const box = $("#confirm-dev-otp");
    if (!box) return;
    const c = String(code || "").trim();
    if (!c) {
      box.hidden = true;
      box.textContent = "";
      return;
    }
    box.hidden = false;
    box.textContent =
      msg("devOtpLocal", "Anteprima locale: la mail non parte da questo computer. Usa questo codice:") +
      " " +
      c;
    const input = $("#shell-confirm-code");
    if (input && !input.value) input.value = c;
  }

  function showEmailGate(p) {
    profile = p || profile;
    document.body.classList.add("email-gate");
    const overlay = $("#setup-overlay");
    const frame = $("#setup-frame");
    if (overlay) {
      overlay.hidden = true;
      overlay.setAttribute("aria-hidden", "true");
    }
    if (frame) frame.src = "about:blank";
    const masked = $("#confirm-email-masked");
    if (masked) masked.textContent = maskEmail(profile && profile.email);
    const lede = $("#confirm-email-lede");
    if (lede) {
      lede.textContent =
        msg("confirmEmailSent", "Ti abbiamo mandato una email da Iris Nous a") +
        " " +
        maskEmail(profile && profile.email) +
        ". " +
        msg("confirmEmailSpam", "Apri la posta (anche Spam), copia il codice di 6 caratteri e inseriscilo qui.");
    }
    showDevOtp(profile && profile.dev_otp_code);
    showAccountState("account-confirm");
    $$(".screen").forEach((el) => el.classList.toggle("on", el.dataset.screen === "account"));
    $$(".shell-tabs .tab").forEach((el) =>
      el.classList.toggle("on", el.getAttribute("data-go") === "account")
    );
    stopCarousel();
  }

  function clearEmailGate() {
    document.body.classList.remove("email-gate");
  }

  function show(name) {
    if (needsEmailGate(profile) && name !== "account") {
      showEmailGate(profile);
      return;
    }
    $$(".screen").forEach((el) => el.classList.toggle("on", el.dataset.screen === name));
    $$(".shell-tabs .tab").forEach((el) =>
      el.classList.toggle("on", el.getAttribute("data-go") === name)
    );
    if (name === "iris") startCarousel();
    else stopCarousel();
    if (name === "account") refreshAccount();
    if (name === "links") refreshConnections();
  }

  function nativeBridge(action, payload) {
    try {
      if (window.IrisNative && typeof window.IrisNative.postMessage === "function") {
        window.IrisNative.postMessage(JSON.stringify({ action, ...(payload || {}) }));
        return true;
      }
    } catch (_) {}
    return false;
  }

  function setupUrl(path) {
    const u = new URL(path, window.location.origin);
    u.searchParams.set("from", "native_app");
    u.searchParams.set("embed", "1");
    return u.pathname + u.search + (u.hash || "");
  }

  function openSetup(path, title) {
    const overlay = $("#setup-overlay");
    const frame = $("#setup-frame");
    const titleEl = $("#setup-overlay-title");
    if (!overlay || !frame) {
      window.location.href = setupUrl(path);
      return;
    }
    if (titleEl) titleEl.textContent = title || msg("setupTitle", "Configurazione");
    frame.src = setupUrl(path);
    overlay.hidden = false;
    overlay.setAttribute("aria-hidden", "false");
  }

  function closeSetup() {
    const overlay = $("#setup-overlay");
    const frame = $("#setup-frame");
    if (overlay) {
      overlay.hidden = true;
      overlay.setAttribute("aria-hidden", "true");
    }
    if (frame) frame.src = "about:blank";
    refreshConnections();
    if (typeof refreshAccount === "function") refreshAccount();
  }

  function setChip(el, label, path, soft) {
    if (!el) return;
    el.textContent = label;
    el.classList.toggle("soft", Boolean(soft));
    if (path && el.tagName === "A") {
      el.setAttribute("href", setupUrl(path));
      el.setAttribute("data-setup", path);
    }
  }

  async function refreshConnections() {
    const guestHint = $("#conn-guest-hint");
    const cuffia = $("#conn-cuffia-chip");
    const contesto = $("#conn-contesto-chip");
    const phone = $("#conn-phone-chip");
    const { res, data } = await api("/api/me");
    const logged = res.ok && data;
    if (guestHint) guestHint.hidden = Boolean(logged);
    if (!logged) {
      setChip(cuffia, msg("connSetup", "Da configurare"), "/cuffia", false);
      setChip(contesto, msg("connOpen", "Apri"), "/contesto", false);
      setChip(phone, msg("connConnect", "Collega"), "/telefono-setup", false);
      return;
    }
    const calib = Boolean(data.calibration_complete);
    const linked = Boolean(data.headset_id);
    const paired = Boolean(data.phone_paired);
    if (calib) setChip(cuffia, msg("connReady", "Pronta"), "/cuffia", true);
    else if (linked) setChip(cuffia, msg("connCalibrate", "Da calibrare"), "/cuffia", false);
    else setChip(cuffia, msg("connSetup", "Da configurare"), "/cuffia", false);
    setChip(contesto, msg("connOpen", "Apri"), "/contesto", calib);
    setChip(
      phone,
      paired ? msg("connLinked", "Collegato") : msg("connConnect", "Collega"),
      "/telefono-setup",
      paired
    );
    nativeBridge("ensureCallBridge", { username: data.username || "" });
  }

  function bindSetupOverlay() {
    $("#setup-overlay-close")?.addEventListener("click", () => closeSetup());
    window.addEventListener("message", (ev) => {
      const data = ev && ev.data;
      if (!data || typeof data !== "object") return;
      if (data.type === "iris-shell-close") closeSetup();
    });

    const titles = {
      "/cuffia": () => msg("setupCuffia", "Cuffia"),
      "/contesto": () => msg("setupContesto", "In ascolto"),
      "/telefono-setup": () => msg("setupPhone", "Telefono"),
    };

    function onSetupChip(e) {
      const a = e.target.closest("a[data-setup]");
      if (!a || !a.closest("#screen-links")) return;
      e.preventDefault();
      if (!profile) {
        show("account");
        setHint($("#auth-hint"), msg("loginForSetup", "Accedi o crea l’account per configurare la cuffia."), "ok");
        return;
      }
      if (needsEmailGate(profile)) {
        showEmailGate(profile);
        return;
      }
      const path = a.getAttribute("data-setup") || "/cuffia";
      const titleFn = titles[path.split("?")[0]] || (() => msg("setupTitle", "Configurazione"));
      openSetup(path, titleFn());
    }

    $("#conn-cuffia-chip")?.addEventListener("click", onSetupChip);
    $("#conn-contesto-chip")?.addEventListener("click", onSetupChip);
    $("#conn-phone-chip")?.addEventListener("click", onSetupChip);
  }

  function renderSlide(i, animate) {
    const slide = PHOTOS[i];
    const img = $("#iris-photo-img");
    const titleEl = $("#explain-title");
    const bodyEl = $("#explain-body");
    const card = $("#explain-card");
    const photo = $("#iris-photo");
    if (!img || !slide) return;
    const token = ++slideToken;

    if (titleEl && slide.title) titleEl.textContent = slide.title;
    if (bodyEl && slide.body) bodyEl.textContent = slide.body;
    $$("#popup-dots button").forEach((btn, n) => {
      btn.classList.toggle("on", n === i);
      btn.setAttribute("aria-current", n === i ? "true" : "false");
    });
    if (photo) photo.style.transform = "";

    const kickAnim = () => {
      if (token !== slideToken || !animate) return;
      img.classList.remove("is-swap");
      if (card) card.classList.remove("is-swap");
      void img.offsetWidth;
      img.classList.add("is-swap");
      if (card) card.classList.add("is-swap");
    };

    const same = img.getAttribute("src") === slide.src;
    img.alt = slide.alt || "";
    if (same) {
      kickAnim();
      return;
    }
    img.src = slide.src;
    const finish = () => {
      if (token !== slideToken) return;
      kickAnim();
    };
    if (typeof img.decode === "function") {
      img.decode().then(finish).catch(finish);
    } else if (!img.complete) {
      img.addEventListener("load", finish, { once: true });
      img.addEventListener("error", finish, { once: true });
    } else {
      finish();
    }
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

  function resetCarouselTimer() {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
    if (!carouselOn) return;
    timer = setInterval(() => {
      if (carouselOn) next();
    }, INTERVAL_MS);
  }

  function startCarousel() {
    stopCarousel();
    carouselOn = true;
    go(index, false);
    resetCarouselTimer();
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
        resetCarouselTimer();
      });
      host.appendChild(btn);
    });
  }

  function bindIrisSwipe() {
    const stage = $(".iris-stage");
    const photo = $("#iris-photo");
    if (!stage) return;
    let startX = 0;
    let startY = 0;
    let tracking = false;

    const clearDrag = () => {
      if (photo) photo.style.transform = "";
    };

    const onStart = (x, y) => {
      startX = x;
      startY = y;
      tracking = true;
    };
    const onMove = (x, y) => {
      if (!tracking || !photo) return;
      const dx = x - startX;
      const dy = y - startY;
      if (Math.abs(dx) < 8 || Math.abs(dx) < Math.abs(dy)) return;
      photo.style.transform = `translate3d(${Math.round(dx * 0.28)}px,0,0)`;
    };
    const onEnd = (x, y) => {
      if (!tracking) return;
      tracking = false;
      clearDrag();
      const dx = x - startX;
      const dy = y - startY;
      if (Math.abs(dx) < 40 || Math.abs(dx) < Math.abs(dy)) return;
      if (dx < 0) next();
      else prev();
      resetCarouselTimer();
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
      "touchmove",
      (e) => {
        const t = e.touches[0];
        if (t) onMove(t.clientX, t.clientY);
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
    stage.addEventListener(
      "touchcancel",
      () => {
        tracking = false;
        clearDrag();
      },
      { passive: true }
    );

    let mouseDown = false;
    stage.addEventListener("mousedown", (e) => {
      mouseDown = true;
      onStart(e.clientX, e.clientY);
    });
    stage.addEventListener("mousemove", (e) => {
      if (!mouseDown) return;
      onMove(e.clientX, e.clientY);
    });
    stage.addEventListener("mouseup", (e) => {
      if (!mouseDown) return;
      mouseDown = false;
      onEnd(e.clientX, e.clientY);
    });
    stage.addEventListener("mouseleave", () => {
      mouseDown = false;
      tracking = false;
      clearDrag();
    });
  }

  const MOTION_MS = 280;

  function afterPaint(fn) {
    requestAnimationFrame(() => requestAnimationFrame(fn));
  }

  function ensureLangFlags() {
    $$("#settings-langs .lang-flag-img, #settings-lang-current .lang-flag-img").forEach((img) => {
      if (!(img instanceof HTMLImageElement)) return;
      img.loading = "eager";
      const src = img.getAttribute("src");
      if (!src) return;
      if (!img.complete || img.naturalWidth === 0) {
        img.src = src;
      }
    });
  }

  function setDropdownOpen(kind, open) {
    const block = kind === "theme" ? $(".settings-theme-block") : $(".settings-lang-block");
    const list = kind === "theme" ? $("#settings-themes") : $("#settings-langs");
    const toggle = kind === "theme" ? $("#settings-theme-toggle") : $("#settings-lang-toggle");
    if (block) block.dataset.open = open ? "1" : "0";
    if (list) {
      // Resta in flusso: l’apertura è animata via CSS (data-open), non con display:none
      list.hidden = false;
      list.removeAttribute("hidden");
      list.setAttribute("aria-hidden", open ? "false" : "true");
    }
    if (toggle) toggle.setAttribute("aria-expanded", open ? "true" : "false");
    if (kind === "lang" && open) ensureLangFlags();
  }

  function closeAllDropdowns() {
    setDropdownOpen("theme", false);
    setDropdownOpen("lang", false);
  }

  function unlockOverlay(el) {
    if (!el) return;
    el.hidden = false;
    el.removeAttribute("hidden");
  }

  function lockOverlay(el) {
    if (!el) return;
    el.hidden = true;
    el.setAttribute("hidden", "");
    el.classList.remove("is-open");
  }

  function openSettings() {
    const panel = $("#settings-panel");
    const backdrop = $("#settings-backdrop");
    if (!panel) return;
    closeAllDropdowns();
    unlockOverlay(panel);
    unlockOverlay(backdrop);
    document.body.classList.add("settings-open");
    afterPaint(() => {
      panel.classList.add("is-open");
      if (backdrop) backdrop.classList.add("is-open");
    });
  }

  function closeSettings() {
    const panel = $("#settings-panel");
    const backdrop = $("#settings-backdrop");
    closeAllDropdowns();
    document.body.classList.remove("settings-open");
    if (panel) panel.classList.remove("is-open");
    if (backdrop) backdrop.classList.remove("is-open");
    window.setTimeout(() => {
      if (panel && !panel.classList.contains("is-open")) lockOverlay(panel);
      if (backdrop && !backdrop.classList.contains("is-open")) lockOverlay(backdrop);
    }, MOTION_MS);
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
      // Tema e Lingua possono restare aperte insieme
      setDropdownOpen("theme", open);
    });

    $("#settings-lang-toggle")?.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      const block = $(".settings-lang-block");
      const open = !(block && block.dataset.open === "1");
      setDropdownOpen("lang", open);
    });

    document.addEventListener("click", (e) => {
      const t = e.target;
      const themeBlock = $(".settings-theme-block");
      const langBlock = $(".settings-lang-block");
      const inTheme = t instanceof Node && themeBlock && themeBlock.contains(t);
      const inLang = t instanceof Node && langBlock && langBlock.contains(t);
      // Chiudi solo se il tap è fuori da entrambe (non chiudere l’altra tendina)
      if (!inTheme && !inLang) closeAllDropdowns();
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
      unlockOverlay(newsOverlay);
      document.body.classList.add("whats-new-open");
      afterPaint(() => newsOverlay.classList.add("is-open"));
      if (newsDialog) newsDialog.focus();
      markNewsSeen();
    }
    function closeNews() {
      if (!newsOverlay) return;
      newsOverlay.classList.remove("is-open");
      document.body.classList.remove("whats-new-open");
      window.setTimeout(() => {
        if (!newsOverlay.classList.contains("is-open")) lockOverlay(newsOverlay);
      }, MOTION_MS);
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
    ["account-loading", "account-guest", "account-confirm", "account-user"].forEach((id) => {
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
    setHint($("#confirm-hint"));
    const { res, data } = await api("/api/me");
    if (res.status === 401) {
      profile = null;
      clearEmailGate();
      showAccountState("account-guest");
      return;
    }
    if (!res.ok) {
      clearEmailGate();
      showAccountState("account-guest");
      setHint($("#auth-hint"), (data && data.detail) || msg("loadAccountFailed", "Non riesco a caricare l’account."), "err");
      return;
    }
    fillProfile(data);
    if (needsEmailGate(data)) {
      showEmailGate(data);
      return;
    }
    clearEmailGate();
    showAccountState("account-user");
  }

  function bindPasswordToggles() {
    const showLabel = msg("showPassword", "Mostra password");
    const hideLabel = msg("hidePassword", "Nascondi password");
    const isTouchUi = window.matchMedia("(hover: none), (pointer: coarse)").matches;
    $$("[data-toggle-password]").forEach((btn) => {
      const input = document.getElementById(btn.getAttribute("data-toggle-password"));
      if (!input) return;
      const eyeShow = btn.querySelector(".eye-show");
      const eyeHide = btn.querySelector(".eye-hide");
      const setVisible = (show) => {
        input.type = show ? "text" : "password";
        btn.setAttribute("aria-pressed", show ? "true" : "false");
        btn.setAttribute("aria-label", show ? hideLabel : showLabel);
        if (eyeShow && eyeHide) {
          eyeShow.hidden = show;
          eyeHide.hidden = !show;
        }
      };
      if (isTouchUi) {
        btn.addEventListener("click", () => setVisible(input.type === "password"));
      } else {
        btn.addEventListener("mouseenter", () => setVisible(true));
        btn.addEventListener("mouseleave", () => setVisible(false));
        btn.addEventListener("click", (e) => e.preventDefault());
      }
    });
  }

  function initPasswordStrength() {
    const input = $("#shell-register-password");
    const meter = $("#shell-reg-strength");
    const list = $("#shell-reg-reqs");
    const submit = $("#shell-reg-submit");
    if (!input || !meter || !list) return null;
    async function check() {
      try {
        const res = await fetch("/api/password-strength?password=" + encodeURIComponent(input.value));
        const data = await res.json();
        meter.dataset.level = data.level || "weak";
        meter.textContent =
          data.message || msg("pwdNeedMedium", "Serve almeno: 8 caratteri, una maiuscola, un numero.");
        list.innerHTML = "";
        (data.requirements || []).forEach((r) => {
          const li = document.createElement("li");
          li.textContent = r.label;
          if (r.optional) li.classList.add("is-optional");
          if (r.ok) li.classList.add("is-ok");
          list.appendChild(li);
        });
        const ok = (data.requirements || []).filter((r) => !r.optional).every((r) => r.ok);
        if (submit) submit.disabled = !ok;
      } catch (_) {
        if (submit) submit.disabled = true;
      }
    }
    input.addEventListener("input", check);
    check();
    return check;
  }

  function bindAuth() {
    const recheckPwd = initPasswordStrength();
    $$(".auth-tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        const mode = btn.getAttribute("data-auth");
        $$(".auth-tab").forEach((b) => b.classList.toggle("on", b === btn));
        $("#form-login").hidden = mode !== "login";
        $("#form-register").hidden = mode !== "register";
        setHint($("#auth-hint"));
        if (mode === "register" && typeof recheckPwd === "function") recheckPwd();
      });
    });

    $("#conn-perms-btn")?.addEventListener("click", () => {
      if (!nativeBridge("openPermissions")) {
        if (!profile) {
          show("account");
          return;
        }
        openSetup("/telefono-setup", msg("setupPhone", "Telefono"));
      }
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
      // Account già verificato → profilo; altrimenti (raro) blocco codice in-app
      if (needsEmailGate(data)) showEmailGate(data);
      else {
        clearEmailGate();
        showAccountState("account-user");
      }
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
      // Codice PRIMA del profilo / cuffia — stessa UI app, zero redirect sito
      fillProfile(data);
      showEmailGate(data);
      showDevOtp(data && data.dev_otp_code);
      setHint($("#confirm-hint"), msg("accountCreated", "Account creato."), "ok");
    });

    const confirmCode = $("#shell-confirm-code");
    confirmCode?.addEventListener("input", function () {
      this.value = this.value.replace(/[^A-Za-z0-9]/g, "").toUpperCase().slice(0, 6);
    });

    $("#form-confirm-email")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const code = String(fd.get("code") || "").trim().toUpperCase();
      setHint($("#confirm-hint"), msg("confirmingEmail", "Conferma in corso…"));
      const { res, data } = await api("/api/auth/confirm-email", {
        method: "POST",
        body: { code },
      });
      if (!res.ok) {
        setHint(
          $("#confirm-hint"),
          (data && data.detail) || msg("confirmEmailFail", "Codice non valido. Riprova."),
          "err"
        );
        return;
      }
      fillProfile(data, { mode: "edit" });
      clearEmailGate();
      showAccountState("account-user");
      setHint($("#profile-hint"), msg("confirmEmailOk", "Email confermata. Ora puoi configurare la cuffia."), "ok");
    });

    $("#btn-resend-confirm")?.addEventListener("click", async () => {
      setHint($("#confirm-hint"), msg("resendingEmail", "Invio in corso…"));
      const { res, data } = await api("/api/auth/resend-confirm-email", { method: "POST" });
      if (!res.ok) {
        setHint(
          $("#confirm-hint"),
          (data && data.detail) || msg("resendEmailFail", "Invio non riuscito. Riprova tra un minuto."),
          "err"
        );
        return;
      }
      if (data && data.dev_otp_code) {
        if (profile) profile.dev_otp_code = data.dev_otp_code;
        showDevOtp(data.dev_otp_code);
      }
      setHint(
        $("#confirm-hint"),
        data && data.dev_otp_code
          ? msg("devOtpLocal", "Anteprima locale: la mail non parte da questo computer. Usa questo codice:")
          : msg("resendEmailOk", "Email reinviata. Controlla anche Spam."),
        "ok"
      );
    });

    $("#btn-confirm-logout")?.addEventListener("click", async () => {
      await api("/api/auth/logout", { method: "POST" });
      profile = null;
      clearEmailGate();
      showAccountState("account-guest");
      setHint($("#auth-hint"), msg("loggedOut", "Sei uscito."), "ok");
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
    preloadIrisPhotos();
    buildDots();
    bindIrisSwipe();
    bindSettings();
    bindWhatsNew();
    bindPhonePicker();
    bindPasswordToggles();
    bindAuth();
    bindSetupOverlay();
    nativeBridge("ensureCallBridge", {});
    setTimeout(async () => {
      const { res, data } = await api("/api/me");
      if (res.ok && needsEmailGate(data)) {
        fillProfile(data);
        showEmailGate(data);
        return;
      }
      if (res.ok) fillProfile(data);
      show("iris");
    }, 400);

    $$(".shell-tabs [data-go]").forEach((btn) => {
      btn.addEventListener("click", () => show(btn.getAttribute("data-go")));
    });
  });
})();
