"""Append ?v=<content hash> to CSS/JS links in every page so browsers never mix stale and fresh assets.
Run after editing anything in site/assets/."""
import hashlib, re
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"
assets = {p.relative_to(SITE).as_posix(): hashlib.sha1(p.read_bytes()).hexdigest()[:8]
          for p in (SITE / "assets").rglob("*") if p.suffix in (".css", ".js")}
pat = re.compile(r'((?:href|src)="(?:\.\./|\./)*(assets/[^"?]+\.(?:css|js)))(?:\?v=[0-9a-f]+)?"')
for page in [SITE / "index.html", *sorted((SITE / "chapters").glob("*.html")), *sorted(SITE.glob("zh/**/*.html"))]:
    html = page.read_text()
    new = pat.sub(lambda m: f'{m.group(1)}?v={assets[m.group(2)]}"' if m.group(2) in assets else m.group(0), html)
    if new != html:
        page.write_text(new)
print("stamped", len(assets), "assets:", ", ".join(f"{k}?v={v}" for k, v in sorted(assets.items())))
