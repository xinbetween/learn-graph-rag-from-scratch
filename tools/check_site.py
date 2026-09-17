"""Static checks for the course site: required components, JSON viz configs, internal links, slugs."""
import json, re, sys
from html.parser import HTMLParser
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"
cur = (SITE / "assets/js/curriculum.js").read_text()
slugs = re.findall(r'slug: "([^"]+)"', cur)

class P(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []; self.ids = set(); self.in_json = False; self.json = []; self.buf = ""
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a: self.ids.add(a["id"])
        if tag == "a" and "href" in a: self.links.append(a["href"])
        if tag == "script" and a.get("type") == "application/json": self.in_json = True; self.buf = ""
    def handle_endtag(self, tag):
        if tag == "script" and self.in_json: self.json.append(self.buf); self.in_json = False
    def handle_data(self, d):
        if self.in_json: self.buf += d

problems = 0
rows = []
for slug in slugs:
    f = SITE / "chapters" / f"{slug}.html"
    if not f.exists():
        rows.append((slug, "MISSING")); problems += 1; continue
    html = f.read_text()
    p = P(); p.feed(html)
    issues = []
    if f'data-slug="{slug}"' not in html: issues.append("data-slug mismatch")
    for i, j in enumerate(p.json):
        try: json.loads(j)
        except Exception as e: issues.append(f"viz json #{i}: {e}")
    for href in p.links:
        if href.startswith(("http", "mailto:", "#")): continue
        target = href.split("#")[0]
        if not (f.parent / target).resolve().exists(): issues.append(f"broken link {href}")
    counts = dict(
        viz=html.count('class="viz"'), svg=len(re.findall(r'class="diagram"', html)),
        ex=html.count('class="exercise"'), ans=html.count('class="answer"'),
        quiz=html.count('class="quiz"'), qa=html.count('class="qa"'),
        proj=html.count('class="project"'), words=len(re.sub(r"<[^>]+>", " ", html).split()),
    )
    for q in re.findall(r'<div class="quiz">(.*?)</div>\s*</div>', html, flags=re.S):
        if q.count("data-correct") != 1: issues.append("quiz without exactly one data-correct")
    if slug not in ("glossary", "library"):
        need = dict(viz=1, svg=1, quiz=3 if slug.startswith("c") else 5, qa=4)
        if not slug.startswith("c"): need.update(ex=4, proj=1)
        for k, v in need.items():
            if counts[k] < v: issues.append(f"{k} {counts[k]}<{v}")
        if counts["ans"] < counts["ex"] and not slug.startswith("c"): issues.append("exercise without answer")
    problems += len(issues)
    rows.append((slug, counts, issues))


# ---------- Chinese mirror ----------
def shape(html):
    """The parts of a chapter a translation must keep: figure types in order, component counts, and the
    position of the correct option in every quiz."""
    quizzes = re.findall(r'<div class="quiz">(.*?)<div class="explain">', html, flags=re.S)
    return dict(
        viz=re.findall(r'class="viz" data-viz="([^"]+)"', html),
        svg=html.count('class="diagram"'), ex=html.count('class="exercise"'), ans=html.count('class="answer"'),
        qa=html.count('class="qa"'), proj=html.count('class="project"'), keypoints=html.count('class="keypoints"'),
        refs=len(re.findall(r"<li", html.split('class="refs"', 1)[1].split("</ul>", 1)[0])) if 'class="refs"' in html else 0,
        quiz=[[i for i, li in enumerate(re.findall(r"<li\b[^>]*>", q)) if "data-correct" in li] for q in quizzes],
    )

zh_rows = []
if not (SITE / "zh/index.html").exists():
    problems += 1; print("zh/index.html MISSING")
for slug in slugs:
    f = SITE / "zh/chapters" / f"{slug}.html"
    if not f.exists():
        zh_rows.append((slug, "missing (run tools/build_zh.py)")); problems += 1; continue
    html = f.read_text()
    issues = []
    if '<html lang="zh-Hans"' not in html: issues.append("lang is not zh-Hans")
    if f'data-slug="{slug}"' not in html: issues.append("data-slug mismatch")
    if "curriculum.zh.js" not in html: issues.append("curriculum.zh.js not loaded")
    p = P(); p.feed(html)
    for i, j in enumerate(p.json):
        try: json.loads(j)
        except Exception as e: issues.append(f"viz json #{i}: {e}")
    for href in p.links:
        if href.startswith(("http", "mailto:", "#")): continue
        if not (f.parent / href.split("#")[0]).resolve().exists(): issues.append(f"broken link {href}")
    translated = re.search(r'<body[^>]*data-translated="true"', html) is not None
    if translated:
        if 'data-fallback="en"' in html: issues.append("both data-translated and data-fallback")
        en_shape, zh_shape = shape((SITE / "chapters" / f"{slug}.html").read_text()), shape(html)
        for k in en_shape:
            if en_shape[k] != zh_shape[k]:
                issues.append(f"shape differs from English in {k}: en={en_shape[k]} zh={zh_shape[k]}")
    elif 'data-fallback="en"' not in html:
        issues.append("neither translated nor marked as English fallback")
    problems += len(issues)
    zh_rows.append((slug, "translated" if translated else "fallback", issues))

for r in rows:
    if r[1] == "MISSING": print(f"{r[0]:32} MISSING"); continue
    c = r[1]
    print(f"{r[0]:32} words={c['words']:5} viz={c['viz']} svg={c['svg']} ex={c['ex']} quiz={c['quiz']} qa={c['qa']} proj={c['proj']}" + ("" if not r[2] else "  !! " + "; ".join(r[2][:6])))
n_tr = sum(1 for r in zh_rows if len(r) == 3 and r[1] == "translated")
print(f"zh: {n_tr} translated, {len(zh_rows) - n_tr} English fallback")
for r in zh_rows:
    if len(r) == 2 or r[2]:
        print(f"  zh/{r[0]:30} " + (r[1] if len(r) == 2 else "!! " + "; ".join(r[2][:6])))
print("problems:", problems)
sys.exit(1 if problems else 0)
