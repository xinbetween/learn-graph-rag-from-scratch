"""Generate sitemap.xml, robots.txt, llms.txt and llms-full.txt for the site.

- sitemap.xml   every English and Chinese page, each with hreflang alternates and a lastmod taken from
                the file's last commit (falling back to its mtime outside a git checkout).
- robots.txt    allow everything, point at the sitemap.
- llms.txt      the index an LLM reads first: what the course is, then every page as a link with a
                one-line description, following the llms.txt convention (llmstxt.org).
- llms-full.txt the whole English course as plain text, chapter by chapter, for a model that wants the
                content rather than the links. Figures and diagrams become short bracketed notes.

Run after adding or renaming a page, or after editing chapter titles, summaries or ledes; CI regenerates
these and fails if anything would change.
"""
from __future__ import annotations

import html
import re
import subprocess
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
ORIGIN = "https://graphrag.xinbetween.com"
REPO = "https://github.com/xinbetween/learn-graph-rag-from-scratch"

CUR = (SITE / "assets/js/curriculum.js").read_text()
COURSE_TITLE = re.search(r'title: "([^"]+)"', CUR).group(1)


def parts():
    """[(part title, blurb, [(slug, title, summary, minutes)])] in curriculum order."""
    out = []
    for block in re.split(r"\n    \{\n", CUR)[1:]:
        p = re.search(r'id: "(\w+)",(?: bridge: "[^"]*",)? title: "([^"]+)", blurb: "([^"]+)"', block)
        if not p:
            continue
        chapters = [(m.group(1), m.group(2), m.group(4), int(m.group(3)))
                    for m in re.finditer(r'\{ slug: "([^"]+)", title: "([^"]+)", minutes: (\d+),[^}]*?summary: "([^"]+)" \}', block, re.S)]
        out.append((p.group(2), p.group(3), chapters))
    return out


PARTS = parts()
SLUGS = [c[0] for _, _, chs in PARTS for c in chs]


def git_lastmod(path: Path) -> str:
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cI", "--", str(path)],
                             cwd=ROOT, capture_output=True, text=True, timeout=20).stdout.strip()
        if out:
            return out[:10]
    except Exception:
        pass
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).date().isoformat()


def meta(path: Path) -> dict:
    s = path.read_text()
    def find(pat, default=""):
        m = re.search(pat, s, re.S)
        return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else default
    return {
        "title": find(r"<title>(.*?)</title>").split(" | ")[0],
        "description": find(r'<meta name="description" content="(.*?)">'),
        "lede": find(r'<p class="lede">(.*?)</p>'),
        "lastmod": git_lastmod(path),
    }


# ---------------------------------------------------------------- sitemap
def sitemap() -> str:
    rows = []
    for rel in ["index.html"] + [f"chapters/{s}.html" for s in SLUGS]:
        en, zh = SITE / rel, SITE / "zh" / rel
        for loc, alt_self, priority in ((f"{ORIGIN}/{rel}", "en", None), (f"{ORIGIN}/zh/{rel}", "zh-Hans", None)):
            path = en if alt_self == "en" else zh
            if not path.exists():
                continue
            pri = "1.0" if rel == "index.html" else "0.8" if alt_self == "en" else "0.6"
            rows.append(
                "  <url>\n"
                f"    <loc>{loc}</loc>\n"
                f"    <lastmod>{meta(path)['lastmod']}</lastmod>\n"
                f"    <changefreq>monthly</changefreq>\n"
                f"    <priority>{pri}</priority>\n"
                f'    <xhtml:link rel="alternate" hreflang="en" href="{ORIGIN}/{rel}"/>\n'
                f'    <xhtml:link rel="alternate" hreflang="zh-Hans" href="{ORIGIN}/zh/{rel}"/>\n'
                f'    <xhtml:link rel="alternate" hreflang="x-default" href="{ORIGIN}/{rel}"/>\n'
                "  </url>"
            )
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
            '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
            + "\n".join(rows) + "\n</urlset>\n")


def robots() -> str:
    return ("# https://graphrag.xinbetween.com\n"
            "User-agent: *\n"
            "Allow: /\n\n"
            f"Sitemap: {ORIGIN}/sitemap.xml\n")


# ---------------------------------------------------------------- llms.txt
def llms_txt() -> str:
    L = [f"# {COURSE_TITLE}", ""]
    L += ["> A self-paced course on graph retrieval-augmented generation (GraphRAG). It starts from a",
          "> hundred-line vector RAG and the questions it cannot answer, then builds the alternative one",
          "> stage at a time: LLM extraction into a knowledge graph, entity resolution, community detection",
          "> and reports, eight retrieval methods (local, global, DRIFT, LightRAG, Personalized PageRank,",
          "> paths, subgraphs, hybrid), context construction, evaluation, cost, temporal graphs and agents.", ""]
    L += ["Every example uses one fictional corpus about Kestrel Labs, an ocean-tech startup, so the same",
          "graph grows from raw text to answers across the whole course. Each chapter has a mechanism",
          "diagram, interactive figures, exercises with worked answers, graded questions and a project.",
          "The companion Python package `minigraphrag` implements every stage and runs offline against a",
          "deterministic mock model.", ""]
    for title, blurb, chs in PARTS:
        L.append(f"## {title}")
        L.append("")
        if blurb:
            L.append(f"{blurb}")
            L.append("")
        for slug, ctitle, summary, _ in chs:
            L.append(f"- [{ctitle}]({ORIGIN}/chapters/{slug}.html): {summary}")
        L.append("")
    L += ["## Code", "",
          f"- [minigraphrag reference implementation]({REPO}/tree/main/code): chunking, extraction with gleaning,",
          "  entity resolution, Louvain and Leiden communities, community reports, eight retrieval methods,",
          "  Text2Cypher, a bi-temporal graph and an evaluation harness. Runs offline with a mock LLM.",
          f"- [Kestrel Labs corpus]({REPO}/tree/main/code/data/corpus): the 12 fictional documents every chapter uses.",
          f"- [Evaluation questions]({REPO}/blob/main/code/data/questions.jsonl): 23 questions with answers and supporting documents.",
          ""]
    L += ["## Chinese (中文)", "",
          f"- [从零构建 Graph RAG]({ORIGIN}/zh/): the same course in Chinese. Navigation, search, quizzes and figures",
          "  are translated throughout; chapters are translated progressively and the rest fall back to English.",
          ""]
    L += ["## Optional", "",
          f"- [Full course text]({ORIGIN}/llms-full.txt): every English chapter as plain text in one file.",
          f"- [Repository]({REPO}): source of the site and the reference implementation.",
          ""]
    return "\n".join(L)


# ------------------------------------------------------------- zh/llms.txt
ZH = (SITE / "assets/js/curriculum.zh.js").read_text()


def zh_text():
    """{id or slug: (title, blurb/summary)} from curriculum.zh.js."""
    parts_zh, chs_zh = {}, {}
    for m in re.finditer(r'(\w+): \{ title: "([^"]+)", blurb: "([^"]+)"', ZH):
        parts_zh[m.group(1)] = (m.group(2), m.group(3))
    for m in re.finditer(r'"([\w-]+)": \{ title: "([^"]+)",\s*summary: "([^"]+)" \}', ZH):
        chs_zh[m.group(1)] = (m.group(2), m.group(3))
    return parts_zh, chs_zh


def llms_txt_zh() -> str:
    parts_zh, chs_zh = zh_text()
    ids = re.findall(r'id: "(\w+)"', CUR)
    L = ["# 从零构建 Graph RAG", ""]
    L += ["> 一门自学的图检索增强生成（GraphRAG）课程。它从一个一百行的向量 RAG 以及它答不了的问题出发，",
          "> 一步一步构建另一条路：用 LLM 抽取知识图谱、实体消解、社区发现与社区报告、八种检索方法",
          "> （局部搜索、全局搜索、DRIFT、LightRAG、个性化 PageRank、路径、子图、混合检索）、上下文构建、",
          "> 评估、成本、时序图与智能体。", ""]
    L += ["所有示例都使用同一份关于 Kestrel Labs（一家虚构的海洋科技公司）的语料，因此同一张图会贯穿整门课程，",
          "从原始文本一路长到答案。每一章都有原理图、交互图、附参考解答的练习、带解析的测验和一个项目。",
          "配套的 Python 包 `minigraphrag` 实现了每个阶段，用模拟模型即可离线运行。",
          "导航、搜索、测验和交互图界面均为中文；章节正文在逐步翻译，尚未翻译的章节回退到英文原文。", ""]
    for pid, (title, blurb, chs) in zip(ids, PARTS):
        ztitle, zblurb = parts_zh.get(pid, (title, blurb))
        L += [f"## {ztitle}", "", zblurb, ""]
        for slug, ctitle, summary, _ in chs:
            zt, zs = chs_zh.get(slug, (ctitle, summary))
            L.append(f"- [{zt}]({ORIGIN}/zh/chapters/{slug}.html)：{zs}")
        L.append("")
    L += ["## 代码", "",
          f"- [minigraphrag 参考实现]({REPO}/tree/main/code)：分块、带补漏抽取的实体关系抽取、实体消解、",
          "  Louvain 与 Leiden 社区发现、社区报告、八种检索方法、Text2Cypher、双时态图与评估框架，可离线运行。",
          f"- [Kestrel Labs 语料]({REPO}/tree/main/code/data/corpus)：每一章都在用的 12 篇虚构文档。", ""]
    L += ["## 其他", "",
          f"- [English version]({ORIGIN}/)：课程的英文版，以及英文全文 {ORIGIN}/llms-full.txt。",
          f"- [代码仓库]({REPO})", ""]
    return "\n".join(L)


# ------------------------------------------------------------ llms-full.txt
BLOCK = {"p", "li", "h1", "h2", "h3", "h4", "h5", "tr", "figcaption", "summary", "pre", "blockquote", "div", "section", "details", "dt", "dd"}


class ToText(HTMLParser):
    """Turn a chapter page into readable plain text: headings keep their level, code blocks are fenced,
    tables become pipe rows, and figures collapse to a bracketed note with their caption."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.line: list[str] = []
        self.skip = 0          # inside <script>, <style> or <svg>
        self.pre = 0
        self.hide = 0          # inside a figure/visualization we summarize instead of transcribing
        self.stack: list[str] = []

    # -- helpers
    def flush(self, blank=False):
        text = "".join(self.line)
        text = text if self.pre else re.sub(r"[ \t]+", " ", text).strip()
        if text:
            self.out.append(text)
        if blank and self.out and self.out[-1] != "":
            self.out.append("")
        self.line = []

    def add(self, s):
        self.line.append(s)

    # -- parser
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class", "")
        if tag in ("script", "style", "svg"):
            self.skip += 1
            return
        if self.skip:
            return
        if "viz" in cls.split() or "diagram" in cls.split():
            self.flush(True)
            self.hide += 1
            if "viz" in cls.split():
                self.out.append(f"[Interactive figure: {a.get('data-viz', 'figure')}]")
            else:
                self.out.append("[Diagram]")
            return
        if self.hide:
            return
        if tag == "pre":
            self.flush(True)
            lang = "python"
            self.pre += 1
            self.out.append(f"```{lang}" if "data-file" not in a else f"```{lang}  # {a['data-file']}")
            return
        if tag in BLOCK:
            self.flush(tag not in ("div", "section", "details"))
        if tag in ("h1", "h2", "h3", "h4", "h5"):
            self.stack.append(tag)
            self.add("#" * int(tag[1]) + " ")
        elif tag == "li":
            self.add("- ")
        elif tag == "summary":
            self.add("▸ ")
        elif tag in ("td", "th") and self.line:
            self.add(" | ")
        elif tag == "blockquote":
            self.add("> ")
        elif cls.startswith("callout-title"):
            self.add("**")
        elif tag == "br":
            self.flush()

    def handle_endtag(self, tag):
        if tag in ("script", "style", "svg"):
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if self.hide:
            if tag == "div" or tag == "figure":
                self.hide = max(0, self.hide - 1)
                if not self.hide:
                    self.out.append("")
            return
        if tag == "pre":
            self.flush()
            self.pre = max(0, self.pre - 1)
            self.out.append("```")
            self.out.append("")
            return
        if tag in ("span",) and self.line and self.line[-1] == "**":
            self.add("**")
        if tag in BLOCK:
            self.flush(tag in ("p", "h1", "h2", "h3", "h4", "tr", "summary", "figcaption", "pre", "dd"))
        if tag in ("h1", "h2", "h3", "h4", "h5") and self.stack:
            self.stack.pop()

    def handle_data(self, data):
        if self.skip or self.hide:
            return
        if self.pre:
            self.line.append(data)
            self.flush()
            return
        self.line.append(data)

    def text(self) -> str:
        self.flush()
        lines, out = self.out, []
        for ln in lines:
            if ln == "" and out and out[-1] == "":
                continue
            out.append(ln.rstrip())
        return "\n".join(out).strip() + "\n"


def prepare(body: str) -> str:
    """Rewrite a few structures so the text conversion keeps information a reader would lose otherwise:
    a figure's title, which quiz option is correct, and where a quiz explanation starts."""
    def viz_note(m):
        cfg = m.group(2)
        title = re.search(r'"title"\s*:\s*"([^"]*)"', cfg)
        sub = re.search(r'"subtitle"\s*:\s*"([^"]*)"', cfg)
        label = title.group(1) if title else m.group(1)
        if sub:
            label += " — " + sub.group(1)
        return f'<p>[Interactive figure: {label} ({m.group(1)})]</p>'
    body = re.sub(r'<div class="viz" data-viz="([^"]+)">\s*<script type="application/json">(.*?)</script>\s*</div>',
                  viz_note, body, flags=re.S)
    body = re.sub(r"<li data-correct>", "<li>✓ (correct) ", body)
    body = re.sub(r'<div class="explain">', '<div class="explain">Answer: ', body)
    return body


def page_text(path: Path) -> str:
    s = path.read_text()
    body = s[s.index("<main"):s.index("</main>")]
    p = ToText()
    p.feed(prepare(body))
    return p.text()


def llms_full() -> str:
    m = meta(SITE / "index.html")
    parts_out = [f"# {COURSE_TITLE}", "",
                 f"Source: {ORIGIN}/  ·  Repository: {REPO}", "",
                 m["description"], "",
                 "Every chapter of the English course follows, in order. Interactive figures and diagrams are",
                 "noted in brackets; their explanation is in the surrounding text. Code blocks are the chapter's",
                 "own; they build the `minigraphrag` package in the repository.", "",
                 "---", ""]
    for title, _, chs in PARTS:
        parts_out += [f"# Part: {title}", ""]
        for slug, ctitle, summary, _ in chs:
            f = SITE / "chapters" / f"{slug}.html"
            parts_out += [f"## {ctitle}", "",
                          f"URL: {ORIGIN}/chapters/{slug}.html", f"Summary: {summary}", "",
                          page_text(f), "---", ""]
    return "\n".join(parts_out)


def main() -> int:
    files = {
        "sitemap.xml": sitemap(),
        "robots.txt": robots(),
        "llms.txt": llms_txt(),
        "llms-full.txt": llms_full(),
        "zh/llms.txt": llms_txt_zh(),
    }
    changed = []
    for name, content in files.items():
        path = SITE / name
        if not path.exists() or path.read_text() != content:
            path.write_text(content)
            changed.append(name)
    urls = sitemap().count("<loc>")
    print(f"meta: sitemap {urls} urls, llms.txt {len(files['llms.txt'].splitlines())} lines, "
          f"llms-full.txt {len(files['llms-full.txt']) // 1024} KB; "
          + (f"updated {', '.join(changed)}" if changed else "no changes"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
