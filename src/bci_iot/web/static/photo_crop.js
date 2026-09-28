/**
 * Profile photo picker: face-aware framing + zoom/pan crop.
 * Exports a square JPEG of the circular avatar area.
 */
(function () {
  const STAGE = 280;
  const OUT = 512;
  const MIN_Z = 1;
  const MAX_Z = 3;

  const file = document.getElementById("photo-input");
  const form = document.getElementById("photo-form");
  const editor = document.getElementById("photo-crop-editor");
  const canvas = document.getElementById("photo-crop-canvas");
  const faceStatus = document.getElementById("photo-face-status");
  const zoom = document.getElementById("photo-zoom");
  const btnCancel = document.getElementById("photo-crop-cancel");
  const previewImg = document.getElementById("photo-preview-img");
  const fallback = document.getElementById("photo-preview-fallback");
  if (!file || !form || !editor || !canvas) return;

  const ctx = canvas.getContext("2d");
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

  function setStatus(kind, text) {
    if (!faceStatus) return;
    faceStatus.textContent = text || "";
    faceStatus.dataset.kind = kind || "";
    faceStatus.hidden = !text;
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
    // Allow centering when image is smaller than stage after scale (shouldn't with cover).
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

    // Face guide ring
    ctx.beginPath();
    ctx.arc(STAGE / 2, STAGE / 2, STAGE * 0.36, 0, Math.PI * 2);
    ctx.strokeStyle = faceBox ? "rgba(61, 214, 165, 0.85)" : "rgba(255, 255, 255, 0.55)";
    ctx.lineWidth = 2;
    ctx.setLineDash(faceBox ? [] : [6, 5]);
    ctx.stroke();
    ctx.setLineDash([]);

    // Outer rim
    ctx.beginPath();
    ctx.arc(STAGE / 2, STAGE / 2, STAGE / 2 - 1.5, 0, Math.PI * 2);
    ctx.strokeStyle = "rgba(0,0,0,0.35)";
    ctx.lineWidth = 3;
    ctx.stroke();
  }

  async function detectFace() {
    faceBox = null;
    if (!bitmap) return;
    if (typeof FaceDetector === "undefined") {
      setStatus(
        "hint",
        faceStatus?.dataset.msgGuide ||
          "Inquadra il volto nel cerchio. Puoi ingrandire e spostare la foto."
      );
      return;
    }
    try {
      const detector = new FaceDetector({ fastMode: true, maxDetectedFaces: 1 });
      // Some browsers need an HTMLImageElement, not ImageBitmap.
      const probe = document.createElement("img");
      probe.src = objectUrl || "";
      await new Promise((resolve, reject) => {
        probe.onload = resolve;
        probe.onerror = reject;
      });
      const faces = await detector.detect(probe);
      if (!faces || !faces.length) {
        setStatus(
          "warn",
          faceStatus?.dataset.msgNoFace ||
            "Non vediamo un volto chiaro. Inquadra meglio il viso nell’area tonda."
        );
        return;
      }
      const box = faces[0].boundingBox;
      faceBox = box;
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
      setStatus(
        "ok",
        faceStatus?.dataset.msgFaceOk ||
          "Volto trovato. Puoi ancora ingrandire o spostare prima di salvare."
      );
      draw();
    } catch (_err) {
      setStatus(
        "hint",
        faceStatus?.dataset.msgGuide ||
          "Inquadra il volto nel cerchio. Puoi ingrandire e spostare la foto."
      );
    }
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
    await detectFace();
    draw();
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
      setStatus("warn", faceStatus?.dataset.msgLoadFail || "Impossibile leggere questa immagine.");
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
      // Zoom around center of stage
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
      // No new crop open: if file selected without editor, fall back
      if (file.files && file.files[0]) {
        HTMLFormElement.prototype.submit.call(form);
      }
      return;
    }
    if (typeof FaceDetector !== "undefined" && !faceBox) {
      const msg =
        faceStatus?.dataset.msgNeedFace ||
        "Serve un volto visibile nell’area tonda per dare un’identità all’account. Sposta o ingrandisci la foto.";
      setStatus("warn", msg);
      // Re-run detection in case user framed it
      await detectFace();
      if (!faceBox) {
        return;
      }
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
      // Reload to pick up flash + saved path
      window.location.href = res.url || "/anagrafica";
    } catch (_err) {
      setStatus("warn", faceStatus?.dataset.msgSaveFail || "Salvataggio non riuscito. Riprova.");
      if (btn) btn.disabled = false;
    }
  });
})();
