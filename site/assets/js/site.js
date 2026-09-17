/* Site shell: top bar, search, chapter rail, on-page contents, progress, quizzes, code blocks, pager, footer.
   Chapter pages only author <main class="chapter"> content; this script wraps it.

   Languages: English pages live at /…, Chinese at /zh/…. The page language comes from <html lang>.
   Chinese pages load curriculum.zh.js before this file; its titles and summaries are merged into
   CURRICULUM here, so every consumer (rail, search, home page) reads the right language. A Chinese
   chapter page whose body has not been translated carries data-fallback="en" and gets a banner. */
(function () {
  "use strict";
  const C = window.CURRICULUM;
  const body = document.body;
  const root = body.dataset.root || ".";
  const slug = body.dataset.slug || "";
  const lang = (document.documentElement.lang || "en").toLowerCase().startsWith("zh") ? "zh" : "en";
  const base = lang === "zh" ? root + "/zh" : root; // where this language's pages live
  const STORE = "grfs-progress-v1";

  /* ---------- UI strings ---------- */
  const STRINGS = {
    en: {
      courseTitle: "Graph RAG from Scratch",
      brand: "Graph RAG",
      curriculum: "Curriculum", capstones: "Capstones", researchMap: "Research map", glossary: "Glossary", library: "Library",
      search: "Search", searchAria: "Search chapters", searchDialog: "Search the course",
      searchPlaceholder: "Search chapters, capstones and topics",
      searchEmpty: (q) => "No chapter matches <b>" + q + "</b>. Try a method name such as PageRank, Leiden or Cypher.",
      navigate: "navigate", open: "open", close: "close",
      results: (n) => n + (n === 1 ? " result" : " results"),
      appendix: "Appendix", appendixKey: "appendix",
      part: (n, t) => "Part " + n + " · " + t,
      openNav: "Open chapter list", toggleTheme: "Toggle dark mode", siteNav: "Site", chaptersNav: "Course chapters",
      github: "Source on GitHub", x: "Follow on X",
      inThisChapter: "In this chapter", linkToSection: "Link to this section",
      read: "read", build: "build",
      minutes: (m) => m + " min", hours: (h) => h + " h",
      figures: (n) => "interactive " + (n === 1 ? "figure" : "figures"),
      exercises: "exercises", milestones: "milestones", questions: "questions", buildsOn: "builds on",
      previous: "← Previous", next: "Next →", pager: "Chapter pager",
      footNote: "A self-paced course on graph retrieval-augmented generation, with a runnable reference implementation. The Kestrel Labs corpus used throughout is fictional.",
      footCourse: "Course", footReference: "Reference", footCredits: "Credits",
      startHere: "Start here", retrieval: "Retrieval", paperLibrary: "Paper and tool library", frameworks: "Frameworks",
      correct: "Correct.", notQuite: "Not quite.",
      quizScore: (a, n, r) => a + " of " + n + " answered" + (a ? ", " + r + " correct" : ""),
      copy: "copy", copied: "copied", selectToCopy: "select to copy",
      langLabel: "Language",
      fallback: "", fallbackLink: ""
    },
    zh: {
      courseTitle: "从零构建 Graph RAG",
      brand: "Graph RAG",
      curriculum: "课程大纲", capstones: "综合项目", researchMap: "研究地图", glossary: "术语表", library: "文献与工具",
      search: "搜索", searchAria: "搜索章节", searchDialog: "搜索课程",
      searchPlaceholder: "搜索章节、综合项目和主题",
      searchEmpty: (q) => "没有章节匹配 <b>" + q + "</b>。可以试试方法名，比如 PageRank、Leiden 或 Cypher。",
      navigate: "选择", open: "打开", close: "关闭",
      results: (n) => n + " 个结果",
      appendix: "附录", appendixKey: "附录",
      part: (n, t) => "第 " + n + " 部分 · " + t,
      openNav: "打开章节列表", toggleTheme: "切换深色模式", siteNav: "站点", chaptersNav: "课程章节",
      github: "GitHub 源码", x: "在 X 上关注",
      inThisChapter: "本章内容", linkToSection: "链接到本节",
      read: "阅读", build: "构建",
      minutes: (m) => m + " 分钟", hours: (h) => h + " 小时",
      figures: () => "个交互图",
      exercises: "道练习", milestones: "个里程碑", questions: "道测验", buildsOn: "前置章节",
      previous: "← 上一章", next: "下一章 →", pager: "章节翻页",
      footNote: "一门自学的图检索增强生成课程，配有可运行的参考实现。课程中使用的 Kestrel Labs 语料是虚构的。",
      footCourse: "课程", footReference: "参考", footCredits: "致谢",
      startHere: "从这里开始", retrieval: "检索", paperLibrary: "文献与工具库", frameworks: "框架实践",
      correct: "回答正确。", notQuite: "不太对。",
      quizScore: (a, n, r) => "已答 " + a + " / " + n + (a ? "，答对 " + r + " 道" : ""),
      copy: "复制", copied: "已复制", selectToCopy: "请手动选择复制",
      langLabel: "语言",
      fallback: "本章尚未翻译成中文，以下是英文原文。导航、测验和交互图的界面已是中文。",
      fallbackLink: "阅读英文页面"
    }
  };
  const T = STRINGS[lang];

  /* ---------- merge Chinese curriculum text ---------- */
  if (lang === "zh" && window.CURRICULUM_ZH) {
    const Z = window.CURRICULUM_ZH;
    C.title_en = C.title; C.title = T.courseTitle;
    C.parts.forEach((p) => {
      const zp = (Z.parts || {})[p.id] || {};
      ["title", "blurb", "bridge"].forEach((k) => { if (p[k] != null) p[k + "_en"] = p[k]; if (zp[k]) p[k] = zp[k]; });
      p.chapters.forEach((c) => {
        const zc = (Z.chapters || {})[c.slug] || {};
        ["title", "summary"].forEach((k) => { c[k + "_en"] = c[k]; if (zc[k]) c[k] = zc[k]; });
      });
    });
  }

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
    if (ch.part.id === "ap") return T.appendix;
    if (ch.slug.startsWith("c")) return lang === "zh" ? "综合项目 " + ch.slug.slice(1, 2) : "Capstone " + ch.slug.slice(1, 2);
    return lang === "zh" ? "第 " + parseInt(ch.slug.slice(0, 2), 10) + " 章" : "Chapter " + parseInt(ch.slug.slice(0, 2), 10);
  }
  function chapterId(ch) {
    if (ch.part.id === "ap") return "";
    if (ch.slug.startsWith("c")) return "C" + ch.slug.slice(1, 2);
    return ch.slug.slice(0, 2);
  }
  function partLabel(part) { return part.id === "ap" ? T.appendix : part.id === "p7" ? T.capstones : T.part(part.id.slice(1), "").replace(/ · $/, ""); }
  function partHeading(part) { return part.id === "ap" || part.id === "p7" ? part.title : T.part(part.id.slice(1), part.title); }
  function href(s) { return base + "/chapters/" + s + ".html"; }
  function home(hash) { return base + "/index.html" + (hash || ""); }
  // The same page in the other language. English and Chinese pages mirror each other path for path.
  function counterpart(target) {
    const b = target === "zh" ? root + "/zh" : root;
    return slug ? b + "/chapters/" + slug + ".html" : b + "/index.html";
  }
  window.GRFS = { flat, learnable, chapterLabel, chapterId, partLabel, partHeading, href, home, progress, root, base, lang, T };

  const REPO = "https://github.com/xinbetween/learn-graph-rag-from-scratch";
  const XURL = "https://x.com/xinbetween";
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const ICON = {
    mark: '<svg viewBox="0 0 16 16" aria-hidden="true"><line x1="3.5" y1="4" x2="12.5" y2="3.5" stroke="var(--accent)" stroke-width="1.4"/><line x1="3.5" y1="4" x2="6" y2="12.5" stroke="var(--accent)" stroke-width="1.4"/><line x1="6" y1="12.5" x2="12.5" y2="3.5" stroke="var(--accent)" stroke-width="1.4"/><circle cx="3.5" cy="4" r="2.4" fill="var(--accent)"/><circle cx="12.5" cy="3.5" r="2" fill="var(--accent)"/><circle cx="6" cy="12.5" r="2.4" fill="var(--accent)"/></svg>',
    search: '<svg width="13" height="13" viewBox="0 0 16 16" aria-hidden="true"><circle cx="7" cy="7" r="5" fill="none" stroke="currentColor" stroke-width="1.6"/><line x1="10.8" y1="10.8" x2="14.5" y2="14.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>',
    theme: '<svg width="15" height="15" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6.2" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M8 1.8a6.2 6.2 0 0 1 0 12.4z" fill="currentColor"/></svg>',
    menu: '<svg width="15" height="15" viewBox="0 0 16 16" aria-hidden="true"><path d="M2 4h12M2 8h12M2 12h12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
    github: '<svg width="15" height="15" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"/></svg>',
    x: '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>'
  };

  function doneCount() { return learnable.filter((c) => progress[c.slug]).length; }

  /* ---------- top bar ---------- */
  function buildTopbar() {
    const bar = document.createElement("header");
    bar.className = "topbar";
    const mac = /Mac|iPhone|iPad/.test(navigator.platform);
    const cur = (s) => (slug === s ? ' aria-current="page"' : "");
    const langsw = '<span class="langsw" role="group" aria-label="' + T.langLabel + '">' +
      (lang === "en" ? '<span class="on" aria-current="true">EN</span>' : '<a href="' + counterpart("en") + '" hreflang="en" lang="en">EN</a>') +
      (lang === "zh" ? '<span class="on" aria-current="true">中</span>' : '<a href="' + counterpart("zh") + '" hreflang="zh-Hans" lang="zh-Hans" title="中文">中</a>') +
      "</span>";
    bar.innerHTML =
      '<button class="iconbtn menubtn" aria-label="' + T.openNav + '" aria-expanded="false">' + ICON.menu + "</button>" +
      '<a class="brand" href="' + home() + '">' + ICON.mark + "<span>" + T.brand + "</span></a>" +
      '<nav class="topnav" aria-label="' + T.siteNav + '">' +
        '<a href="' + home("#curriculum") + '">' + T.curriculum + "</a>" +
        '<a class="hide-sm" href="' + href("c1-minigraphrag") + '"' + (slug.startsWith("c") ? ' aria-current="page"' : "") + ">" + T.capstones + "</a>" +
        '<a class="hide-sm" href="' + href("33-research-map") + '"' + cur("33-research-map") + ">" + T.researchMap + "</a>" +
        '<a href="' + href("glossary") + '"' + cur("glossary") + ">" + T.glossary + "</a>" +
        '<a href="' + href("library") + '"' + cur("library") + ">" + T.library + "</a>" +
        '<button class="searchbtn" aria-label="' + T.searchAria + '">' + ICON.search + '<span class="lbl">' + T.search + '</span><span class="kb">' + (mac ? "⌘K" : "Ctrl K") + "</span></button>" +
        langsw +
        '<button class="iconbtn theme-btn" aria-label="' + T.toggleTheme + '">' + ICON.theme + "</button>" +
        '<a class="iconbtn" href="' + REPO + '" aria-label="' + T.github + '" title="' + T.github + '" rel="noopener">' + ICON.github + "</a>" +
        '<a class="iconbtn" href="' + XURL + '" aria-label="' + T.x + '" title="' + T.x + '" rel="noopener">' + ICON.x + "</a>" +
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
    dlg.setAttribute("aria-label", T.searchDialog);
    dlg.innerHTML =
      '<div class="search-backdrop"></div><div class="search-panel">' +
      '<label class="search-in">' + ICON.search + '<input type="search" placeholder="' + T.searchPlaceholder + '" aria-label="' + T.search + '" autocomplete="off"><button class="search-esc" type="button">esc</button></label>' +
      '<div class="search-results" role="listbox"></div>' +
      '<div class="search-foot"><span><kbd>↑</kbd><kbd>↓</kbd>' + T.navigate + "</span><span><kbd>↵</kbd>" + T.open + "</span><span><kbd>esc</kbd>" + T.close + '</span><span class="count"></span></div></div>';
    body.appendChild(dlg);
    const input = dlg.querySelector("input");
    dlg.querySelector(".search-backdrop").addEventListener("click", closeSearch);
    dlg.querySelector(".search-esc").addEventListener("click", closeSearch);
    input.addEventListener("input", () => renderSearch(input.value));
    input.addEventListener("keydown", (e) => {
      if (e.isComposing) return; // an IME is still composing Chinese input
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
      // On Chinese pages the English title and summary stay searchable, since most method names are English.
      const t = (c.title + " " + (c.title_en || "")).toLowerCase();
      const s = (c.summary + " " + (c.summary_en || "")).toLowerCase();
      const p = (c.part.title + " " + (c.part.title_en || "")).toLowerCase();
      const id = chapterId(c).toLowerCase();
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
      res.innerHTML = '<div class="empty">' + T.searchEmpty(esc(q)) + "</div>";
    } else {
      let html = "", lastPart = null;
      hits.forEach((c) => {
        if (!terms.length && c.part !== lastPart) { html += '<div class="grp">' + esc(partHeading(c.part)) + "</div>"; lastPart = c.part; }
        html += '<a class="hit" role="option" href="' + href(c.slug) + '"><span class="hrow"><span class="ht">' + mark(c.title) + '</span><span class="hk">' + esc(chapterId(c) || T.appendixKey) + '</span></span><span class="hs">' + mark(c.summary) + "</span></a>";
      });
      res.innerHTML = html;
    }
    dlg.querySelector(".count").textContent = T.results(hits.length);
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
    nav.setAttribute("aria-label", T.chaptersNav);
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

  // Heading ids come from the heading's ASCII letters and digits; a heading with none (most Chinese
  // headings) gets a positional id. Ids are made unique either way.
  const usedIds = new Set();
  function assignId(h, i) {
    if (h.id) { usedIds.add(h.id); return h.id; }
    let id = h.textContent.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
    if (!id) id = "s" + (i + 1);
    let unique = id, n = 2;
    while (usedIds.has(unique) || document.getElementById(unique)) unique = id + "-" + n++;
    usedIds.add(unique);
    h.id = unique;
    return unique;
  }

  function buildToc(main) {
    const hs = [...main.querySelectorAll(":scope > h2")];
    if (hs.length < 2) return null;
    const aside = document.createElement("aside");
    aside.className = "toc";
    aside.innerHTML = "<h2>" + T.inThisChapter + "</h2><ol></ol>";
    const ol = aside.querySelector("ol");
    const links = [];
    hs.forEach((h) => {
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

  function assignHeadingIds(main) {
    [...main.querySelectorAll("h2, h3")].filter((h) => !h.closest(".quiz, .exercise, .project, .objectives, .viz, .keypoints"))
      .forEach((h, i) => assignId(h, i));
  }

  function decorateHeadings(main) {
    main.querySelectorAll("h2, h3").forEach((h) => {
      if (h.closest(".quiz, .exercise, .project, .objectives, .viz, .keypoints") || !h.id) return;
      const a = document.createElement("a");
      a.className = "anchor";
      a.href = "#" + h.id;
      a.setAttribute("aria-label", T.linkToSection);
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
      '<span class="chap-part">' + esc(ch.part.id === "ap" ? T.appendix : partHeading(ch.part)) + "</span>";
    head.insertBefore(kicker, head.firstChild);
    const meta = document.createElement("div");
    meta.className = "meta-row";
    const bits = [];
    const capstone = ch.slug.startsWith("c");
    if (ch.minutes) bits.push("<span><b>" + (ch.minutes >= 120 ? T.hours(Math.round(ch.minutes / 60)) : T.minutes(ch.minutes)) + "</b> " + (capstone ? T.build : T.read) + "</span>");
    const nEx = main.querySelectorAll(".exercise").length, nQ = main.querySelectorAll(".quiz").length, nViz = main.querySelectorAll(".viz").length;
    if (nViz) bits.push("<span><b>" + nViz + "</b> " + T.figures(nViz) + "</span>");
    if (nEx) bits.push("<span><b>" + nEx + "</b> " + (capstone ? T.milestones : T.exercises) + "</span>");
    if (nQ) bits.push("<span><b>" + nQ + "</b> " + T.questions + "</span>");
    const pre = ch.prereqs.map((p) => flat.find((f) => f.slug === p)).filter(Boolean);
    if (pre.length) bits.push("<span>" + T.buildsOn + " " + pre.map((p) => '<a href="' + href(p.slug) + '" title="' + esc(p.title) + '"><b>' + esc(chapterId(p)) + "</b> " + esc(p.title) + "</a>").join(lang === "zh" ? "、" : ", ") + "</span>");
    meta.innerHTML = bits.join("");
    if (bits.length) {
      const lede = head.querySelector(".lede");
      const h1 = head.querySelector("h1");
      (lede || h1).after(meta);
    }
    document.title = (head.querySelector("h1") || {}).textContent + " | " + C.title;
  }

  // A Chinese page that still carries the English body says so, and links to the English page.
  function addFallbackBanner(main) {
    if (lang !== "zh" || body.dataset.fallback !== "en") return;
    const note = document.createElement("div");
    note.className = "callout note lang-fallback";
    note.setAttribute("lang", "zh-Hans");
    note.innerHTML = "<p>" + T.fallback + ' <a href="' + counterpart("en") + '" hreflang="en">' + T.fallbackLink + "</a></p>";
    main.prepend(note);
    main.querySelectorAll(":scope > *:not(.lang-fallback)").forEach((el) => { if (!el.hasAttribute("lang")) el.setAttribute("lang", "en"); });
  }

  function buildFooter(ch) {
    const foot = document.createElement("footer");
    foot.className = "chapter-foot";
    const idx = flat.indexOf(ch);
    const prev = flat[idx - 1];
    const next = flat[idx + 1];
    let html = '<nav class="pager" aria-label="' + T.pager + '">';
    if (prev) html += '<a class="prev" href="' + href(prev.slug) + '"><small>' + T.previous + "</small>" + esc((chapterId(prev) ? chapterId(prev) + " " : "") + prev.title) + "</a>";
    if (next) html += '<a class="next" href="' + href(next.slug) + '"><small>' + T.next + "</small>" + esc((chapterId(next) ? chapterId(next) + " " : "") + next.title) + "</a>";
    html += "</nav>";
    foot.innerHTML = html;
    // A chapter counts as complete once the reader scrolls down to its pager.
    // Requiring a real scroll keeps short viewports and #fragment jumps from marking it on load.
    // Progress is keyed by slug, so reading a chapter in either language completes it.
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
      '<div><a class="brand" href="' + home() + '">' + ICON.mark + "<span>" + esc(C.title) + '</span></a><p class="note">' + T.footNote + '</p><p class="note"><a href="' + REPO + '" rel="noopener">' + T.github + '</a> · <a href="' + XURL + '" rel="noopener">' + T.x + "</a></p></div>" +
      "<div><h5>" + T.footCourse + '</h5><ul><li><a href="' + home("#curriculum") + '">' + T.curriculum + '</a></li><li><a href="' + href("00-welcome") + '">' + T.startHere + '</a></li><li><a href="' + href("14-local-search") + '">' + T.retrieval + '</a></li><li><a href="' + href("c1-minigraphrag") + '">' + T.capstones + "</a></li></ul></div>" +
      "<div><h5>" + T.footReference + '</h5><ul><li><a href="' + href("glossary") + '">' + T.glossary + '</a></li><li><a href="' + href("library") + '">' + T.paperLibrary + '</a></li><li><a href="' + href("33-research-map") + '">' + T.researchMap + '</a></li><li><a href="' + href("28-frameworks-in-practice") + '">' + T.frameworks + "</a></li></ul></div>" +
      "<div><h5>" + T.footCredits + '</h5><ul><li><a href="https://github.com/microsoft/graphrag">Microsoft GraphRAG</a></li><li><a href="https://github.com/DEEP-PolyU/Awesome-GraphRAG">Awesome-GraphRAG</a></li><li><a href="https://github.com/graphrag/awesome-graphrag">graphrag/awesome-graphrag</a></li><li><a href="https://huggingface.co/collections/graphrag/graphrag-papers">GraphRAG papers</a></li></ul></div>' +
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
            v.textContent = right ? T.correct : T.notQuite;
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
      scoreEl.textContent = T.quizScore(answered.length, quizzes.length, right);
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
      b.textContent = T.copy;
      b.addEventListener("click", async () => {
        try { await navigator.clipboard.writeText(pre.querySelector("code") ? pre.querySelector("code").innerText : pre.innerText); b.textContent = T.copied; }
        catch (e) { b.textContent = T.selectToCopy; }
        setTimeout(() => (b.textContent = T.copy), 1400);
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
    const cdn = "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/";
    const load = (src) => new Promise((res) => { const s = document.createElement("script"); s.src = src; s.onload = () => res(true); s.onerror = () => res(false); document.body.appendChild(s); });
    window.Prism = window.Prism || {}; window.Prism.manual = true;
    load(cdn + "prism.min.js").then((ok) => ok && window.Prism.languages && Promise.all(["python", "bash", "json", "cypher", "sql", "yaml", "typescript"].map((l) => load(cdn + "components/prism-" + l + ".min.js"))))
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
    addFallbackBanner(main);
    assignHeadingIds(main);
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
