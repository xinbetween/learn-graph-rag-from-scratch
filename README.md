# Graph RAG from Scratch

A self-paced course website that teaches engineers to build graph retrieval-augmented generation from first principles.

- `site/` — the static website (no build step). Open `site/index.html` through any static server:
  `python3 tools/serve.py` (a no-cache server) then visit http://localhost:8765/
- `code/` — `minigraphrag`, the Python reference implementation the chapters build step by step. Runs offline with a mock LLM.
- `docs/running-example.md` — the fictional Kestrel Labs world used by every example.
- `docs/AUTHORING.md` — how chapters are written: markup, visualization configs, style and accuracy rules.
- `tools/stamp_assets.py` — adds `?v=<hash>` to CSS/JS links; run after editing `site/assets/`.
- `tools/check_site.py` — static checks (required sections, visualization JSON, internal links).
- `tools/render_check.py` — loads every page in Chromium (light, dark, phone width), clicks through all visualizations, reports JS errors and horizontal overflow. Needs the local server on port 8765 and Python Playwright.

Reference code: `cd code && python3 -m venv .venv && .venv/bin/pip install -e ".[dev]" && .venv/bin/pytest -q`

## Course outline

0. Start here · 1. Foundations · 2. Building the graph · 3. Retrieval · 4. Generation · 5. Evaluation and production ·
6. Frontiers · 7. Capstones · Appendices (glossary, paper and tool library). The structure lives in
`site/assets/js/curriculum.js`.

## Deploying

The site is published to https://graphrag.xinbetween.com by GitHub Pages.

- `.github/workflows/deploy.yml` runs on every push to `main`: it checks the site, copies `site/` into a Pages
  artifact with `.nojekyll`, and deploys it through the `github-pages` environment. There is no build step;
  `site/` is the published output, and all internal links are relative.
- `site/CNAME` holds the custom domain so it survives every deploy.
- `.github/workflows/ci.yml` runs on pushes and pull requests: the `minigraphrag` test suite, the site structure
  and link checks, a check that asset `?v=` stamps are current, and a Chromium render of every page.

One-time repository setup: in Settings → Pages, set the source to "GitHub Actions" and the custom domain to
`graphrag.xinbetween.com`, then enable "Enforce HTTPS" once the certificate is issued. DNS needs a `CNAME`
record from `graphrag` to `xinbetween.github.io`.
