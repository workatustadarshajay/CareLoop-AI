# Publishing this site

The site is built from `docs/` and deployed with GitHub Actions (or MkDocs'
`gh-deploy`). Nothing is published automatically until you choose one.

## 1. Build it locally

```bash
python3 build_docs_site.py      # refresh docs/ from the diagram, the plate and deck/
mkdocs build                    # -> site/   (add --strict to fail on warnings)
mkdocs serve                    # preview at http://127.0.0.1:8000
```

MkDocs is not a project dependency; it is only needed to publish. Install it with
`uv run --with mkdocs-material mkdocs build` or `pip install mkdocs-material`.

## 2. Pick one deployment route

**Route A — GitHub Actions (no force-push, keeps history).**

`.github/workflows/pages.yml` is already in the repository. Once Pages is set to
*Source: GitHub Actions* in **Settings → Pages**, every push to `main` that touches
`docs/`, `deck/`, `promo/` or the workflow republishes the site. The independent
promotional landing page is published at `/promo/`; it does not use the React app.

**Route B — `mkdocs gh-deploy` (branch-based).**

```bash
mkdocs gh-deploy --force
```

This **force-pushes** the `gh-pages` branch: anything else on that branch is
destroyed silently. Set Pages to *Source: Deploy from a branch → gh-pages*.

Either way the site lands at <https://workatustadarshajay.github.io/CareLoop-AI/>.
