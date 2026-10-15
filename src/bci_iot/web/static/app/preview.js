(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  let focus = "idle"; // idle | call | message

  function show(name) {
    $$(".screen").forEach((el) => el.classList.toggle("on", el.dataset.screen === name));
    $$(".phone-tabs .tab").forEach((el) =>
      el.classList.toggle("on", el.getAttribute("data-go") === name)
    );
  }

  function setFocus(kind, title) {
    focus = kind;
    const el = $("#pv-focus");
    if (el) el.textContent = title;
    const msg = $("#pv-live-msg");
    if (msg) {
      msg.hidden = false;
      msg.className = "hint";
      msg.textContent =
        kind === "idle"
          ? "Tocca una prova, poi SÌ o NO."
          : "Ora tocca SÌ o NO.";
    }
  }

  function decide(answer) {
    const msg = $("#pv-live-msg");
    if (!msg) return;
    msg.hidden = false;
    if (focus === "idle") {
      msg.className = "hint";
      msg.textContent = "Prima prova una chiamata o un messaggio.";
      return;
    }
    if (answer === "SI" && focus === "message") {
      msg.className = "hint ok";
      msg.textContent = "Apro WhatsApp…";
      try {
        window.open("https://wa.me/", "_blank", "noopener");
      } catch (_) {
        /* ignore */
      }
      setFocus("idle", "Niente in corso");
      return;
    }
    if (answer === "SI" && focus === "call") {
      msg.className = "hint ok";
      msg.textContent = "Chiamata accettata.";
      setFocus("idle", "Niente in corso");
      return;
    }
    if (answer === "NO") {
      msg.className = "hint ok";
      msg.textContent =
        focus === "call" ? "Chiamata rifiutata." : "Messaggio lasciato stare.";
      setFocus("idle", "Niente in corso");
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    // Splash → Iris
    setTimeout(() => show("iris"), 900);

    $$("[data-go]").forEach((btn) => {
      btn.addEventListener("click", () => show(btn.getAttribute("data-go")));
    });

    $$("[data-perm]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const on = btn.classList.toggle("on");
        btn.textContent = on ? "Attivo" : "Attiva";
      });
    });

    $("#pv-pair")?.addEventListener("click", () => {
      const user = ($("#pv-user")?.value || "").trim();
      const pass = $("#pv-pass")?.value || "";
      const code = ($("#pv-code")?.value || "").trim();
      const msg = $("#pv-pair-msg");
      if (!msg) return;
      msg.hidden = false;
      if (!user || !pass || code.length < 4) {
        msg.className = "hint err";
        msg.textContent = "Compila i campi per continuare.";
        return;
      }
      msg.className = "hint ok";
      msg.textContent = "Anteprima: collegamento simulato. Continua dai tab.";
      setTimeout(() => show("perm"), 700);
    });

    $("#pv-try-call")?.addEventListener("click", () =>
      setFocus("call", "Chiamata in arrivo")
    );
    $("#pv-try-msg")?.addEventListener("click", () =>
      setFocus("message", "Messaggio da Marco")
    );
    $("#pv-yes")?.addEventListener("click", () => decide("SI"));
    $("#pv-no")?.addEventListener("click", () => decide("NO"));
  });
})();
