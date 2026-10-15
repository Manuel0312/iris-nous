(() => {
  const SLIDES = [
    {
      kicker: "Benvenuto",
      title: "Iris ti ascolta",
      body: "Pensi sì o no. Casa, musica e telefono rispondono a te — senza tastiera.",
    },
    {
      kicker: "Cuffia",
      title: "Indossa e basta",
      body: "Metti la cuffia. Quando pensi sì o no, Iris lo sente e agisce.",
    },
    {
      kicker: "Telefono",
      title: "Chiamate e messaggi",
      body: "Arriva una chiamata o un messaggio: rispondi pensando sì o no.",
    },
    {
      kicker: "Musica",
      title: "Cambia brano col pensiero",
      body: "Vuoi la traccia dopo? Un sì basta. Niente di complicato.",
    },
    {
      kicker: "Casa",
      title: "La casa ti segue",
      body: "Luci e dispositivi possono seguire i tuoi sì e no, quando li colleghi.",
    },
    {
      kicker: "Privacy",
      title: "Non legge i messaggi",
      body: "Iris non apre le chat. Se dici sì a un messaggio, può solo aprire WhatsApp.",
    },
  ];

  const INTERVAL_MS = 7000;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  let index = 0;
  let timer = null;
  let carouselOn = false;

  function show(name) {
    $$(".screen").forEach((el) => el.classList.toggle("on", el.dataset.screen === name));
    $$(".shell-tabs .tab").forEach((el) =>
      el.classList.toggle("on", el.getAttribute("data-go") === name)
    );
    if (name === "iris") startCarousel();
    else stopCarousel();
  }

  function renderSlide(i, animate) {
    const slide = SLIDES[i];
    const popup = $("#iris-popup");
    const kicker = $("#popup-kicker");
    const title = $("#popup-title");
    const body = $("#popup-body");
    if (!popup || !slide) return;
    if (animate) {
      popup.classList.remove("is-swap");
      void popup.offsetWidth;
      popup.classList.add("is-swap");
    }
    kicker.textContent = slide.kicker;
    title.textContent = slide.title;
    body.textContent = slide.body;
    $$("#popup-dots button").forEach((btn, n) => {
      btn.classList.toggle("on", n === i);
      btn.setAttribute("aria-current", n === i ? "true" : "false");
    });
  }

  function go(i, animate = true) {
    index = (i + SLIDES.length) % SLIDES.length;
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
    SLIDES.forEach((_, n) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.setAttribute("aria-label", `Passo ${n + 1}`);
      btn.addEventListener("click", () => {
        go(n, true);
        if (carouselOn) startCarousel();
      });
      host.appendChild(btn);
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    buildDots();
    setTimeout(() => show("iris"), 900);

    $$(".shell-tabs [data-go]").forEach((btn) => {
      btn.addEventListener("click", () => show(btn.getAttribute("data-go")));
    });
  });
})();
