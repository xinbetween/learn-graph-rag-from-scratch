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

for r in rows:
    if r[1] == "MISSING": print(f"{r[0]:32} MISSING"); continue
    c = r[1]
    print(f"{r[0]:32} words={c['words']:5} viz={c['viz']} svg={c['svg']} ex={c['ex']} quiz={c['quiz']} qa={c['qa']} proj={c['proj']}" + ("" if not r[2] else "  !! " + "; ".join(r[2][:6])))
print("problems:", problems)
sys.exit(1 if problems else 0)
