(() => {
  const TOKEN_KEY = "iris_companion_token";
  const USER_KEY = "iris_companion_user";

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));

  const msgEl = () => $("#app-msg");
  const livePill = () => $("#live-pill");

  function token() {
    return localStorage.getItem(TOKEN_KEY) || "";
  }

  function setToken(t, user) {
    if (t) localStorage.setItem(TOKEN_KEY, t);
    else localStorage.removeItem(TOKEN_KEY);
    if (user) localStorage.setItem(USER_KEY, user);
  }

  function showMsg(text, kind) {
    const el = msgEl();
    if (!el) return;
    el.textContent = text || "";
    el.className = "msg" + (kind ? " " + kind : "");
  }

  async function api(path, { method = "GET", body, auth = true } = {}) {
    const headers = {
      Accept: "application/json",
      "Content-Type": "application/json",
    };
    const t = token();
    if (auth && t) {
      headers.Authorization = "Bearer " + t;
      headers["X-Iris-Device-Token"] = t;
    }
    const res = await fetch(path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      credentials: "same-origin",
    });
    let data = {};
    try {
      data = await res.json();
    } catch (_) {
      /* empty */
    }
    if (!res.ok) {
      const detail = data.detail;
      const err = new Error(
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail.map((d) => d.msg || d).join(" ")
            : "Errore Iris (" + res.status + ")"
      );
      err.status = res.status;
      throw err;
    }
    return data;
  }

  function setLive(on) {
    const el = livePill();
    if (!el) return;
    el.classList.toggle("on", !!on);
    el.textContent = on ? "con te" : "in attesa";
  }

  function setText(sel, text, className) {
    const el = $(sel);
    if (!el) return;
    el.textContent = text;
    if (className !== undefined) el.className = className;
  }

  function renderStatus(data) {
    const ctx = data.context || {};
    const focus = (ctx.focus && (ctx.focus.label || ctx.focus.kind)) || "—";
    setText("#st-user", data.username || localStorage.getItem(USER_KEY) || "—");
    setText("#st-paired", data.phone_paired ? "sì" : "no", data.phone_paired ? "ok" : "warn");
    setText("#st-spotify", data.spotify_linked ? "collegato" : "da collegare");
    const call = ctx.incoming_call
      ? "in arrivo" + (ctx.caller_name ? " · " + ctx.caller_name : "")
      : "nessuna";
    setText("#st-call", call, ctx.incoming_call ? "warn" : "");
    setText(
      "#st-msg",
      ctx.unread_message
        ? "in arrivo" +
          (ctx.message_from ? " · " + ctx.message_from : "") +
          (ctx.message_app ? " (" + ctx.message_app + ")" : "")
        : "nessuno",
      ctx.unread_message ? "warn" : ""
    );
    setText(
      "#st-music",
      ctx.music_playing ? ctx.track_hint || "in riproduzione" : "ferma"
    );
    setText("#st-focus", typeof focus === "string" ? focus : JSON.stringify(focus));
    setLive(!!data.phone_paired);
    drainCommands(data.pending_commands || []);
  }

  async function openWhatsApp(url) {
    const candidates = [url || "whatsapp://", "whatsapp://", "https://wa.me/"];
    for (const u of candidates) {
      try {
        window.location.href = u;
        return true;
      } catch (_) {
        /* next */
      }
    }
    return false;
  }

  async function drainCommands(list) {
    if (!Array.isArray(list) || !list.length) return;
    const ids = [];
    for (const item of list) {
      if (!item || !item.id || !item.action) continue;
      if (item.action === "open_whatsapp" || item.action === "open_url") {
        await openWhatsApp(item.url || "whatsapp://");
        ids.push(item.id);
        showMsg("Apro WhatsApp.", "ok");
      }
    }
    if (ids.length) {
      try {
        await api("/api/companion/commands/ack", {
          method: "POST",
          body: { ids },
        });
      } catch (_) {
        /* ignore */
      }
    }
  }

  async function decide(answer) {
    showMsg("", "");
    try {
      const data = await api("/api/companion/decide", {
        method: "POST",
        body: { answer },
      });
      const exec = data.execution || {};
      const cmd = exec.os_command || {};
      if (cmd.action === "open_whatsapp" || cmd.action === "open_url" || exec.open_url) {
        await openWhatsApp(cmd.url || exec.open_url || "whatsapp://");
        if (cmd.id) {
          try {
            await api("/api/companion/commands/ack", {
              method: "POST",
              body: { ids: [cmd.id] },
            });
          } catch (_) {
            /* ignore */
          }
        }
      }
      if (data.companion) renderStatus(data.companion);
      else await refresh();
      showMsg(data.feedback || data.message || "Fatto.", "ok");
    } catch (e) {
      showMsg(e.message || "Riprova tra un attimo.", "err");
    }
  }

  async function refresh() {
    if (!token()) {
      setLive(false);
      return;
    }
    try {
      const data = await api("/api/companion/heartbeat", { method: "POST" });
      renderStatus(data);
      showMsg("", "");
    } catch (e) {
      setLive(false);
      if (e.status === 401 || e.status === 403) {
        setToken("", null);
        showMsg(
          e.message ||
            (e.status === 403
              ? "Questo account non è disponibile."
              : "Ricollegati per continuare."),
          "err"
        );
        showTab("login");
      }
    }
  }

  async function pair() {
    const username = ($("#f-user").value || "").trim();
    const password = $("#f-pass").value || "";
    const code = ($("#f-code").value || "").trim();
    const device_name = ($("#f-device")?.value || "").trim();
    const btn = $("#btn-pair");
    btn.disabled = true;
    showMsg("Un momento…", "");
    try {
      const data = await api("/api/companion/pair", {
        method: "POST",
        auth: false,
        body: { username, password, code, device_name },
      });
      setToken(data.device_token, data.username);
      renderStatus(data);
      showMsg("Sei collegato. Iris è con te.", "ok");
      showTab("home");
    } catch (e) {
      showMsg(e.message || "Non riuscito. Controlla i dati e riprova.", "err");
    } finally {
      btn.disabled = false;
    }
  }

  async function sendEvent(event, extra) {
    showMsg("", "");
    try {
      const data = await api("/api/companion/event", {
        method: "POST",
        body: Object.assign({ event }, extra || {}),
      });
      if (data.companion) renderStatus(data.companion);
      else await refresh();
      showMsg("Iris ha ricevuto il segnale.", "ok");
    } catch (e) {
      showMsg(e.message || "Non riuscito. Riprova.", "err");
    }
  }

  async function musicNext() {
    showMsg("", "");
    try {
      const data = await api("/api/companion/music/next", { method: "POST" });
      showMsg(
        data.status === "ok" ? "Prossima canzone inviata a Spotify." : data.detail || data.message || "Spotify",
        data.status === "ok" ? "ok" : "err"
      );
      await refresh();
    } catch (e) {
      showMsg(e.message || "Spotify non disponibile", "err");
    }
  }

  function unpair() {
    setToken("", null);
    setLive(false);
    showMsg("Telefono scollegato. Torna quando vuoi.", "ok");
    showTab("gate");
  }

  function wrapWords(el, className) {
    if (!el || el.dataset.liquidDone === "1") return;
    const text = (el.textContent || "").trim();
    if (!text) return;
    el.dataset.liquidDone = "1";
    el.innerHTML = text
      .split(/(\s+)/)
      .map((part) => {
        if (/^\s+$/.test(part)) return part;
        return `<span class="${className}">${part}</span>`;
      })
      .join("");
  }

  function animateLiquidCopy(root) {
    const scope = root || document;
    scope.querySelectorAll("[data-liquid-title]").forEach((el) => {
      el.dataset.liquidDone = "";
      wrapWords(el, "word");
    });
    scope.querySelectorAll("[data-liquid-lede]").forEach((el) => {
      el.dataset.liquidDone = "";
      wrapWords(el, "word");
    });
  }

  function showTab(id) {
    $$("nav.tabs button").forEach((b) => b.classList.toggle("on", b.dataset.tab === id));
    $$(".screen").forEach((s) => s.classList.toggle("on", s.id === "screen-" + id));
    const active = document.getElementById("screen-" + id);
    if (active) {
      // re-trigger word motion each visit
      active.querySelectorAll("[data-liquid-title], [data-liquid-lede]").forEach((el) => {
        el.dataset.liquidDone = "";
      });
      animateLiquidCopy(active);
    }
  }

  function isStandalone() {
    return (
      window.matchMedia("(display-mode: standalone)").matches ||
      window.navigator.standalone === true
    );
  }

  function setupInstallBanner() {
    const banner = $("#install-banner");
    if (!banner) return;
    if (isStandalone()) {
      banner.hidden = true;
      return;
    }
    banner.hidden = false;
  }

  function registerSw() {
    if (!("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/app/sw.js", { scope: "/app" }).catch(() => {});
  }

  document.addEventListener("DOMContentLoaded", () => {
    $$("nav.tabs button").forEach((btn) => {
      btn.addEventListener("click", () => showTab(btn.dataset.tab));
    });
    $$("[data-goto]").forEach((btn) => {
      btn.addEventListener("click", () => showTab(btn.getAttribute("data-goto")));
    });
    $("#pair-form")?.addEventListener("submit", (e) => {
      e.preventDefault();
      pair();
    });
    $("#btn-call")?.addEventListener("click", () =>
      sendEvent("call_incoming", { caller: "demo" })
    );
    $("#btn-wa")?.addEventListener("click", () =>
      sendEvent("message_incoming", { caller: "Marco" })
    );
    $("#btn-yes")?.addEventListener("click", () => decide("SI"));
    $("#btn-no")?.addEventListener("click", () => decide("NO"));
    $("#btn-end")?.addEventListener("click", () => sendEvent("call_ended"));
    $("#btn-next")?.addEventListener("click", () => musicNext());
    $("#btn-refresh")?.addEventListener("click", () => refresh());
    $("#btn-unpair")?.addEventListener("click", () => unpair());

    setupInstallBanner();
    registerSw();
    animateLiquidCopy(document);

    // /app/device has no tabs — wire buttons if present; /app is the full site iframe.
    if ($("#pair-form") || $("#btn-yes") || $("#btn-wa")) {
      if (token()) {
        if (typeof showTab === "function" && $("#screen-home")) showTab("home");
        refresh();
        setInterval(refresh, 12000);
      } else if (typeof showTab === "function" && $("#screen-gate")) {
        showTab("gate");
      } else if (typeof showTab === "function" && $("#screen-login")) {
        showTab("login");
      }
    }
  });
})();
