(() => {
  const PHOTOS = [
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

  let index = 0;
  let timer = null;
  let carouselOn = false;
  let profile = null;

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
    if (!img || !slide) return;
    if (animate) {
      img.classList.remove("is-swap");
      void img.offsetWidth;
      img.classList.add("is-swap");
    }
    img.src = slide.src;
    img.alt = slide.alt;
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

  function openSettings() {
    const panel = $("#settings-panel");
    const backdrop = $("#settings-backdrop");
    if (!panel) return;
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
  }

  function bindSettings() {
    $("#settings-open")?.addEventListener("click", openSettings);
    $("#settings-close")?.addEventListener("click", closeSettings);
    $("#settings-backdrop")?.addEventListener("click", closeSettings);

    $$(".theme-choice").forEach((btn) => {
      btn.addEventListener("click", () => {
        const choice = btn.getAttribute("data-theme-choice");
        try {
          localStorage.setItem(THEME_KEY, choice);
        } catch (_) {}
        applyTheme(choice);
      });
    });

    // Re-evaluate auto theme every minute (hour boundary).
    setInterval(() => {
      if (getThemeChoice() === "auto") applyTheme("auto");
    }, 60_000);
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

  function fillProfile(data) {
    profile = data;
    const form = $("#form-profile");
    if (!form) return;
    form.first_name.value = data.first_name || "";
    form.last_name.value = data.last_name || "";
    form.email.value = data.email || "";
    form.phone_country.value = data.phone_country || "IT";
    form.phone_national.value = data.phone_national || "";
    const gender = data.gender || "";
    $$('input[name="gender"]', form).forEach((r) => {
      r.checked = r.value === gender;
    });
    const img = $("#profile-photo");
    const fallback = $("#profile-photo-fallback");
    if (data.photo_url) {
      img.src = data.photo_url + (data.photo_url.includes("?") ? "&" : "?") + "t=" + Date.now();
      img.hidden = false;
      if (fallback) fallback.hidden = true;
    } else {
      img.removeAttribute("src");
      img.hidden = true;
      if (fallback) fallback.hidden = false;
    }
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
      setHint($("#auth-hint"), (data && data.detail) || "Non riesco a caricare l’account.", "err");
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
      setHint($("#auth-hint"), "Accesso in corso…");
      const { res, data } = await api("/api/auth/login", {
        method: "POST",
        body: {
          username: String(fd.get("username") || "").trim(),
          password: String(fd.get("password") || ""),
        },
      });
      if (!res.ok) {
        setHint($("#auth-hint"), (data && data.detail) || "Credenziali non valide.", "err");
        return;
      }
      fillProfile(data);
      showAccountState("account-user");
      setHint($("#profile-hint"), "Ok.", "ok");
    });

    $("#form-register")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      setHint($("#auth-hint"), "Creazione account…");
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
        setHint($("#auth-hint"), typeof detail === "string" ? detail : "Registrazione non riuscita.", "err");
        return;
      }
      fillProfile(data);
      showAccountState("account-user");
      setHint($("#profile-hint"), "Account creato.", "ok");
    });

    $("#form-profile")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const gender = fd.get("gender");
      if (!gender) {
        setHint($("#profile-hint"), "Scegli come ti senti.", "err");
        return;
      }
      setHint($("#profile-hint"), "Salvataggio…");
      const { res, data } = await api("/api/me/anagrafica", {
        method: "PUT",
        body: {
          first_name: String(fd.get("first_name") || "").trim(),
          last_name: String(fd.get("last_name") || "").trim(),
          email: String(fd.get("email") || "").trim(),
          phone_country: String(fd.get("phone_country") || "").trim(),
          phone_national: String(fd.get("phone_national") || "").trim(),
          gender: String(gender),
        },
      });
      if (!res.ok) {
        setHint($("#profile-hint"), (data && data.detail) || "Salvataggio non riuscito.", "err");
        return;
      }
      fillProfile(data);
      setHint($("#profile-hint"), "Salvato.", "ok");
    });

    $("#btn-logout")?.addEventListener("click", async () => {
      await api("/api/auth/logout", { method: "POST" });
      profile = null;
      showAccountState("account-guest");
      setHint($("#auth-hint"), "Sei uscito.", "ok");
    });

    $("#photo-input")?.addEventListener("change", async (e) => {
      const file = e.target.files && e.target.files[0];
      if (!file) return;
      const body = new FormData();
      body.append("photo", file);
      setHint($("#profile-hint"), "Carico la foto…");
      const { res, data } = await api("/anagrafica/foto", {
        method: "POST",
        body,
        headers: { Accept: "application/json" },
      });
      e.target.value = "";
      if (!res.ok) {
        setHint($("#profile-hint"), (data && data.detail) || "Foto non caricata.", "err");
        return;
      }
      const me = await api("/api/me");
      if (me.res.ok) fillProfile(me.data);
      setHint($("#profile-hint"), "Foto aggiornata.", "ok");
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    applyTheme();
    buildDots();
    bindSettings();
    bindAuth();
    setTimeout(() => show("iris"), 700);

    $$(".shell-tabs [data-go]").forEach((btn) => {
      btn.addEventListener("click", () => show(btn.getAttribute("data-go")));
    });
  });
})();
