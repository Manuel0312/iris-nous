/**
 * Profile photo picker: face-aware framing + zoom/pan crop.
 * Exports a square JPEG of the circular avatar area.
 * Shows a modal when no face is found (security).
 */
(function () {
  const STAGE = 320;
  const OUT = 512;
  const MIN_Z = 1;
  const MAX_Z = 3;
  const FACE_API_JS =
    "https://cdn.jsdelivr.net/npm/face-api.js@0.22.2/dist/face-api.min.js";
  const FACE_API_MODELS =
    "https://cdn.jsdelivr.net/gh/justadudewhohacks/face-api.js@0.22.2/weights";

  const file = document.getElementById("photo-input");
  const form = document.getElementById("photo-form");
  const editor = document.getElementById("photo-crop-editor");
  const canvas = document.getElementById("photo-crop-canvas");
  const faceStatus = document.getElementById("photo-face-status");
  const zoom = document.getElementById("photo-zoom");
  const btnCancel = document.getElementById("photo-crop-cancel");
  const previewImg = document.getElementById("photo-preview-img");
  const fallback = document.getElementById("photo-preview-fallback");
  const faceDialog = document.getElementById("photo-face-dialog");
  const faceDialogText = document.getElementById("photo-face-dialog-text");
  const faceDialogOk = document.getElementById("photo-face-dialog-ok");
  if (!file || !form || !editor || !canvas) return;

  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  canvas.width = STAGE;
  canvas.height = STAGE;

  let bitmap = null;
  let scale = 1;
  let minScale = 1;
  let ox = 0;
  let oy = 0;
  let dragging = false;
  let lastX = 0;
  let lastY = 0;
  let faceBox = null;
  let objectUrl = null;
  let faceApiReady = null;

  function msg(key, fallbackText) {
    // data-msg-need-face → dataset.msgNeedFace
    const dataKey =
      "msg" +
      String(key)
        .split("-")
        .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
        .join("");
    return (faceStatus && faceStatus.dataset[dataKey]) || fallbackText;
  }

  function setStatus(kind, text) {
    if (!faceStatus) return;
    faceStatus.textContent = text || "";
    faceStatus.dataset.kind = kind || "";
    faceStatus.hidden = !text;
  }

  function showFacePopup(text) {
    const body =
      text ||
      msg(
        "need-face",
        "Per la sicurezza del tuo account scegli una foto in cui si vede bene il volto. Poi potrai ritagliarla tranquillamente."
      );
    if (faceDialog && typeof faceDialog.showModal === "function") {
      if (faceDialogText) faceDialogText.textContent = body;
      try {
        faceDialog.showModal();
        return;
      } catch (_e) {}
    }
    window.alert(body);
  }

  function closeFacePopup() {
    if (faceDialog && faceDialog.open) faceDialog.close();
  }

  if (faceDialogOk) {
    faceDialogOk.addEventListener("click", (e) => {
      e.preventDefault();
      closeFacePopup();
      file.value = "";
      file.click();
    });
  }
  if (faceDialog) {
    faceDialog.addEventListener("cancel", () => {
      /* allow Esc to close */
    });
  }

  function coverScale(bw, bh) {
    return Math.max(STAGE / bw, STAGE / bh);
  }

  function clampOffset() {
    if (!bitmap) return;
    const dw = bitmap.width * scale;
    const dh = bitmap.height * scale;
    const minOx = STAGE - dw;
    const minOy = STAGE - dh;
    if (dw <= STAGE) ox = (STAGE - dw) / 2;
    else ox = Math.min(0, Math.max(minOx, ox));
    if (dh <= STAGE) oy = (STAGE - dh) / 2;
    else oy = Math.min(0, Math.max(minOy, oy));
  }

  function draw() {
    if (!bitmap) return;
    clampOffset();
    ctx.clearRect(0, 0, STAGE, STAGE);
    ctx.save();
    ctx.beginPath();
    ctx.arc(STAGE / 2, STAGE / 2, STAGE / 2 - 2, 0, Math.PI * 2);
    ctx.closePath();
    ctx.clip();
    ctx.drawImage(bitmap, ox, oy, bitmap.width * scale, bitmap.height * scale);
    ctx.restore();

    ctx.beginPath();
    ctx.arc(STAGE / 2, STAGE / 2, STAGE * 0.36, 0, Math.PI * 2);
    ctx.strokeStyle = faceBox ? "rgba(61, 214, 165, 0.85)" : "rgba(255, 255, 255, 0.55)";
    ctx.lineWidth = 2;
    ctx.setLineDash(faceBox ? [] : [6, 5]);
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.beginPath();
    ctx.arc(STAGE / 2, STAGE / 2, STAGE / 2 - 1.5, 0, Math.PI * 2);
    ctx.strokeStyle = "rgba(0,0,0,0.35)";
    ctx.lineWidth = 3;
    ctx.stroke();
  }

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      if (document.querySelector('script[data-face-api="1"]')) {
        resolve();
        return;
      }
      const s = document.createElement("script");
      s.src = src;
      s.async = true;
      s.dataset.faceApi = "1";
      s.onload = () => resolve();
      s.onerror = () => reject(new Error("face-api load failed"));
      document.head.appendChild(s);
    });
  }

  async function ensureFaceApi() {
    if (faceApiReady) return faceApiReady;
    faceApiReady = (async () => {
      if (!window.faceapi) await loadScript(FACE_API_JS);
      if (!window.faceapi) throw new Error("face-api missing");
      if (!window.faceapi.nets.tinyFaceDetector.isLoaded) {
        await window.faceapi.nets.tinyFaceDetector.loadFromUri(FACE_API_MODELS);
      }
      return true;
    })().catch((err) => {
      faceApiReady = null;
      throw err;
    });
    return faceApiReady;
  }

  async function detectWithFaceApi(source) {
    await ensureFaceApi();
    const opts = new window.faceapi.TinyFaceDetectorOptions({
      inputSize: 320,
      scoreThreshold: 0.4,
    });
    const result = await window.faceapi.detectSingleFace(source, opts);
    if (!result) return null;
    const box = result.box;
    return { x: box.x, y: box.y, width: box.width, height: box.height };
  }

  async function detectWithNative(source) {
    if (typeof FaceDetector === "undefined") return null;
    try {
      const detector = new FaceDetector({ fastMode: true, maxDetectedFaces: 1 });
      const faces = await detector.detect(source);
      if (!faces || !faces.length) return null;
      const box = faces[0].boundingBox;
      return { x: box.x, y: box.y, width: box.width, height: box.height };
    } catch (_err) {
      return null;
    }
  }

  async function detectFace({ popupIfMissing } = { popupIfMissing: false }) {
    faceBox = null;
    if (!bitmap) return false;

    let box = null;
    let fromFullImage = false;

    if (objectUrl) {
      const probe = document.createElement("img");
      probe.decoding = "async";
      probe.src = objectUrl;
      await new Promise((resolve, reject) => {
        probe.onload = resolve;
        probe.onerror = reject;
      });
      box = await detectWithNative(probe);
      if (!box) box = await detectWithFaceApi(probe).catch(() => null);
      if (box) fromFullImage = true;
    }

    if (!box) {
      const stageImg = document.createElement("canvas");
      stageImg.width = STAGE;
      stageImg.height = STAGE;
      const sctx = stageImg.getContext("2d");
      sctx.drawImage(bitmap, ox, oy, bitmap.width * scale, bitmap.height * scale);
      box = await detectWithNative(stageImg);
      if (!box) box = await detectWithFaceApi(stageImg).catch(() => null);
      fromFullImage = false;
    }

    if (!box) {
      const warn = msg("no-face", "In questa foto non si vede un volto chiaro.");
      setStatus("warn", warn);
      if (popupIfMissing) showFacePopup(msg("need-face", warn));
      return false;
    }

    faceBox = box;
    if (fromFullImage) {
      const faceCx = box.x + box.width / 2;
      const faceCy = box.y + box.height / 2;
      const faceSize = Math.max(box.width, box.height) * 1.55;
      scale = Math.max(minScale, Math.min(MAX_Z * minScale, STAGE / faceSize));
      ox = STAGE / 2 - faceCx * scale;
      oy = STAGE / 2 - faceCy * scale;
      if (zoom) {
        zoom.min = String(MIN_Z);
        zoom.max = String(MAX_Z);
        zoom.step = "0.01";
        zoom.value = String(Math.min(MAX_Z, Math.max(MIN_Z, scale / minScale)));
      }
    }
    setStatus(
      "ok",
      msg("face-ok", "Perfetto. Se vuoi, puoi ancora spostare o ingrandire prima di salvare.")
    );
    draw();
    return true;
  }

  function openEditor() {
    editor.hidden = false;
    editor.removeAttribute("hidden");
  }

  function closeEditor() {
    editor.hidden = true;
    editor.setAttribute("hidden", "");
    if (bitmap && bitmap.close) {
      try {
        bitmap.close();
      } catch (_e) {}
    }
    bitmap = null;
    faceBox = null;
    if (objectUrl) {
      URL.revokeObjectURL(objectUrl);
      objectUrl = null;
    }
    file.value = "";
    setStatus("", "");
  }

  async function loadFile(f) {
    if (!f || !f.type.startsWith("image/")) return;
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    objectUrl = URL.createObjectURL(f);
    if (bitmap && bitmap.close) {
      try {
        bitmap.close();
      } catch (_e) {}
    }
    bitmap = await createImageBitmap(f);
    minScale = coverScale(bitmap.width, bitmap.height);
    scale = minScale;
    ox = (STAGE - bitmap.width * scale) / 2;
    oy = (STAGE - bitmap.height * scale) / 2;
    if (zoom) {
      zoom.min = String(MIN_Z);
      zoom.max = String(MAX_Z);
      zoom.value = "1";
    }
    openEditor();
    draw();
    const ok = await detectFace({ popupIfMissing: true });
    draw();
    if (!ok) {
      // Keep editor open so they can try another file from the popup.
    }
  }

  function exportBlob() {
    return new Promise((resolve, reject) => {
      if (!bitmap) {
        reject(new Error("no image"));
        return;
      }
      const out = document.createElement("canvas");
      out.width = OUT;
      out.height = OUT;
      const octx = out.getContext("2d");
      const ratio = OUT / STAGE;
      octx.beginPath();
      octx.arc(OUT / 2, OUT / 2, OUT / 2, 0, Math.PI * 2);
      octx.closePath();
      octx.clip();
      octx.fillStyle = "#111";
      octx.fillRect(0, 0, OUT, OUT);
      octx.drawImage(
        bitmap,
        ox * ratio,
        oy * ratio,
        bitmap.width * scale * ratio,
        bitmap.height * scale * ratio
      );
      out.toBlob(
        (blob) => {
          if (!blob) reject(new Error("export failed"));
          else resolve(blob);
        },
        "image/jpeg",
        0.92
      );
    });
  }

  file.addEventListener("change", () => {
    const f = file.files && file.files[0];
    if (!f) return;
    loadFile(f).catch(() => {
      setStatus("warn", msg("load-fail", "Impossibile leggere questa immagine."));
      showFacePopup(msg("load-fail", "Impossibile leggere questa immagine."));
    });
  });

  if (zoom) {
    zoom.addEventListener("input", () => {
      if (!bitmap) return;
      const z = Number(zoom.value) || 1;
      const prev = scale;
      const next = minScale * Math.min(MAX_Z, Math.max(MIN_Z, z));
      const cx = STAGE / 2;
      const cy = STAGE / 2;
      const imgX = (cx - ox) / prev;
      const imgY = (cy - oy) / prev;
      scale = next;
      ox = cx - imgX * scale;
      oy = cy - imgY * scale;
      draw();
    });
  }

  function pointerDown(e) {
    if (!bitmap) return;
    dragging = true;
    const p = e.touches ? e.touches[0] : e;
    lastX = p.clientX;
    lastY = p.clientY;
    canvas.setPointerCapture?.(e.pointerId);
    e.preventDefault();
  }
  function pointerMove(e) {
    if (!dragging || !bitmap) return;
    const p = e.touches ? e.touches[0] : e;
    ox += p.clientX - lastX;
    oy += p.clientY - lastY;
    lastX = p.clientX;
    lastY = p.clientY;
    draw();
    e.preventDefault();
  }
  function pointerUp() {
    dragging = false;
  }

  canvas.addEventListener("pointerdown", pointerDown);
  canvas.addEventListener("pointermove", pointerMove);
  canvas.addEventListener("pointerup", pointerUp);
  canvas.addEventListener("pointercancel", pointerUp);
  canvas.addEventListener("touchstart", pointerDown, { passive: false });
  canvas.addEventListener("touchmove", pointerMove, { passive: false });
  canvas.addEventListener("touchend", pointerUp);

  if (btnCancel) {
    btnCancel.addEventListener("click", (e) => {
      e.preventDefault();
      closeEditor();
    });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!bitmap) {
      if (file.files && file.files[0]) {
        HTMLFormElement.prototype.submit.call(form);
      } else {
        showFacePopup(
          msg(
            "pick-first",
            "Scegli prima una foto dal tuo dispositivo, poi salvala qui."
          )
        );
      }
      return;
    }
    const ok = faceBox ? true : await detectFace({ popupIfMissing: true });
    if (!ok) {
      return;
    }
    const btn = form.querySelector('button[type="submit"]');
    if (btn) btn.disabled = true;
    try {
      const blob = await exportBlob();
      const fd = new FormData();
      fd.append("photo", blob, "avatar.jpg");
      const res = await fetch(form.action || "/anagrafica/foto", {
        method: "POST",
        body: fd,
        credentials: "same-origin",
        redirect: "follow",
      });
      if (previewImg) {
        const url = URL.createObjectURL(blob);
        previewImg.src = url;
        previewImg.hidden = false;
        previewImg.removeAttribute("hidden");
      }
      if (fallback) {
        fallback.hidden = true;
        fallback.setAttribute("hidden", "");
      }
      window.location.href = res.url || "/anagrafica";
    } catch (_err) {
      setStatus("warn", msg("save-fail", "Salvataggio non riuscito. Riprova."));
      if (btn) btn.disabled = false;
    }
  });
})();
