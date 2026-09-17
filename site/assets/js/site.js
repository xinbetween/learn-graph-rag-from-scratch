/* Site shell: top bar, search, chapter rail, on-page contents, progress, quizzes, code blocks, pager, footer.
   Chapter pages only author <main class="chapter"> content; this script wraps it. */
(function () {
  "use strict";
  const C = window.CURRICULUM;
  const body = document.body;
  const root = body.dataset.root || ".";
  const slug = body.dataset.slug || "";
  const STORE = "grfs-progress-v1";

  /* ---------- storage (never trusted to exist) ---------- */
  function loadProgress() {
    try { return JSON.parse(localStorage.getItem(STORE) || "{}"); } catch (e) { return {}; }
  }
  function saveProgress(p) {
    try { localStorage.setItem(STORE, JSON.stringify(p)); } catch (e) { /* private mode */ }
  }
  const progress = loadProgress();

  /* ---------- theme ---------- */
  function currentTheme() {
    const t = document.documentElement.dataset.theme;
    if (t) return t;
    return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  function setTheme(t) {
    document.documentElement.dataset.theme = t;
    try { localStorage.setItem("grfs-theme", t); } catch (e) { }
    document.dispatchEvent(new CustomEvent("themechange"));
  }

  /* ---------- curriculum helpers ---------- */
  const flat = [];
  C.parts.forEach((part, pi) => part.chapters.forEach((ch) => flat.push(Object.assign({ part, partIndex: pi }, ch))));
  const learnable = flat.filter((c) => c.part.id !== "ap");
  function chapterLabel(ch) {
    if (ch.part.id === "ap") return "Appendix";
    if (ch.slug.startsWith("c")) return "Capstone " + ch.slug.slice(1, 2);
    return "Chapter " + parseInt(ch.slug.slice(0, 2), 10);
  }
  function chapterId(ch) {
    if (ch.part.id === "ap") return "";
    if (ch.slug.startsWith("c")) return "C" + ch.slug.slice(1, 2);
    return ch.slug.slice(0, 2);
  }
  function partLabel(part) { return part.id === "ap" ? "Appendices" : part.id === "p7" ? "Capstones" : "Part " + part.id.slice(1); }
  function partHeading(part) { return part.id === "ap" || part.id === "p7" ? part.title : "Part " + part.id.slice(1) + " · " + part.title; }
  function href(s) { return root + "/chapters/" + s + ".html"; }
  window.GRFS = { flat, learnable, chapterLabel, chapterId, partLabel, partHeading, href, progress, root };

  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const ICON = {
    mark: '<svg viewBox="0 0 16 16" aria-hidden="true"><line x1="3.5" y1="4" x2="12.5" y2="3.5" stroke="var(--accent)" stroke-width="1.4"/><line x1="3.5" y1="4" x2="6" y2="12.5" stroke="var(--accent)" stroke-width="1.4"/><line x1="6" y1="12.5" x2="12.5" y2="3.5" stroke="var(--accent)" stroke-width="1.4"/><circle cx="3.5" cy="4" r="2.4" fill="var(--accent)"/><circle cx="12.5" cy="3.5" r="2" fill="var(--accent)"/><circle cx="6" cy="12.5" r="2.4" fill="var(--accent)"/></svg>',
    search: '<svg width="13" height="13" viewBox="0 0 16 16" aria-hidden="true"><circle cx="7" cy="7" r="5" fill="none" stroke="currentColor" stroke-width="1.6"/><line x1="10.8" y1="10.8" x2="14.5" y2="14.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>',
    theme: '<svg width="15" height="15" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6.2" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M8 1.8a6.2 6.2 0 0 1 0 12.4z" fill="currentColor"/></svg>',
    menu: '<svg width="15" height="15" viewBox="0 0 16 16" aria-hidden="true"><path d="M2 4h12M2 8h12M2 12h12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
    check: '<svg width="13" height="13" viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8.5l3.2 3L13 4.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'
  };

  function doneCount() { return learnable.filter((c) => progress[c.slug]).length; }

  /* ---------- top bar ---------- */
  function buildTopbar() {
    const bar = document.createElement("header");
    bar.className = "topbar";
    const mac = /Mac|iPhone|iPad/.test(navigator.platform);
    const cur = (s) => (slug === s ? ' aria-current="page"' : "");
    bar.innerHTML =
      '<button class="iconbtn menubtn" aria-label="Open chapter list" aria-expanded="false">' + ICON.menu + "</button>" +
      '<a class="brand" href="' + root + '/index.html">' + ICON.mark + "<span>Graph RAG</span></a>" +
      '<nav class="topnav" aria-label="Site">' +
        '<a href="' + root + '/index.html#curriculum">Curriculum</a>' +
        '<a class="hide-sm" href="' + href("c1-minigraphrag") + '"' + (slug.startsWith("c") ? ' aria-current="page"' : "") + ">Capstones</a>" +
        '<a class="hide-sm" href="' + href("33-research-map") + '"' + cur("33-research-map") + ">Research map</a>" +
        '<a href="' + href("glossary") + '"' + cur("glossary") + ">Glossary</a>" +
        '<a href="' + href("library") + '"' + cur("library") + ">Library</a>" +
        '<button class="searchbtn" aria-label="Search chapters">' + ICON.search + '<span class="lbl">Search</span><span class="kb">' + (mac ? "⌘K" : "Ctrl K") + "</span></button>" +
        '<button class="iconbtn theme-btn" aria-label="Toggle dark mode">' + ICON.theme + "</button>" +
      "</nav>";
    bar.querySelector(".theme-btn").addEventListener("click", () => setTheme(currentTheme() === "dark" ? "light" : "dark"));
    bar.querySelector(".menubtn").addEventListener("click", () => toggleNav());
    bar.querySelector(".searchbtn").addEventListener("click", () => openSearch());
    return bar;
  }
  function toggleNav(force) {
    const open = force != null ? force : !body.classList.contains("nav-open");
    body.classList.toggle("nav-open", open);
    const b = document.querySelector(".menubtn");
    if (b) b.setAttribute("aria-expanded", String(open));
    const scrim = document.querySelector(".side-scrim");
    if (scrim) scrim.hidden = !open;
  }

  /* ---------- search dialog ---------- */
  let dlg = null, hits = [], sel = 0;
  function buildSearch() {
    dlg = document.createElement("div");
    dlg.className = "search-dlg";
    dlg.hidden = true;
    dlg.setAttribute("role", "dialog");
    dlg.setAttribute("aria-modal", "true");
    dlg.setAttribute("aria-label", "Search the course");
    dlg.innerHTML =
      '<div class="search-backdrop"></div><div class="search-panel">' +
      '<label class="search-in">' + ICON.search + '<input type="search" placeholder="Search chapters, capstones and topics" aria-label="Search" autocomplete="off"><button class="search-esc" type="button">esc</button></label>' +
      '<div class="search-results" role="listbox"></div>' +
      '<div class="search-foot"><span><kbd>↑</kbd><kbd>↓</kbd>navigate</span><span><kbd>↵</kbd>open</span><span><kbd>esc</kbd>close</span><span class="count"></span></div></div>';
    body.appendChild(dlg);
    const input = dlg.querySelector("input");
    dlg.querySelector(".search-backdrop").addEventListener("click", closeSearch);
    dlg.querySelector(".search-esc").addEventListener("click", closeSearch);
    input.addEventListener("input", () => renderSearch(input.value));
    input.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown") { e.preventDefault(); sel = Math.min(hits.length - 1, sel + 1); paintSel(); }
      else if (e.key === "ArrowUp") { e.preventDefault(); sel = Math.max(0, sel - 1); paintSel(); }
      else if (e.key === "Enter" && hits[sel]) { location.href = href(hits[sel].slug); }
      else if (e.key === "Escape") closeSearch();
    });
  }
  function openSearch() {
    if (!dlg) buildSearch();
    dlg.hidden = false;
    body.classList.add("search-open");
    const input = dlg.querySelector("input");
    input.value = "";
    renderSearch("");
    setTimeout(() => input.focus(), 0);
  }
  function closeSearch() { if (!dlg) return; dlg.hidden = true; body.classList.remove("search-open"); }
  function renderSearch(q) {
    const res = dlg.querySelector(".search-results");
    const terms = q.trim().toLowerCase().split(/\s+/).filter(Boolean);
    const scored = flat.map((c) => {
      const t = c.title.toLowerCase(), s = c.summary.toLowerCase(), p = c.part.title.toLowerCase(), id = chapterId(c).toLowerCase();
      let score = 0;
      for (const w of terms) {
        if (id === w) score += 10;
        else if (t.includes(w)) score += 4; else if (s.includes(w)) score += 2; else if (p.includes(w)) score += 1; else return null;
      }
      return { c, score };
    }).filter(Boolean);
    if (terms.length) scored.sort((a, b) => b.score - a.score);
    hits = scored.map((x) => x.c);
    sel = 0;
    const mark = (text) => {
      let out = esc(text);
      terms.forEach((w) => { out = out.replace(new RegExp("(" + esc(w).replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "ig"), "<mark>$1</mark>"); });
      return out;
    };
    if (!hits.length) {
      res.innerHTML = '<div class="empty">No chapter matches <b>' + esc(q) + "</b>. Try a method name such as PageRank, Leiden or Cypher.</div>";
    } else {
      let html = "", lastPart = null;
      hits.forEach((c, i) => {
        if (!terms.length && c.part !== lastPart) { html += '<div class="grp">' + esc(partHeading(c.part)) + "</div>"; lastPart = c.part; }
        html += '<a class="hit" role="option" href="' + href(c.slug) + '"><span class="hrow"><span class="ht">' + mark(c.title) + '</span><span class="hk">' + esc(chapterId(c) || "appendix") + '</span></span><span class="hs">' + mark(c.summary) + "</span></a>";
      });
      res.innerHTML = html;
    }
    dlg.querySelector(".count").textContent = hits.length + (hits.length === 1 ? " result" : " results");
    paintSel();
  }
  function paintSel() {
    dlg.querySelectorAll(".hit").forEach((h, i) => {
      h.setAttribute("aria-selected", String(i === sel));
      if (i === sel) h.scrollIntoView({ block: "nearest" });
    });
  }
  document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); dlg && !dlg.hidden ? closeSearch() : openSearch(); return; }
    if (e.key === "/" && !e.target.closest("input, textarea, select, [contenteditable]")) { e.preventDefault(); openSearch(); return; }
    if (e.key === "Escape") { closeSearch(); toggleNav(false); }
  });

  /* ---------- chapter rail ---------- */
  function buildSidebar() {
    const nav = document.createElement("nav");
    nav.className = "sidebar";
    nav.setAttribute("aria-label", "Course chapters");
    nav.innerHTML = '<div class="sidenav-list"></div>';
    const list = nav.querySelector(".sidenav-list");
    C.parts.forEach((part) => {
      const wrap = document.createElement("div");
      wrap.className = "nav-part";
      const h = document.createElement("h5");
      h.textContent = partHeading(part);
      wrap.appendChild(h);
      const ol = document.createElement("ol");
      part.chapters.forEach((ch0) => {
        const ch = flat.find((f) => f.slug === ch0.slug);
        const li = document.createElement("li");
        const a = document.createElement("a");
        a.href = href(ch.slug);
        a.dataset.search = (ch.title + " " + ch.summary + " " + chapterId(ch)).toLowerCase();
        if (progress[ch.slug]) a.classList.add("done");
        if (ch.slug === slug) a.setAttribute("aria-current", "page");
        a.innerHTML = '<span class="cid">' + esc(chapterId(ch)) + '</span><span class="ct"></span><span class="tick" aria-hidden="true">✓</span>';
        a.querySelector(".ct").textContent = ch.title;
        li.appendChild(a);
        ol.appendChild(li);
      });
      wrap.appendChild(ol);
      list.appendChild(wrap);
    });
    nav.querySelectorAll("a").forEach((a) => a.addEventListener("click", () => toggleNav(false)));
    return nav;
  }

  function slugify(t) { return t.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, ""); }

  function buildToc(main) {
    const hs = [...main.querySelectorAll(":scope > h2")];
    if (hs.length < 2) return null;
    const aside = document.createElement("aside");
    aside.className = "toc";
    aside.innerHTML = "<h2>In this chapter</h2><ol></ol>";
    const ol = aside.querySelector("ol");
    const links = [];
    hs.forEach((h) => {
      if (!h.id) h.id = slugify(h.textContent);
      const a = document.createElement("a");
      a.href = "#" + h.id;
      a.textContent = h.textContent;
      const li = document.createElement("li");
      li.appendChild(a);
      ol.appendChild(li);
      links.push([h, a]);
    });
    const onScroll = () => {
      let cur = links[0];
      for (const pair of links) if (pair[0].getBoundingClientRect().top < 120) cur = pair;
      links.forEach((p) => p[1].classList.toggle("active", p === cur));
    };
    addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return aside;
  }

  function decorateHeadings(main) {
    main.querySelectorAll("h2, h3").forEach((h) => {
      if (h.closest(".quiz, .exercise, .project, .objectives, .viz, .keypoints")) return;
      if (!h.id) h.id = slugify(h.textContent);
      const a = document.createElement("a");
      a.className = "anchor";
      a.href = "#" + h.id;
      a.setAttribute("aria-label", "Link to this section");
      a.textContent = "#";
      h.appendChild(a);
    });
  }

  function decorateHeader(main, ch) {
    const head = main.querySelector(".chapter-head");
    if (!head || !ch) return;
    const kicker = document.createElement("div");
    kicker.className = "chapter-kicker";
    const id = chapterId(ch);
    kicker.innerHTML = (id ? '<span class="chap-id">' + esc(id) + "</span>" : "") +
      '<span class="chap-part">' + esc(ch.part.id === "ap" ? "Appendix" : partHeading(ch.part)) + "</span>";
    head.insertBefore(kicker, head.firstChild);
    const meta = document.createElement("div");
    meta.className = "meta-row";
    const bits = [];
    const capstone = ch.slug.startsWith("c");
    if (ch.minutes) bits.push("<span><b>" + (ch.minutes >= 120 ? Math.round(ch.minutes / 60) + " h" : ch.minutes + " min") + "</b> " + (capstone ? "build" : "read") + "</span>");
    const nEx = main.querySelectorAll(".exercise").length, nQ = main.querySelectorAll(".quiz").length, nViz = main.querySelectorAll(".viz").length;
    if (nViz) bits.push("<span><b>" + nViz + "</b> interactive " + (nViz === 1 ? "figure" : "figures") + "</span>");
    if (nEx) bits.push("<span><b>" + nEx + "</b> " + (capstone ? "milestones" : "exercises") + "</span>");
    if (nQ) bits.push("<span><b>" + nQ + "</b> questions</span>");
    const pre = ch.prereqs.map((p) => flat.find((f) => f.slug === p)).filter(Boolean);
    if (pre.length) bits.push("<span>builds on " + pre.map((p) => '<a href="' + href(p.slug) + '" title="' + esc(p.title) + '"><b>' + esc(chapterId(p)) + "</b> " + esc(p.title) + "</a>").join(", ") + "</span>");
    meta.innerHTML = bits.join("");
    if (bits.length) {
      const lede = head.querySelector(".lede");
      const h1 = head.querySelector("h1");
      (lede || h1).after(meta);
    }
    document.title = (head.querySelector("h1") || {}).textContent + " | " + C.title;
  }

  function buildFooter(ch) {
    const foot = document.createElement("footer");
    foot.className = "chapter-foot";
    const idx = flat.indexOf(ch);
    const prev = flat[idx - 1];
    const next = flat[idx + 1];
    let html = '<nav class="pager" aria-label="Chapter pager">';
    if (prev) html += '<a class="prev" href="' + href(prev.slug) + '"><small>← Previous</small>' + esc((chapterId(prev) ? chapterId(prev) + " " : "") + prev.title) + "</a>";
    if (next) html += '<a class="next" href="' + href(next.slug) + '"><small>Next →</small>' + esc((chapterId(next) ? chapterId(next) + " " : "") + next.title) + "</a>";
    html += "</nav>";
    foot.innerHTML = html;
    // A chapter counts as complete once the reader scrolls down to its pager.
    // Requiring a real scroll keeps short viewports and #fragment jumps from marking it on load.
    if (ch.part.id !== "ap" && !progress[ch.slug] && "IntersectionObserver" in window) {
      let scrolled = false;
      addEventListener("scroll", () => { scrolled = true; }, { passive: true, once: true });
      const io = new IntersectionObserver((entries) => {
        if (!scrolled || !entries.some((e) => e.isIntersecting)) return;
        progress[ch.slug] = true;
        saveProgress(progress);
        const link = document.querySelector('.sidebar a[aria-current="page"]');
        if (link) link.classList.add("done");
        io.disconnect();
      });
      io.observe(foot);
    }
    document.addEventListener("keydown", (e) => {
      if (e.target.closest("input, textarea, select, [contenteditable]") || e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "[" && prev) location.href = href(prev.slug);
      if (e.key === "]" && next) location.href = href(next.slug);
    });
    return foot;
  }

  function buildSiteFoot() {
    const f = document.createElement("footer");
    f.className = "sitefoot";
    f.innerHTML = '<div class="wrap"><div class="cols">' +
      '<div><a class="brand" href="' + root + '/index.html">' + ICON.mark + "<span>" + esc(C.title) + '</span></a><p class="note">A self-paced course on graph retrieval-augmented generation, with a runnable reference implementation. The Kestrel Labs corpus used throughout is fictional.</p></div>' +
      '<div><h5>Course</h5><ul><li><a href="' + root + '/index.html#curriculum">Curriculum</a></li><li><a href="' + href("00-welcome") + '">Start here</a></li><li><a href="' + href("14-local-search") + '">Retrieval</a></li><li><a href="' + href("c1-minigraphrag") + '">Capstones</a></li></ul></div>' +
      '<div><h5>Reference</h5><ul><li><a href="' + href("glossary") + '">Glossary</a></li><li><a href="' + href("library") + '">Paper and tool library</a></li><li><a href="' + href("33-research-map") + '">Research map</a></li><li><a href="' + href("28-frameworks-in-practice") + '">Frameworks</a></li></ul></div>' +
      '<div><h5>Credits</h5><ul><li><a href="https://github.com/microsoft/graphrag">Microsoft GraphRAG</a></li><li><a href="https://github.com/DEEP-PolyU/Awesome-GraphRAG">Awesome-GraphRAG</a></li><li><a href="https://github.com/graphrag/awesome-graphrag">graphrag/awesome-graphrag</a></li><li><a href="https://huggingface.co/collections/graphrag/graphrag-papers">GraphRAG papers</a></li></ul></div>' +
      "</div></div>";
    return f;
  }

  /* ---------- quizzes ----------
     <div class="quiz"><p class="q">Question?</p><ol><li>wrong</li><li data-correct>right</li></ol>
       <div class="explain">Why.</div></div> */
  function initQuizzes(scope) {
    const quizzes = [...scope.querySelectorAll(".quiz")];
    quizzes.forEach((quiz, qi) => {
      if (!quiz.querySelector(".qn")) {
        const qn = document.createElement("span");
        qn.className = "qn";
        qn.textContent = "Q" + (qi + 1);
        quiz.insertBefore(qn, quiz.firstChild);
      }
      quiz.querySelectorAll("ol > li").forEach((li) => {
        if (li.querySelector("button")) return;
        const b = document.createElement("button");
        b.type = "button";
        while (li.firstChild) b.appendChild(li.firstChild);
        li.appendChild(b);
        b.addEventListener("click", () => {
          if (quiz.classList.contains("answered")) return;
          quiz.classList.add("answered");
          const right = li.hasAttribute("data-correct");
          quiz.dataset.result = right ? "right" : "wrong";
          quiz.querySelectorAll("ol > li").forEach((o) => {
            o.querySelector("button").disabled = true;
            if (o.hasAttribute("data-correct")) o.classList.add("correct");
          });
          if (!right) li.classList.add("wrong");
          const ex = quiz.querySelector(".explain");
          if (ex && !ex.querySelector(".verdict")) {
            const v = document.createElement("span");
            v.className = "verdict";
            v.textContent = right ? "Correct." : "Not quite.";
            ex.insertBefore(v, ex.firstChild);
          }
          updateScore();
        });
      });
    });
    const scoreEl = scope.querySelector(".quiz-score");
    function updateScore() {
      if (!scoreEl) return;
      const answered = quizzes.filter((q) => q.classList.contains("answered"));
      const right = answered.filter((q) => q.dataset.result === "right").length;
      scoreEl.textContent = answered.length + " of " + quizzes.length + " answered" + (answered.length ? ", " + right + " correct" : "");
    }
    updateScore();
  }

  /* ---------- tables, code blocks, highlighting ---------- */
  function initTables(scope) {
    scope.querySelectorAll("table").forEach((t) => {
      if (t.parentElement.classList.contains("tablewrap")) return;
      const w = document.createElement("div");
      w.className = "tablewrap";
      t.before(w);
      w.appendChild(t);
    });
  }
  function initCode(scope) {
    scope.querySelectorAll("pre").forEach((pre) => {
      const b = document.createElement("button");
      b.className = "copy-btn";
      b.type = "button";
      b.textContent = "copy";
      b.addEventListener("click", async () => {
        try { await navigator.clipboard.writeText(pre.querySelector("code") ? pre.querySelector("code").innerText : pre.innerText); b.textContent = "copied"; }
        catch (e) { b.textContent = "select to copy"; }
        setTimeout(() => (b.textContent = "copy"), 1400);
      });
      const file = pre.getAttribute("data-file");
      if (file && !pre.parentElement.classList.contains("codeblock")) {
        const wrap = document.createElement("div");
        wrap.className = "codeblock";
        const head = document.createElement("div");
        head.className = "cb-head";
        const name = document.createElement("span");
        name.textContent = file;
        head.appendChild(name);
        head.appendChild(b);
        pre.before(wrap);
        wrap.appendChild(head);
        wrap.appendChild(pre);
      } else {
        pre.appendChild(b);
      }
    });
    const needsPrism = scope.querySelector('code[class*="language-"]');
    if (!needsPrism) return;
    const base = "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/";
    const load = (src) => new Promise((res) => { const s = document.createElement("script"); s.src = src; s.onload = () => res(true); s.onerror = () => res(false); document.body.appendChild(s); });
    window.Prism = window.Prism || {}; window.Prism.manual = true;
    load(base + "prism.min.js").then((ok) => ok && window.Prism.languages && Promise.all(["python", "bash", "json", "cypher", "sql", "yaml", "typescript"].map((l) => load(base + "components/prism-" + l + ".min.js"))))
      .then((ok) => { if (ok && window.Prism && Prism.highlightAllUnder) Prism.highlightAllUnder(scope); });
  }

  /* ---------- checklists persist per page ---------- */
  function initChecklists(scope) {
    scope.querySelectorAll(".checklist input[type=checkbox]").forEach((cb, i) => {
      const key = "grfs-check-" + slug + "-" + i;
      try { cb.checked = localStorage.getItem(key) === "1"; } catch (e) { }
      cb.addEventListener("change", () => { try { localStorage.setItem(key, cb.checked ? "1" : "0"); } catch (e) { } });
    });
  }

  function init() {
    const main = document.querySelector("main");
    if (!main) return;
    body.prepend(buildTopbar());
    if (main.classList.contains("home")) {
      const mb = document.querySelector(".menubtn"); if (mb) mb.remove();
      initCode(main);
      initTables(main);
      body.appendChild(buildSiteFoot());
      return;
    }
    const ch = flat.find((c) => c.slug === slug);
    const layout = document.createElement("div");
    layout.className = "layout";
    main.before(layout);
    layout.appendChild(buildSidebar());
    const scrim = document.createElement("div");
    scrim.className = "side-scrim";
    scrim.hidden = true;
    scrim.addEventListener("click", () => toggleNav(false));
    layout.appendChild(scrim);
    const content = document.createElement("div");
    content.className = "content";
    layout.appendChild(content);
    const grid = document.createElement("div");
    grid.className = "content-grid";
    content.appendChild(grid);
    const col = document.createElement("div");
    col.className = "content-main";
    grid.appendChild(col);
    col.appendChild(main);
    decorateHeader(main, ch);
    const toc = buildToc(main);
    decorateHeadings(main);
    if (toc) grid.appendChild(toc); else layout.classList.add("no-toc");
    if (ch) col.appendChild(buildFooter(ch));
    body.appendChild(buildSiteFoot());
    initQuizzes(main);
    initTables(main);
    initCode(main);
    initChecklists(main);
    const curLink = document.querySelector('.sidebar a[aria-current="page"]');
    if (curLink) { const sb = document.querySelector(".sidebar"); if (curLink.offsetTop > sb.clientHeight - 80) sb.scrollTop = curLink.offsetTop - sb.clientHeight / 2; }
    if (location.hash) { const t = document.getElementById(decodeURIComponent(location.hash.slice(1))); if (t) setTimeout(() => t.scrollIntoView(), 50); }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
