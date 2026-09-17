"""Keep the Chinese mirror under site/zh/ in step with the English site.

Every English chapter page has a Chinese counterpart at site/zh/chapters/<slug>.html:

- A translated page carries data-translated="true" on <body>. Its content is left alone; only the parts of
  <head> and the script tags this tool owns are normalized.
- Any other page is regenerated from the English source: same body, Chinese chrome, and
  data-fallback="en" so site.js shows the "not yet translated" banner. Regenerating means an English edit
  reaches the fallback page on the next run.

site/zh/index.html is hand-written and must exist. Both languages get hreflang alternates.

Run after changing an English chapter or adding a translation, then run tools/stamp_assets.py.
CI runs both and fails if either would change a file.
"""
import re
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"
ORIGIN = "https://graphrag.xinbetween.com"
slugs = re.findall(r'slug: "([^"]+)"', (SITE / "assets/js/curriculum.js").read_text())


def alternates(path: str) -> str:
    return (f'<link rel="alternate" hreflang="en" href="{ORIGIN}/{path}">\n'
            f'<link rel="alternate" hreflang="zh-Hans" href="{ORIGIN}/zh/{path}">\n'
            f'<link rel="alternate" hreflang="x-default" href="{ORIGIN}/{path}">\n')


def set_alternates(html: str, path: str) -> str:
    html = re.sub(r'<link rel="alternate" hreflang="[^"]+" href="[^"]*">\n?', "", html)
    return html.replace('<link rel="stylesheet"', alternates(path) + '<link rel="stylesheet"', 1)


def zh_chrome(html: str, up: str) -> str:
    """Point a page at the shared assets from one directory deeper and load the Chinese curriculum text.
    `up` is the prefix that reaches site/ from the Chinese page ("../" for zh/index.html, "../../" for chapters)."""
    html = re.sub(r'<html lang="[^"]*"', '<html lang="zh-Hans"', html, count=1)
    html = re.sub(r'((?:href|src)=")(?:\.\./)*(assets/)', lambda m: m.group(1) + up + m.group(2), html)
    html = re.sub(r'data-root="[^"]*"', f'data-root="{up.rstrip("/")}"', html, count=1)
    # Keep an existing ?v= stamp so a regenerate-then-stamp cycle leaves unchanged pages untouched.
    prev = re.search(r'<script src="[^"]*curriculum\.zh\.js(\?v=[0-9a-f]+)?"></script>', html)
    stamp = prev.group(1) or "" if prev else ""
    html = re.sub(r'<script src="[^"]*curriculum\.zh\.js[^"]*"></script>\n?', "", html)
    html = re.sub(r'(<script src="[^"]*assets/js/site\.js[^"]*"></script>)',
                  lambda m: f'<script src="{up}assets/js/curriculum.zh.js{stamp}"></script>\n' + m.group(1), html, count=1)
    return html


def fallback_from_english(en: str) -> str:
    html = zh_chrome(en, "../../")
    body = re.search(r"<body([^>]*)>", html)
    attrs = re.sub(r'\s*data-(?:fallback|translated)="[^"]*"', "", body.group(1)) + ' data-fallback="en"'
    return html[: body.start()] + f"<body{attrs}>" + html[body.end():]


def main() -> int:
    changed = []
    (SITE / "zh/chapters").mkdir(parents=True, exist_ok=True)

    home_zh = SITE / "zh/index.html"
    if not home_zh.exists():
        print("missing site/zh/index.html (hand-written, not generated)")
        return 1

    pages = [("index.html", SITE / "index.html", home_zh, "../")]
    pages += [(f"chapters/{s}.html", SITE / f"chapters/{s}.html", SITE / f"zh/chapters/{s}.html", "../../") for s in slugs]
    translated = 0
    for path, en_file, zh_file, up in pages:
        en = en_file.read_text()
        new_en = set_alternates(en, path)
        if new_en != en:
            en_file.write_text(new_en)
            changed.append(str(en_file.relative_to(SITE)))

        old = zh_file.read_text() if zh_file.exists() else None
        if old is not None and re.search(r'<body[^>]*data-translated="true"', old):
            translated += path != "index.html"
            new = zh_chrome(old, up)
        elif path == "index.html":
            new = zh_chrome(old, up)
        else:
            new = fallback_from_english(new_en)
            prev = re.search(r'curriculum\.zh\.js(\?v=[0-9a-f]+)"', old or "")
            if prev:
                new = new.replace('curriculum.zh.js"', "curriculum.zh.js" + prev.group(1) + '"', 1)
        new = set_alternates(new, path)
        if new != old:
            zh_file.write_text(new)
            changed.append(str(zh_file.relative_to(SITE)))

    stale = {p.name for p in (SITE / "zh/chapters").glob("*.html")} - {f"{s}.html" for s in slugs}
    for name in sorted(stale):
        (SITE / "zh/chapters" / name).unlink()
        changed.append(f"zh/chapters/{name} (removed)")

    print(f"zh mirror: {len(slugs)} pages, {translated} translated, {len(slugs) - translated} English fallback; "
          f"{len(changed)} files updated")
    for c in changed[:20]:
        print("  ", c)
    return 0


if __name__ == "__main__":
    sys.exit(main())
