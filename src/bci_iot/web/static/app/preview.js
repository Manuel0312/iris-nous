(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  function show(name) {
    $$(".screen").forEach((el) => el.classList.toggle("on", el.dataset.screen === name));
    $$(".phone-tabs .tab").forEach((el) =>
      el.classList.toggle("on", el.getAttribute("data-go") === name)
    );
  }

  function openInIris(path) {
    const frame = $("#iris-frame");
    if (!frame) return;
    const url = path.startsWith("http") ? path : path;
    frame.src = url;
    show("iris");
  }

  document.addEventListener("DOMContentLoaded", () => {
    setTimeout(() => show("iris"), 900);

    $$(".phone-tabs [data-go]").forEach((btn) => {
      btn.addEventListener("click", () => show(btn.getAttribute("data-go")));
    });

    $$("[data-open-iris]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        openInIris(btn.getAttribute("data-open-iris"));
      });
    });
  });
})();
