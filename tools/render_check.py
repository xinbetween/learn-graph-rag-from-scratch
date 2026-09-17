"""Load every page in Chromium, click through all visualizations, report JS errors and horizontal overflow."""
import asyncio, re, sys
from pathlib import Path
from playwright.async_api import async_playwright

SITE = Path(__file__).resolve().parent.parent / "site"
BASE = "http://localhost:8765/"
slugs = re.findall(r'slug: "([^"]+)"', (SITE / "assets/js/curriculum.js").read_text())
pages = ["index.html"] + [f"chapters/{s}.html" for s in slugs]

async def check(ctx, path, width):
    pg = await ctx.new_page()
    await pg.set_viewport_size({"width": width, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)))
    pg.on("console", lambda m: errs.append("console: " + m.text) if m.type == "error" and "cdnjs" not in m.text and "fonts" not in m.text else None)
    await pg.goto(BASE + path, wait_until="load")
    await pg.wait_for_timeout(300)
    # click every viz step button a few times and every quiz first option
    n = await pg.evaluate("""async () => {
      let clicks = 0;
      for (const v of document.querySelectorAll('.viz')) {
        for (let i = 0; i < 12; i++) {
          const b = [...v.querySelectorAll('.viz-controls button')].find(x => x.textContent === 'Next' && !x.disabled);
          if (!b) break; b.click(); clicks++;
        }
        for (const r of v.querySelectorAll('input[type=range]')) { r.value = r.min; r.dispatchEvent(new Event('input')); r.value = r.max; r.dispatchEvent(new Event('input')); }
      }
      document.querySelectorAll('.quiz li:first-child button').forEach(b => b.click());
      document.querySelectorAll('details').forEach(d => d.open = true);
      return clicks;
    }""")
    await pg.wait_for_timeout(300)
    failed_viz = await pg.evaluate("[...document.querySelectorAll('.viz')].filter(v => !v.dataset.mounted || /failed|error|Unknown/.test(v.textContent.slice(0,80))).length")
    overflow = await pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    await pg.close()
    return errs, failed_viz, overflow, n

async def main():
    bad = 0
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for scheme in ("light", "dark"):
            ctx = await b.new_context(color_scheme=scheme)
            for path in pages:
                for width in ((1300, 390) if scheme == "light" else (1300,)):
                    errs, fv, ov, n = await check(ctx, path, width)
                    if errs or fv or ov > 2:
                        bad += 1
                        print(f"{scheme} {width} {path}: errors={errs[:3]} failed_viz={fv} overflow={ov}px")
            await ctx.close()
        await b.close()
    print("pages with problems:", bad)

asyncio.run(main())
