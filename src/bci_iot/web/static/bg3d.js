/* 3D background: neural field on public pages, vault shield on private pages. */
(function () {
  const canvas = document.getElementById("iris-bg");
  if (!canvas || !canvas.getContext) return;
  const skip =
    window.matchMedia("(max-width: 859px), (pointer: coarse), (prefers-reduced-motion: reduce)").matches ||
    document.body.classList.contains("page-chat") ||
    document.body.classList.contains("page-ai-chat") ||
    document.body.classList.contains("page-contact-mail");
  if (skip) {
    canvas.remove();
    return;
  }
  const ctx = canvas.getContext("2d");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const mode = document.body.classList.contains("page-private") ? "vault" : "neural";

  let width = 0;
  let height = 0;
  let mouseX = 0.5;
  let mouseY = 0.5;
  let tick = 0;
  const nodes = [];
  let shells = [];
  let rings = [];

  function isDark() {
    return document.documentElement.getAttribute("data-theme-resolved") === "dark";
  }

  function palette() {
    const dark = isDark();
    if (mode === "vault") {
      return dark
        ? {
            line: "rgba(90, 210, 170, 0.36)",
            mesh: "rgba(140, 230, 195, 0.22)",
            ring: "rgba(212, 175, 90, 0.4)",
            dot: "rgba(230, 210, 140, 0.78)",
            glow: "rgba(61, 214, 165, 0.16)",
          }
        : {
            line: "rgba(18, 92, 72, 0.24)",
            mesh: "rgba(26, 110, 85, 0.14)",
            ring: "rgba(150, 118, 40, 0.34)",
            dot: "rgba(120, 90, 28, 0.62)",
            glow: "rgba(26, 122, 92, 0.1)",
          };
    }
    return dark
      ? { line: "rgba(180, 220, 210, 0.32)", dot: "rgba(210, 245, 235, 0.72)" }
      : { line: "rgba(20, 70, 60, 0.28)", dot: "rgba(26, 90, 75, 0.6)" };
  }

  function resize() {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
  }

  function rotY(p, a) {
    const c = Math.cos(a);
    const s = Math.sin(a);
    return { x: p.x * c - p.z * s, y: p.y, z: p.x * s + p.z * c };
  }

  function rotX(p, a) {
    const c = Math.cos(a);
    const s = Math.sin(a);
    return { x: p.x, y: p.y * c - p.z * s, z: p.y * s + p.z * c };
  }

  function project(p, rot, parallax, scale) {
    let q = rotY(p, rot);
    q = rotX(q, rot * 0.32);
    const px = (mouseX - 0.5) * parallax;
    const py = (mouseY - 0.5) * parallax * 0.8;
    const depth = 2.15 / (2.15 + q.z);
    const span = scale || Math.min(width, height) * 0.52;
    return {
      x: width * 0.5 + (q.x + px) * depth * span,
      y: height * 0.5 + (q.y + py) * depth * span,
      depth,
    };
  }

  function fibSphere(count, radius) {
    const pts = [];
    const golden = Math.PI * (3 - Math.sqrt(5));
    for (let i = 0; i < count; i += 1) {
      const y = 1 - (i / Math.max(count - 1, 1)) * 2;
      const r = Math.sqrt(Math.max(0, 1 - y * y)) * radius;
      const theta = golden * i;
      pts.push({
        x: Math.cos(theta) * r,
        y: y * radius,
        z: Math.sin(theta) * r,
      });
    }
    return pts;
  }

  function connectNear(points, maxDist) {
    const edges = [];
    const limit = maxDist * maxDist;
    for (let i = 0; i < points.length; i += 1) {
      for (let j = i + 1; j < points.length; j += 1) {
        const dx = points[i].x - points[j].x;
        const dy = points[i].y - points[j].y;
        const dz = points[i].z - points[j].z;
        const d = dx * dx + dy * dy + dz * dz;
        if (d < limit) edges.push([i, j]);
      }
    }
    return edges;
  }

  function seedNeural() {
    nodes.length = 0;
    const count = Math.min(420, Math.max(240, Math.floor((width * height) / 3800)));
    for (let i = 0; i < count; i += 1) {
      nodes.push({
        x: Math.random() * 2.8 - 1.4,
        y: Math.random() * 2.6 - 1.3,
        z: Math.random() * 2.4 - 1.2,
        s: 0.5 + Math.random() * 1.7,
      });
    }
  }

  function seedVault() {
    shells = [
      { points: fibSphere(120, 0.55), rot: 0.4, scale: 0.42 },
      { points: fibSphere(160, 1), rot: 0.56, scale: 0.58 },
      { points: fibSphere(110, 1.38), rot: 0.3, scale: 0.74 },
      { points: fibSphere(90, 1.78), rot: 0.22, scale: 0.9 },
    ];
    shells.forEach((shell) => {
      const span = shell.points[0] ? Math.abs(shell.points[0].x) + 0.35 : 0.45;
      shell.edges = connectNear(shell.points, span * 0.42);
    });
    rings = [];
    for (let r = 0; r < 7; r += 1) {
      const pts = [];
      const n = 64;
      const radius = 0.48 + r * 0.2;
      const tiltX = (r - 3) * 0.22;
      const tiltY = r * 0.17;
      for (let i = 0; i < n; i += 1) {
        const a = (i / n) * Math.PI * 2;
        let p = { x: Math.cos(a) * radius, y: 0, z: Math.sin(a) * radius };
        p = rotX(p, tiltX);
        p = rotY(p, tiltY);
        pts.push(p);
      }
      rings.push(pts);
    }
  }

  function drawNeural() {
    tick += reduceMotion ? 0 : 0.0018;
    ctx.clearRect(0, 0, width, height);
    const colors = palette();
    const span = Math.max(width, height) * 0.56;
    const link = Math.min(280, Math.max(170, Math.min(width, height) * 0.24));
    const projected = nodes.map((node) => {
      const p = project(node, tick, 0.28, span);
      return { ...p, s: node.s };
    });
    ctx.lineWidth = 1;
    for (let i = 0; i < projected.length; i += 1) {
      for (let j = i + 1; j < projected.length; j += 1) {
        const a = projected[i];
        const b = projected[j];
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < link) {
          ctx.strokeStyle = colors.line;
          ctx.globalAlpha = (1 - dist / link) * 0.95;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }
    }
    ctx.globalAlpha = 1;
    projected.forEach((point) => {
      ctx.fillStyle = colors.dot;
      ctx.beginPath();
      ctx.arc(point.x, point.y, point.s * point.depth * 2.35, 0, Math.PI * 2);
      ctx.fill();
    });
  }

  function drawVault() {
    tick += reduceMotion ? 0 : 0.00115;
    ctx.clearRect(0, 0, width, height);
    const colors = palette();
    const pulse = 0.55 + Math.sin(tick * 2.05) * 0.22;
    const span = Math.min(width, height) * 0.78;

    const cx = width * 0.5;
    const cy = height * 0.5;
    const halo = Math.min(width, height) * 0.48;
    const glow = ctx.createRadialGradient(cx, cy, halo * 0.12, cx, cy, halo);
    glow.addColorStop(0, colors.glow);
    glow.addColorStop(1, "rgba(0,0,0,0)");
    ctx.globalAlpha = 1;
    ctx.fillStyle = glow;
    ctx.beginPath();
    ctx.arc(cx, cy, halo, 0, Math.PI * 2);
    ctx.fill();

    rings.forEach((ring, index) => {
      ctx.beginPath();
      ring.forEach((pt, i) => {
        const p = project(pt, tick * (0.55 + index * 0.08), 0.1, span);
        if (i === 0) ctx.moveTo(p.x, p.y);
        else ctx.lineTo(p.x, p.y);
      });
      ctx.closePath();
      ctx.strokeStyle = colors.ring;
      ctx.globalAlpha = 0.22 + (index % 3) * 0.08;
      ctx.lineWidth = index === 3 ? 1.7 : 1;
      ctx.stroke();
    });

    shells.forEach((shell) => {
      const verts = shell.points.map((pt) => project(pt, tick * shell.rot, 0.1, span * (0.72 + shell.scale * 0.2)));
      ctx.lineWidth = 1;
      ctx.strokeStyle = colors.mesh;
      ctx.globalAlpha = 0.42;
      shell.edges.forEach(([a, b]) => {
        ctx.beginPath();
        ctx.moveTo(verts[a].x, verts[a].y);
        ctx.lineTo(verts[b].x, verts[b].y);
        ctx.stroke();
      });
      ctx.globalAlpha = 0.85;
      verts.forEach((p) => {
        ctx.fillStyle = colors.dot;
        ctx.beginPath();
        ctx.arc(p.x, p.y, (1.15 + pulse * 0.5) * p.depth, 0, Math.PI * 2);
        ctx.fill();
      });
    });
  }

  function draw() {
    if (mode === "vault") drawVault();
    else drawNeural();
    if (!reduceMotion) window.requestAnimationFrame(draw);
  }

  function seed() {
    if (mode === "vault") seedVault();
    else seedNeural();
  }

  resize();
  seed();
  window.addEventListener("resize", () => {
    resize();
    seed();
    if (reduceMotion) draw();
  });
  window.addEventListener(
    "pointermove",
    (event) => {
      mouseX = event.clientX / Math.max(window.innerWidth, 1);
      mouseY = event.clientY / Math.max(window.innerHeight, 1);
    },
    { passive: true }
  );
  draw();
})();
