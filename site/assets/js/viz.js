/* Interactive visualizations. Dependency-free, SVG-based, theme-aware (colors come from CSS variables).

   Usage in a chapter:
     <div class="viz" data-viz="graph-steps">
       <script type="application/json">{ ...config... }</script>
     </div>

   Built-in types (see AUTHORING.md for full config reference):
     graph-steps     step-through animation over a graph (BFS, expansion, paths, PPR scores...)
     flow            pipeline animation: a packet travels through stages, caption per stage
     chunker         live chunk size / overlap slider over a passage
     embedding-space 2D similarity search with draggable query and k slider
     pagerank        live (personalized) PageRank; click nodes to toggle seeds
     louvain         step-through Louvain local-moving phase with live modularity
     text-to-graph   highlights mentions in a passage and grows the extracted graph
     map-reduce      global search: map scores per community, filter, reduce
     rrf             reciprocal rank fusion of several rankings with k slider
     token-budget    stacked context-window budget with sliders

   Custom: GRFSViz.register("my-viz", (el, cfg, api) => { ... }) in a <script> after this file. */
(function () {
  "use strict";
  const NS = "http://www.w3.org/2000/svg";
  const registry = {};
  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- tiny helpers ---------- */
  function svgEl(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs || {}) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function h(tag, attrs, parent, text) {
    const e = document.createElement(tag);
    for (const k in attrs || {}) {
      if (k === "class") e.className = attrs[k];
      else e.setAttribute(k, attrs[k]);
    }
    if (text != null) e.textContent = text;
    if (parent) parent.appendChild(e);
    return e;
  }
  function groupColor(g) {
    const n = typeof g === "number" ? g : hashStr(String(g == null ? "" : g));
    return "var(--c" + ((((n - 1) % 8) + 8) % 8 + 1) + ")";
  }
  function hashStr(s) { let x = 0; for (let i = 0; i < s.length; i++) x = (x * 31 + s.charCodeAt(i)) | 0; return Math.abs(x) % 8 + 1; }
  function mulberry(seed) { return function () { seed |= 0; seed = (seed + 0x6D2B79F5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
  function edgeKey(a, b) { return a + ">" + b; }
  function fmt(x, d) { return Number(x).toFixed(d == null ? 3 : d); }
  function setCaption(el, html) { el.innerHTML = html || ""; }

  function frame(el, cfg) {
    el.innerHTML = "";
    const head = h("div", { class: "viz-head" }, el);
    h("span", { class: "viz-title" }, head, cfg.title || "");
    h("span", { class: "viz-badge" }, head, "Interactive");
    if (cfg.subtitle) h("span", { class: "viz-sub" }, head, cfg.subtitle);
    const stage = h("div", { class: "viz-stage" }, el);
    return { head, stage };
  }
  function controls(el) { return h("div", { class: "viz-controls" }, el); }
  function button(parent, label, cls) { const b = h("button", { type: "button", class: cls || "" }, parent, label); return b; }

  /* ---------- force layout (deterministic) ---------- */
  function layoutGraph(nodes, edges, W, H, opts) {
    opts = opts || {};
    const rnd = mulberry(opts.seed || 7);
    const byId = {};
    const allFixed = nodes.every((n) => n.x != null && n.y != null);
    nodes.forEach((n) => {
      byId[n.id] = n;
      if (n.x != null && n.y != null) { n._x = (n.x / 100) * W; n._y = (n.y / 100) * H; }
      else { n._x = W / 2 + (rnd() - 0.5) * W * 0.6; n._y = H / 2 + (rnd() - 0.5) * H * 0.6; }
    });
    if (allFixed) return byId;
    const k = Math.sqrt((W * H) / Math.max(nodes.length, 1)) * (opts.spread || 0.75);
    for (let it = 0; it < 400; it++) {
      const t = 1 - it / 400;
      nodes.forEach((n) => { n._dx = 0; n._dy = 0; });
      for (let i = 0; i < nodes.length; i++) for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i], b = nodes[j];
        let dx = a._x - b._x, dy = a._y - b._y; let d = Math.hypot(dx, dy) || 0.01;
        const f = (k * k) / d;
        dx /= d; dy /= d; a._dx += dx * f; a._dy += dy * f; b._dx -= dx * f; b._dy -= dy * f;
      }
      edges.forEach((e) => {
        const a = byId[e.source], b = byId[e.target]; if (!a || !b) return;
        let dx = a._x - b._x, dy = a._y - b._y; const d = Math.hypot(dx, dy) || 0.01;
        const f = (d * d) / k; dx /= d; dy /= d;
        a._dx -= dx * f; a._dy -= dy * f; b._dx += dx * f; b._dy += dy * f;
      });
      nodes.forEach((n) => {
        if (n.x != null && n.y != null) return;
        n._dx += (W / 2 - n._x) * 0.02 * k; n._dy += (H / 2 - n._y) * 0.02 * k;
        const d = Math.hypot(n._dx, n._dy) || 1; const step = Math.min(d, k * 0.5 * t + 1);
        n._x += (n._dx / d) * step; n._y += (n._dy / d) * step;
      });
    }
    // fit to box
    const pad = opts.pad || 46;
    const xs = nodes.map((n) => n._x), ys = nodes.map((n) => n._y);
    const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
    nodes.forEach((n) => {
      n._x = pad + ((n._x - minX) / (maxX - minX || 1)) * (W - 2 * pad);
      n._y = pad + ((n._y - minY) / (maxY - minY || 1)) * (H - 2 * pad);
    });
    return byId;
  }

  /* Renders nodes/edges into an svg; returns handles for styling. Supports dragging. */
  function drawGraph(svg, cfg, W, H) {
    const nodes = cfg.nodes.map((n) => Object.assign({}, n));
    const edges = cfg.edges.map((e) => Object.assign({}, e));
    const byId = layoutGraph(nodes, edges, W, H, cfg.layout);
    const directed = !!cfg.directed;
    const defs = svgEl("defs", {}, svg);
    const uid = Math.random().toString(36).slice(2, 8);
    ["", "-hot"].forEach((suffix) => {
      const m = svgEl("marker", { id: "arr" + suffix + uid, viewBox: "0 0 10 10", refX: 10, refY: 5, markerWidth: 9, markerHeight: 9, markerUnits: "userSpaceOnUse", orient: "auto-start-reverse" }, defs);
      svgEl("path", { d: "M0,0 L10,5 L0,10 z", style: "fill:" + (suffix ? "var(--edge)" : "var(--muted)") }, m);
    });
    const gE = svgEl("g", {}, svg), gL = svgEl("g", {}, svg), gN = svgEl("g", {}, svg);
    const edgeEls = {}, labelEls = {}, nodeEls = {};
    const radius = (n) => n._r || n.size || cfg.nodeRadius || 13;
    edges.forEach((e) => {
      const line = svgEl("line", { class: "g-edge" }, gE);
      if (directed || e.directed) line.setAttribute("marker-end", "url(#arr" + uid + ")");
      edgeEls[edgeKey(e.source, e.target)] = line;
      e._el = line;
      if (e.label && cfg.edgeLabels !== false) {
        const t = svgEl("text", { class: "g-edge-label", "text-anchor": "middle" }, gL);
        t.textContent = e.label; e._label = t; labelEls[edgeKey(e.source, e.target)] = t;
      }
    });
    nodes.forEach((n) => {
      const g = svgEl("g", { class: "g-node", tabindex: cfg.focusable ? 0 : -1 }, gN);
      const col = n.color ? n.color : groupColor(n.group || 1);
      const c = svgEl("circle", { r: radius(n), style: "fill:color-mix(in srgb, " + col + " 24%, var(--panel));stroke:" + col }, g);
      const t = svgEl("text", { "text-anchor": "middle", dy: radius(n) + 14 }, g);
      t.textContent = n.label != null ? n.label : n.id;
      const s = svgEl("text", { class: "score", "text-anchor": "middle", dy: 4 }, g);
      n._g = g; n._c = c; n._t = t; n._s = s; n._col = col;
      nodeEls[n.id] = n;
    });
    function place() {
      edges.forEach((e) => {
        const a = byId[e.source], b = byId[e.target]; if (!a || !b) return;
        const dx = b._x - a._x, dy = b._y - a._y, d = Math.hypot(dx, dy) || 1;
        const ra = radius(a), rb = radius(b) + ((directed || e.directed) ? 3 : 0);
        e._el.setAttribute("x1", a._x + (dx / d) * ra); e._el.setAttribute("y1", a._y + (dy / d) * ra);
        e._el.setAttribute("x2", b._x - (dx / d) * rb); e._el.setAttribute("y2", b._y - (dy / d) * rb);
        if (e._label) { e._label.setAttribute("x", (a._x + b._x) / 2); e._label.setAttribute("y", (a._y + b._y) / 2 - 4); }
      });
      nodes.forEach((n) => { n._g.setAttribute("transform", "translate(" + n._x + "," + n._y + ")"); n._t.setAttribute("dy", radius(n) + 14); });
    }
    place();
    // dragging
    let drag = null;
    function pt(ev) { const r = svg.getBoundingClientRect(); return { x: ((ev.clientX - r.left) / r.width) * W, y: ((ev.clientY - r.top) / r.height) * H }; }
    nodes.forEach((n) => {
      n._g.addEventListener("pointerdown", (ev) => { drag = { n, moved: false }; n._g.setPointerCapture(ev.pointerId); });
      n._g.addEventListener("pointermove", (ev) => { if (!drag || drag.n !== n) return; const p = pt(ev); n._x = Math.max(10, Math.min(W - 10, p.x)); n._y = Math.max(10, Math.min(H - 10, p.y)); drag.moved = true; place(); });
      n._g.addEventListener("pointerup", () => { if (drag && !drag.moved && cfg.onNodeClick) cfg.onNodeClick(n); drag = null; });
      n._g.addEventListener("keydown", (ev) => { if ((ev.key === "Enter" || ev.key === " ") && cfg.onNodeClick) { ev.preventDefault(); cfg.onNodeClick(n); } });
    });
    return { nodes, edges, byId, edgeEls, nodeEls, labelEls, place, radius, getEdge: (a, b) => edgeEls[edgeKey(a, b)] || edgeEls[edgeKey(b, a)] };
  }

  function legend(el, map) {
    if (!map) return;
    const lg = h("div", { class: "viz-legend" }, el);
    Object.keys(map).forEach((k) => {
      const s = h("span", {}, lg);
      const i = h("i", {}, s);
      i.style.background = groupColor(isNaN(+k) ? k : +k);
      s.appendChild(document.createTextNode(map[k]));
    });
  }

  /* Step player shared by several visualizations */
  function player(el, n, render, opts) {
    opts = opts || {};
    const bar = controls(el);
    const reset = button(bar, "Reset");
    const prev = button(bar, "Back");
    const play = button(bar, "Play", "primary");
    const next = button(bar, "Next");
    h("span", { class: "grow" }, bar);
    const no = h("span", { class: "stepno" }, bar);
    let i = 0, timer = null;
    function go(k) {
      i = Math.max(0, Math.min(n - 1, k));
      render(i);
      no.textContent = "Step " + (i + 1) + " of " + n;
      prev.disabled = i === 0; next.disabled = i === n - 1;
      if (i === n - 1) stop();
    }
    function stop() { clearInterval(timer); timer = null; play.textContent = i === n - 1 ? "Replay" : "Play"; }
    play.addEventListener("click", () => {
      if (timer) return stop();
      if (i === n - 1) go(0);
      play.textContent = "Pause";
      timer = setInterval(() => (i < n - 1 ? go(i + 1) : stop()), opts.interval || 1900);
    });
    prev.addEventListener("click", () => { stop(); go(i - 1); });
    next.addEventListener("click", () => { stop(); go(i + 1); });
    reset.addEventListener("click", () => { stop(); go(0); });
    go(0);
    return { go, bar };
  }

  /* ================= graph-steps ================= */
  registry["graph-steps"] = function (el, cfg) {
    const W = cfg.width || 720, H = cfg.height || 380;
    const { stage } = frame(el, cfg);
    const svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, role: "img", "aria-label": cfg.title || "Graph animation" }, stage);
    const G = drawGraph(svg, cfg, W, H);
    const cap = h("div", { class: "viz-caption", "aria-live": "polite" }, el);
    const steps = cfg.steps && cfg.steps.length ? cfg.steps : [{ caption: cfg.caption || "" }];
    legend(el, cfg.legend);
    function render(i) {
      const s = steps[i];
      const dim = s.dim != null ? s.dim : cfg.dim !== false && (s.active || s.visited);
      el.classList.toggle("dimmed", !!dim);
      const active = new Set(s.active || []), visited = new Set(s.visited || []);
      G.nodes.forEach((n) => {
        n._g.classList.toggle("active", active.has(n.id));
        n._g.classList.toggle("visited", visited.has(n.id) && !active.has(n.id));
        const hot = active.has(n.id) || visited.has(n.id);
        n._c.style.fill = hot ? "color-mix(in srgb, " + n._col + " " + (active.has(n.id) ? 70 : 45) + "%, var(--panel))" : "color-mix(in srgb, " + n._col + " 24%, var(--panel))";
        const sc = s.scores && s.scores[n.id];
        n._s.textContent = sc != null ? (typeof sc === "number" ? fmt(sc, cfg.scoreDigits == null ? 2 : cfg.scoreDigits) : sc) : "";
        n._s.setAttribute("dy", -G.radius(n) - 6);
        if (s.scores && cfg.scaleByScore) {
          const vals = Object.values(s.scores).filter((v) => typeof v === "number");
          const mx = Math.max(...vals, 1e-9);
          n._r = (cfg.nodeRadius || 13) * (0.6 + 1.2 * ((sc || 0) / mx));
          n._c.setAttribute("r", n._r);
        }
      });
      const aE = new Set((s.edges || []).map(norm)), vE = new Set((s.visitedEdges || []).map(norm));
      G.edges.forEach((e) => {
        const k1 = edgeKey(e.source, e.target), k2 = edgeKey(e.target, e.source);
        const isA = aE.has(k1) || aE.has(k2), isV = vE.has(k1) || vE.has(k2);
        e._el.classList.toggle("active", isA);
        e._el.classList.toggle("visited", isV && !isA);
        if (isA) { if (e._el.hasAttribute("marker-end")) e._el.setAttribute("marker-end", e._el.getAttribute("marker-end").replace("#arr", "#arr-hot").replace("-hot-hot", "-hot")); }
        else if (e._el.hasAttribute("marker-end")) e._el.setAttribute("marker-end", e._el.getAttribute("marker-end").replace("#arr-hot", "#arr"));
        if (e._label) e._label.classList.toggle("off", !(isA || isV) && !s.showAllLabels);
      });
      G.place();
      setCaption(cap, s.caption);
    }
    function norm(k) { return String(k).replace("->", ">").replace("|", ">"); }
    if (steps.length > 1) player(el, steps.length, render, { interval: cfg.interval });
    else render(0);
  };

  /* ================= flow ================= */
  registry["flow"] = function (el, cfg) {
    const stages = cfg.stages || [];
    const { stage } = frame(el, cfg);
    const perRow = cfg.perRow || Math.min(stages.length, 4);
    const bw = 150, bh = 54, gx = 34, gy = 46;
    const rows = Math.ceil(stages.length / perRow);
    const W = perRow * bw + (perRow - 1) * gx + 40, H = rows * bh + (rows - 1) * gy + 40;
    const svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, role: "img", "aria-label": cfg.title || "Pipeline" }, stage);
    svg.style.maxHeight = H * 1.3 + "px";
    const pos = stages.map((s, i) => {
      const r = Math.floor(i / perRow); let c = i % perRow;
      if (cfg.snake !== false && r % 2 === 1) c = perRow - 1 - c;
      return { x: 20 + c * (bw + gx), y: 20 + r * (bh + gy) };
    });
    const arrows = [];
    const fid = "fa" + Math.random().toString(36).slice(2, 8);
    const fm = svgEl("marker", { id: fid, viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto" }, svgEl("defs", {}, svg));
    svgEl("path", { d: "M0,0 L10,5 L0,10 z", style: "fill:var(--muted)" }, fm);
    for (let i = 0; i < stages.length - 1; i++) {
      const a = pos[i], b = pos[i + 1];
      let d;
      if (a.y === b.y) { const dir = b.x > a.x ? 1 : -1; const x1 = dir > 0 ? a.x + bw : a.x, x2 = dir > 0 ? b.x : b.x + bw; d = "M" + x1 + "," + (a.y + bh / 2) + " L" + x2 + "," + (b.y + bh / 2); }
      else d = "M" + (a.x + bw / 2) + "," + (a.y + bh) + " L" + (b.x + bw / 2) + "," + b.y;
      arrows.push(svgEl("path", { d, class: "flow-arrow", "marker-end": "url(#" + fid + ")" }, svg));
    }
    const boxes = stages.map((s, i) => {
      const g = svgEl("g", { class: "flow-stage" }, svg);
      svgEl("rect", { x: pos[i].x, y: pos[i].y, width: bw, height: bh, rx: 8, class: "d-box" }, g);
      const lines = wrapText(s.label, 20);
      lines.forEach((ln, k) => {
        const t = svgEl("text", { x: pos[i].x + bw / 2, y: pos[i].y + bh / 2 + (k - (lines.length - 1) / 2) * 15 + 4, "text-anchor": "middle", class: "d-text bold" }, g);
        t.textContent = ln;
      });
      return g;
    });
    const packet = svgEl("circle", { r: 6, class: "packet", opacity: 0 }, svg);
    const cap = h("div", { class: "viz-caption", "aria-live": "polite" }, el);
    function render(i) {
      boxes.forEach((b, k) => { b.classList.toggle("active", k === i); b.classList.toggle("done", k < i); });
      arrows.forEach((a, k) => a.classList.toggle("done", k < i));
      const s = stages[i];
      setCaption(cap, "<strong>" + s.label + ".</strong> " + (s.detail || ""));
      if (i > 0 && !reduceMotion) {
        const path = arrows[i - 1]; const L = path.getTotalLength(); const t0 = performance.now();
        packet.setAttribute("opacity", 1);
        const tick = (now) => { const p = Math.min(1, (now - t0) / 600); const q = path.getPointAtLength(L * p); packet.setAttribute("cx", q.x); packet.setAttribute("cy", q.y); if (p < 1) requestAnimationFrame(tick); else packet.setAttribute("opacity", 0); };
        requestAnimationFrame(tick);
      }
    }
    player(el, stages.length, render, { interval: cfg.interval || 2200 });
  };
  function wrapText(s, n) {
    const words = String(s).split(/\s+/); const out = []; let cur = "";
    words.forEach((w) => { if ((cur + " " + w).trim().length > n && cur) { out.push(cur); cur = w; } else cur = (cur + " " + w).trim(); });
    if (cur) out.push(cur); return out;
  }

  /* ================= chunker ================= */
  registry["chunker"] = function (el, cfg) {
    frame(el, cfg);
    const words = String(cfg.text).trim().split(/\s+/);
    const body = h("div", { class: "viz-text" }, el.querySelector(".viz-stage"));
    const cap = h("div", { class: "viz-caption", "aria-live": "polite" }, el);
    const bar = controls(el);
    const sizeL = h("label", {}, bar, "Chunk size "); const size = h("input", { type: "range", min: 10, max: Math.max(20, Math.min(200, words.length)), value: cfg.size || 40 }, sizeL); const sizeV = h("b", {}, sizeL);
    const ovL = h("label", {}, bar, "Overlap "); const ov = h("input", { type: "range", min: 0, max: 30, value: cfg.overlap || 8 }, ovL); const ovV = h("b", {}, ovL);
    const cols = ["var(--c1)", "var(--c2)", "var(--c3)", "var(--c4)", "var(--c6)", "var(--c7)"];
    function render() {
      const S = +size.value; let O = Math.min(+ov.value, S - 1); sizeV.textContent = S + " words"; ovV.textContent = O + " words";
      const chunks = []; for (let s = 0; s < words.length; s += S - O) { chunks.push([s, Math.min(words.length, s + S)]); if (s + S >= words.length) break; }
      const owner = words.map(() => []);
      chunks.forEach((c, ci) => { for (let k = c[0]; k < c[1]; k++) owner[k].push(ci); });
      body.innerHTML = "";
      words.forEach((w, k) => {
        const sp = h("span", {}, body, w + " ");
        const o = owner[k];
        const col = cols[o[0] % cols.length];
        if (o.length > 1) { sp.style.background = "color-mix(in srgb, " + cols[o[1] % cols.length] + " 30%, var(--panel))"; sp.style.boxShadow = "inset 0 -3px 0 " + col; }
        else sp.style.background = "color-mix(in srgb, " + col + " 16%, var(--panel))";
        if (chunks.some((c) => c[0] === k)) { const m = document.createElement("sup"); m.textContent = "#" + (o[o.length - 1] + 1); m.style.cssText = "font-family:var(--font-ui);font-size:.65em;color:var(--muted);margin-right:2px"; sp.prepend(m); }
      });
      const ovWords = owner.filter((o) => o.length > 1).length;
      setCaption(cap, "<strong>" + chunks.length + " chunks.</strong> " + ovWords + " words appear in two chunks. " + (cfg.note || "Try a tiny chunk size: facts like who acquired whom get split away from their subject."));
    }
    size.addEventListener("input", render); ov.addEventListener("input", render); render();
  };

  /* ================= embedding-space ================= */
  registry["embedding-space"] = function (el, cfg) {
    const W = 640, H = cfg.height || 380;
    const { stage } = frame(el, cfg);
    const svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, role: "img", "aria-label": "2D embedding space" }, stage);
    const pts = cfg.points.map((p) => ({ ...p, X: (p.x / 100) * W, Y: (p.y / 100) * H }));
    const gl = svgEl("g", {}, svg);
    pts.forEach((p) => {
      p._c = svgEl("circle", { cx: p.X, cy: p.Y, r: 7, style: "fill:color-mix(in srgb," + groupColor(p.group || 1) + " 35%, var(--panel));stroke:" + groupColor(p.group || 1) + ";stroke-width:2" }, svg);
      const t = svgEl("text", { x: p.X + 10, y: p.Y + 4, class: "d-text small" }, svg); t.textContent = p.label;
    });
    const q = { X: ((cfg.query ? cfg.query.x : 50) / 100) * W, Y: ((cfg.query ? cfg.query.y : 50) / 100) * H };
    const qg = svgEl("g", { tabindex: 0, style: "cursor:grab" }, svg);
    svgEl("rect", { x: -9, y: -9, width: 18, height: 18, transform: "rotate(45)", style: "fill:var(--edge);stroke:var(--ink);stroke-width:1.5" }, qg);
    const qt = svgEl("text", { x: 14, y: -12, class: "d-text bold" }, qg); qt.textContent = (cfg.query && cfg.query.label) || "query";
    const cap = h("div", { class: "viz-caption", "aria-live": "polite" }, el);
    const bar = controls(el);
    const kL = h("label", {}, bar, "Top k "); const k = h("input", { type: "range", min: 1, max: Math.min(8, pts.length), value: cfg.k || 3 }, kL); const kV = h("b", {}, kL);
    h("span", { class: "grow" }, bar); h("span", { class: "stepno" }, bar, "Drag the diamond to ask a different question");
    function render() {
      qg.setAttribute("transform", "translate(" + q.X + "," + q.Y + ")");
      gl.innerHTML = "";
      const K = +k.value; kV.textContent = K;
      const ranked = pts.map((p) => ({ p, d: Math.hypot(p.X - q.X, p.Y - q.Y) })).sort((a, b) => a.d - b.d);
      pts.forEach((p) => p._c.setAttribute("r", 7));
      ranked.slice(0, K).forEach((r) => { svgEl("line", { x1: q.X, y1: q.Y, x2: r.p.X, y2: r.p.Y, class: "d-line hot" }, gl); r.p._c.setAttribute("r", 10); });
      const maxD = Math.hypot(W, H);
      setCaption(cap, "Retrieved: " + ranked.slice(0, K).map((r) => '<span class="viz-chip node">' + r.p.label + " · " + fmt(1 - r.d / maxD, 2) + "</span>").join(" ") + (cfg.note ? "<br>" + cfg.note : ""));
    }
    let dragging = false;
    const pt = (ev) => { const r = svg.getBoundingClientRect(); return { x: ((ev.clientX - r.left) / r.width) * W, y: ((ev.clientY - r.top) / r.height) * H }; };
    qg.addEventListener("pointerdown", (e) => { dragging = true; qg.setPointerCapture(e.pointerId); });
    qg.addEventListener("pointermove", (e) => { if (!dragging) return; const p = pt(e); q.X = Math.max(10, Math.min(W - 10, p.x)); q.Y = Math.max(10, Math.min(H - 10, p.y)); render(); });
    qg.addEventListener("pointerup", () => (dragging = false));
    qg.addEventListener("keydown", (e) => { const d = 12; if (e.key === "ArrowLeft") q.X -= d; else if (e.key === "ArrowRight") q.X += d; else if (e.key === "ArrowUp") q.Y -= d; else if (e.key === "ArrowDown") q.Y += d; else return; e.preventDefault(); render(); });
    k.addEventListener("input", render);
    render();
  };

  /* ================= pagerank ================= */
  function pagerank(nodes, edges, seeds, alpha, iters, directed) {
    const ids = nodes.map((n) => n.id), idx = {}; ids.forEach((id, i) => (idx[id] = i));
    const N = ids.length, out = ids.map(() => []);
    edges.forEach((e) => { const w = e.weight || 1; out[idx[e.source]].push([idx[e.target], w]); if (!directed) out[idx[e.target]].push([idx[e.source], w]); });
    const seedIds = [...seeds];
    const p = new Array(N).fill(0);
    if (seedIds.length) seedIds.forEach((s) => (p[idx[s]] = 1 / seedIds.length)); else p.fill(1 / N);
    let r = p.slice(); const history = [r.slice()];
    for (let t = 0; t < iters; t++) {
      const nr = p.map((v) => (1 - alpha) * v);
      let dangling = 0;
      for (let i = 0; i < N; i++) {
        const tot = out[i].reduce((s, x) => s + x[1], 0);
        if (!tot) { dangling += r[i]; continue; }
        out[i].forEach(([j, w]) => (nr[j] += alpha * r[i] * (w / tot)));
      }
      for (let i = 0; i < N; i++) nr[i] += alpha * dangling * p[i];
      r = nr; history.push(r.slice());
    }
    return { ids, history };
  }
  registry["pagerank"] = function (el, cfg) {
    const W = cfg.width || 720, H = cfg.height || 380;
    const { stage } = frame(el, cfg);
    const svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, role: "img", "aria-label": "PageRank" }, stage);
    const seeds = new Set(cfg.seeds || []);
    const conf = Object.assign({}, cfg, { focusable: true, onNodeClick: (n) => { seeds.has(n.id) ? seeds.delete(n.id) : seeds.add(n.id); run(); } });
    const G = drawGraph(svg, conf, W, H);
    const cap = h("div", { class: "viz-caption", "aria-live": "polite" }, el);
    const bar = controls(el);
    const aL = h("label", {}, bar, "Damping α "); const a = h("input", { type: "range", min: 0.05, max: 0.95, step: 0.05, value: cfg.alpha || 0.85 }, aL); const aV = h("b", {}, aL);
    const itL = h("label", {}, bar, "Iteration "); const it = h("input", { type: "range", min: 0, max: 30, value: 30 }, itL); const itV = h("b", {}, itL);
    const anim = button(bar, "Animate", "primary");
    h("span", { class: "grow" }, bar); h("span", { class: "stepno" }, bar, "Click nodes to toggle seeds");
    let result;
    function run() { aV.textContent = (+a.value).toFixed(2); result = pagerank(G.nodes, G.edges, seeds, +a.value, 30, cfg.directed); draw(); }
    function draw() {
      const t = +it.value; itV.textContent = t;
      const r = result.history[t]; const mx = Math.max(...r);
      G.nodes.forEach((n, i) => {
        const v = r[result.ids.indexOf(n.id)];
        n._r = 8 + 20 * Math.sqrt(v / (mx || 1));
        n._c.setAttribute("r", n._r);
        n._c.style.fill = "color-mix(in srgb, " + (seeds.has(n.id) ? "var(--edge)" : n._col) + " " + Math.round(20 + 60 * (v / (mx || 1))) + "%, var(--panel))";
        n._c.style.stroke = seeds.has(n.id) ? "var(--edge)" : n._col;
        n._s.textContent = fmt(v, 2); n._s.setAttribute("dy", -n._r - 5);
      });
      G.place();
      const top = result.ids.map((id, i) => [id, r[i]]).sort((x, y) => y[1] - x[1]).slice(0, 4);
      const label = (id) => (G.byId[id].label || id);
      setCaption(cap, (seeds.size ? "Personalized to " + [...seeds].map((s) => '<span class="viz-chip edge">' + label(s) + "</span>").join(" ") : "Uniform teleport (classic PageRank)") + ". Highest mass: " + top.map((x) => '<span class="viz-chip node">' + label(x[0]) + " " + fmt(x[1], 3) + "</span>").join(" "));
    }
    a.addEventListener("input", run); it.addEventListener("input", draw);
    anim.addEventListener("click", () => { let t = 0; it.value = 0; draw(); const tm = setInterval(() => { t++; it.value = t; draw(); if (t >= 30) clearInterval(tm); }, reduceMotion ? 1 : 120); });
    run();
  };

  /* ================= louvain ================= */
  function louvainTrace(nodes, edges, seed) {
    const ids = nodes.map((n) => n.id); const adj = {}; ids.forEach((i) => (adj[i] = {}));
    let m2 = 0;
    edges.forEach((e) => { const w = e.weight || 1; adj[e.source][e.target] = (adj[e.source][e.target] || 0) + w; adj[e.target][e.source] = (adj[e.target][e.source] || 0) + w; m2 += 2 * w; });
    const deg = {}; ids.forEach((i) => (deg[i] = Object.values(adj[i]).reduce((a, b) => a + b, 0)));
    const comm = {}; ids.forEach((i, k) => (comm[i] = k));
    const Q = () => { let q = 0; ids.forEach((i) => ids.forEach((j) => { if (comm[i] !== comm[j]) return; q += (adj[i][j] || 0) - (deg[i] * deg[j]) / m2; })); return q / m2; };
    const trace = [{ comm: { ...comm }, q: Q(), moved: null }];
    const rnd = mulberry(seed || 3); const order = ids.slice().sort(() => rnd() - 0.5);
    let improved = true, pass = 0;
    while (improved && pass < 10) {
      improved = false; pass++;
      order.forEach((i) => {
        const tot = {}; ids.forEach((j) => { tot[comm[j]] = (tot[comm[j]] || 0) + deg[j]; });
        const links = {}; Object.entries(adj[i]).forEach(([j, w]) => { if (j !== i) links[comm[j]] = (links[comm[j]] || 0) + w; });
        const own = comm[i]; const totOwn = tot[own] - deg[i];
        const gain = (c) => (links[c] || 0) - (c === own ? totOwn : tot[c]) * deg[i] / m2;
        let best = own, bestGain = gain(own);
        Object.keys(links).forEach((c) => { c = +c; const g = gain(c); if (g > bestGain + 1e-12) { best = c; bestGain = g; } });
        if (best !== own) { comm[i] = best; improved = true; trace.push({ comm: { ...comm }, q: Q(), moved: i, to: best, pass }); }
      });
    }
    return trace;
  }
  registry["louvain"] = function (el, cfg) {
    const W = cfg.width || 720, H = cfg.height || 380;
    const { stage } = frame(el, cfg);
    const svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, role: "img", "aria-label": "Louvain community detection" }, stage);
    const G = drawGraph(svg, Object.assign({}, cfg, { edgeLabels: false }), W, H);
    const cap = h("div", { class: "viz-caption", "aria-live": "polite" }, el);
    const trace = louvainTrace(G.nodes, G.edges, cfg.seed);
    // Color the final communities distinctly; communities that later dissolve stay neutral.
    const palette = {}; let nextCol = 1;
    G.nodes.forEach((n) => { const c = trace[trace.length - 1].comm[n.id]; if (!(c in palette)) palette[c] = nextCol++; });
    function render(i) {
      const s = trace[i];
      const labels = {};
      G.nodes.forEach((n) => {
        const c = s.comm[n.id];
        const col = c in palette ? groupColor(palette[c]) : "var(--muted)";
        n._col = col;
        n._c.style.fill = "color-mix(in srgb, " + col + " 45%, var(--panel))"; n._c.style.stroke = col;
        n._g.classList.toggle("active", s.moved === n.id);
        labels[c] = (labels[c] || 0) + 1;
      });
      G.edges.forEach((e) => { const same = s.comm[e.source] === s.comm[e.target]; const ec = s.comm[e.source] in palette ? groupColor(palette[s.comm[e.source]]) : "var(--muted)"; e._el.style.stroke = same ? "color-mix(in srgb, " + ec + " 70%, var(--rule))" : ""; e._el.style.strokeDasharray = same ? "" : "4 4"; });
      const k = Object.keys(labels).length;
      const mv = s.moved != null ? "Pass " + s.pass + ": <strong>" + (G.byId[s.moved].label || s.moved) + "</strong> joins a neighbor's community because it raises modularity. " : "Start: every node is its own community. ";
      setCaption(cap, mv + "Communities: <strong>" + k + "</strong>. Modularity Q = <strong>" + fmt(s.q, 3) + "</strong>." + (i === trace.length - 1 ? " No single move improves Q any more, so phase 1 ends here; Louvain would now collapse each community into a super-node and repeat." : ""));
    }
    player(el, trace.length, render, { interval: cfg.interval || 900 });
  };

  /* ================= text-to-graph ================= */
  registry["text-to-graph"] = function (el, cfg) {
    const { stage } = frame(el, cfg);
    stage.style.display = "grid"; stage.style.gridTemplateColumns = "minmax(0,1fr)";
    const text = h("div", { class: "viz-text" }, stage);
    const W = 640, H = cfg.height || 300;
    const svgWrap = h("div", {}, stage); svgWrap.style.borderTop = "1px solid var(--rule)";
    const svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, role: "img", "aria-label": "Extracted graph" }, svgWrap);
    const ents = cfg.entities || [], rels = cfg.relations || [];
    const G = drawGraph(svg, { nodes: ents.map((e) => ({ id: e.name, label: e.name, group: e.group || e.type, x: e.x, y: e.y })), edges: rels.map((r) => ({ source: r.source, target: r.target, label: r.label })), directed: true, layout: cfg.layout }, W, H);
    const cap = h("div", { class: "viz-caption", "aria-live": "polite" }, el);
    // Build highlighted text: mark mention spans (first occurrence of each mention string)
    let html = escapeHtml(cfg.text);
    const mentions = [];
    ents.forEach((e, ei) => (e.mentions || [e.name]).forEach((m) => mentions.push({ m, ei })));
    mentions.sort((a, b) => b.m.length - a.m.length);
    const tokens = [];
    mentions.forEach(({ m, ei }) => {
      const esc = escapeHtml(m); const re = new RegExp(esc.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "g");
      html = html.replace(re, (x) => { tokens.push('<mark data-e="' + ei + '">' + x + "</mark>"); return " " + (tokens.length - 1) + ""; });
    });
    html = html.replace(/ (\d+)/g, (_, i) => tokens[+i]);
    text.innerHTML = html;
    text.querySelectorAll("mark").forEach((mk) => { mk.style.background = "transparent"; mk.style.color = "inherit"; mk.style.borderRadius = "3px"; mk.style.padding = "0 2px"; mk.style.transition = "background .3s"; });
    const steps = [{ caption: cfg.intro || "The extractor reads the chunk. Step through to see each entity, then each relationship, get pulled out." }];
    ents.forEach((e, i) => steps.push({ e: i, caption: 'Entity <span class="viz-chip node">' + e.name + "</span> type <strong>" + (e.type || "") + "</strong>" + (e.description ? ": " + e.description : "") }));
    rels.forEach((r, i) => steps.push({ r: i, caption: 'Relationship <span class="viz-chip edge">' + r.source + " → " + r.label + " → " + r.target + "</span>" + (r.description ? " " + r.description : "") }));
    function render(i) {
      const shownE = new Set(), shownR = new Set();
      for (let k = 0; k <= i; k++) { if (steps[k].e != null) shownE.add(steps[k].e); if (steps[k].r != null) shownR.add(steps[k].r); }
      text.querySelectorAll("mark").forEach((mk) => { const ei = +mk.dataset.e; mk.style.background = shownE.has(ei) ? "color-mix(in srgb, " + groupColor(ents[ei].group || ents[ei].type) + " 30%, var(--panel))" : "transparent"; mk.style.outline = steps[i].e === ei ? "2px solid var(--edge)" : "none"; });
      G.nodes.forEach((n, k) => { n._g.style.opacity = shownE.has(k) ? 1 : 0; n._g.classList.toggle("active", steps[i].e === k); });
      G.edges.forEach((e, k) => { const on = shownR.has(k); e._el.style.opacity = on ? 1 : 0; if (e._label) e._label.style.opacity = on ? 1 : 0; e._el.classList.toggle("active", steps[i].r === k); });
      setCaption(cap, steps[i].caption);
    }
    player(el, steps.length, render, { interval: cfg.interval || 1500 });
  };
  function escapeHtml(s) { return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]); }

  /* ================= map-reduce (global search) ================= */
  registry["map-reduce"] = function (el, cfg) {
    const { stage } = frame(el, cfg);
    const threshold = cfg.threshold == null ? 20 : cfg.threshold;
    const q = h("div", { class: "viz-text" }, stage); q.innerHTML = "<strong>Question:</strong> " + escapeHtml(cfg.question || "");
    const grid = h("div", { class: "viz-grid" }, stage); grid.style.gridTemplateColumns = "repeat(auto-fit, minmax(190px, 1fr))";
    const cards = (cfg.communities || []).map((c) => {
      const d = h("div", {}, grid); d.style.cssText = "border:1px solid var(--rule);border-radius:8px;padding:10px;background:var(--paper);transition:opacity .3s, border-color .3s";
      h("div", { class: "viz-title" }, d, c.title).style.fontSize = ".88rem";
      const sc = h("div", { class: "viz-sub" }, d, "score: ?");
      const barBg = h("div", {}, d); barBg.style.cssText = "height:8px;background:var(--paper-2);border-radius:4px;margin:6px 0";
      const barFg = h("div", { class: "viz-bar" }, barBg); barFg.style.width = "0%";
      const ans = h("div", {}, d, ""); ans.style.cssText = "font-family:var(--font-prose);font-size:.86rem;line-height:1.4;color:var(--ink-2)";
      return { c, d, sc, barFg, ans };
    });
    const out = h("div", { class: "viz-text" }, stage); out.style.borderTop = "1px solid var(--rule)";
    const cap = h("div", { class: "viz-caption", "aria-live": "polite" }, el);
    const steps = ["shuffle", "map", "filter", "reduce"];
    function render(i) {
      const st = steps[i];
      cards.forEach((k) => {
        const mapped = i >= 1, filtered = i >= 2 && k.c.score < threshold;
        k.sc.textContent = mapped ? "helpfulness: " + k.c.score + " / 100" : "helpfulness: ?";
        k.barFg.style.width = mapped ? k.c.score + "%" : "0%";
        k.barFg.style.background = filtered ? "var(--bad)" : "var(--node)";
        k.ans.textContent = mapped ? k.c.answer || "" : "";
        k.d.style.opacity = filtered ? 0.35 : 1;
      });
      out.innerHTML = st === "reduce" ? "<strong>Reduce:</strong> " + escapeHtml(cfg.final || "") : "";
      setCaption(cap, ({
        shuffle: "Community reports (at one level of the hierarchy) are shuffled and packed into context-sized batches.",
        map: "Map: each batch is sent to the LLM in parallel. It writes a partial answer and scores how helpful that batch is for the question.",
        filter: "Filter: partial answers scoring below " + threshold + " are dropped, then the rest are sorted by score.",
        reduce: "Reduce: the surviving partial answers are packed into one final prompt that synthesizes the global answer."
      })[st]);
    }
    player(el, steps.length, render, { interval: 2400 });
  };

  /* ================= rrf ================= */
  registry["rrf"] = function (el, cfg) {
    const { stage } = frame(el, cfg);
    const lists = cfg.lists || {};
    const grid = h("div", { class: "viz-grid" }, stage);
    const names = Object.keys(lists);
    grid.style.gridTemplateColumns = "repeat(auto-fit, minmax(140px, 1fr))";
    const bar = controls(el);
    const kL = h("label", {}, bar, "k "); const k = h("input", { type: "range", min: 0, max: 100, value: cfg.k == null ? 60 : cfg.k }, kL); const kV = h("b", {}, kL);
    const cap = h("div", { class: "viz-caption", "aria-live": "polite" }, el);
    function render() {
      const K = +k.value; kV.textContent = K;
      grid.innerHTML = "";
      const scores = {};
      names.forEach((nm) => {
        const col = h("div", {}, grid); h("div", { class: "viz-title" }, col, nm).style.fontSize = ".85rem";
        lists[nm].forEach((item, r) => { scores[item] = (scores[item] || 0) + 1 / (K + r + 1); const row = h("div", { class: "viz-sub" }, col); row.innerHTML = (r + 1) + ". " + escapeHtml(item); });
      });
      const fused = Object.entries(scores).sort((a, b) => b[1] - a[1]);
      const col = h("div", {}, grid); h("div", { class: "viz-title" }, col, "Fused (RRF)").style.fontSize = ".85rem";
      const mx = fused[0] ? fused[0][1] : 1;
      fused.forEach(([item, s], r) => { const row = h("div", {}, col); row.style.fontSize = ".82rem"; row.innerHTML = (r + 1) + ". " + escapeHtml(item) + ' <span class="viz-sub">' + fmt(s, 4) + "</span>"; const b = h("div", { class: "viz-bar" }, row); b.style.width = (100 * s / mx) + "%"; b.style.height = "4px"; });
      setCaption(cap, "score(d) = Σ 1 / (k + rank). With k = " + K + ", " + (K < 10 ? "top positions dominate: whichever list ranks an item first nearly decides." : "ranks are flattened, so items that appear in several lists rise above one-list winners."));
    }
    k.addEventListener("input", render); render();
  };

  /* ================= token-budget ================= */
  registry["token-budget"] = function (el, cfg) {
    const { stage } = frame(el, cfg);
    const total = cfg.total || 12000; const parts = (cfg.parts || []).map((p) => ({ ...p }));
    const barWrap = h("div", {}, stage); barWrap.style.cssText = "display:flex;height:42px;margin:16px 14px;border-radius:6px;overflow:hidden;border:1px solid var(--rule)";
    const bar = controls(el);
    const cap = h("div", { class: "viz-caption", "aria-live": "polite" }, el);
    const sliders = parts.map((p, i) => { const L = h("label", {}, bar, p.label + " "); const s = h("input", { type: "range", min: 0, max: 100, value: Math.round(p.share * 100) }, L); s.addEventListener("input", render); return s; });
    function render() {
      const raw = sliders.map((s) => +s.value); const sum = raw.reduce((a, b) => a + b, 0) || 1;
      barWrap.innerHTML = "";
      const rows = parts.map((p, i) => { const share = raw[i] / sum; const seg = h("div", {}, barWrap); seg.style.cssText = "width:" + share * 100 + "%;background:color-mix(in srgb," + groupColor(i + 1) + " 55%, var(--panel));display:flex;align-items:center;font-size:.75rem;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;padding:0 4px;min-width:0;transition:width .2s"; seg.title = p.label; seg.textContent = share * 100 >= p.label.length * 1.1 ? p.label : ""; return p.label + ": <strong>" + Math.round(share * total).toLocaleString() + "</strong> tokens"; });
      setCaption(cap, rows.join(" &nbsp; ") + (cfg.note ? "<br>" + cfg.note : ""));
    }
    render();
  };

  /* ---------- boot ---------- */
  function mount(el) {
    if (el.dataset.mounted) return;
    const type = el.dataset.viz; const fn = registry[type];
    const script = el.querySelector('script[type="application/json"]');
    let cfg = {};
    try { cfg = script ? JSON.parse(script.textContent) : {}; }
    catch (e) { el.textContent = "Visualization config error: " + e.message; console.error(e, el); return; }
    if (!fn) { el.textContent = "Unknown visualization: " + type; return; }
    el.dataset.mounted = "1";
    try { fn(el, cfg, api); } catch (e) { console.error("viz " + type + " failed", e); el.textContent = "Visualization failed to load: " + e.message; }
  }
  const api = { svgEl, h, frame, controls, button, player, drawGraph, layoutGraph, groupColor, legend, pagerank, fmt, escapeHtml };
  window.GRFSViz = { register: (name, fn) => { registry[name] = fn; document.querySelectorAll('.viz[data-viz="' + name + '"]').forEach(mount); }, api, mountAll: () => document.querySelectorAll(".viz[data-viz]").forEach(mount) };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", window.GRFSViz.mountAll); else window.GRFSViz.mountAll();
})();
