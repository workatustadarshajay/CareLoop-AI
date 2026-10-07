#!/usr/bin/env python3
"""Assemble the GitHub Pages site under docs/ (MkDocs).

Sources of truth, never hand-edited here:
  * the interactive architecture diagram produced by archify
        .archify/architecture-careloop-ai-<stamp>/careloop-ai-architecture.html
  * the 2x plate rendered by archify  (CareLoop_AI_architecture.png)
  * the animated review deck          (deck/)

The generated .md pages are written from this script so the site and the deck
cannot drift apart. Run from the repository root:

    python3 build_docs_site.py          # assemble docs/
    mkdocs build                        # -> site/

Publishing is deliberately NOT part of this script; see docs/publishing.md.
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
ARCHIFY = ROOT / ".archify"
DECK = ROOT / "deck"
PLATE = ROOT / "CareLoop_AI_architecture.png"

# The archify run directory is timestamped; take the newest one that has an HTML page.
DIAGRAM_CANDIDATES = sorted(
    p for p in ARCHIFY.glob("architecture-careloop-ai-*") if (p / "careloop-ai-architecture.html").is_file()
)

INDEX_MD = """# CareLoop AI

**Healthcare Commitment Intelligence & Closed-Loop Care** — from a doctor&rsquo;s word
to a verified outcome.

This site publishes the artefacts behind the CareLoop AI POC review. They are all
generated from the same repository revision, so the diagram, the numbers and the
deck describe one system.

## Start here

<div class="grid cards" markdown>

-   **[Interactive architecture](architecture.html)**

    ---

    The whole system as one clickable diagram. Every node carries the file and
    line that proves it, and it renders in both light and dark mode.

-   **[Architecture notes](architecture-notes.md)**

    ---

    The same system in words: four subsystems, where each one ends, and the
    honest limits of the POC.

-   **[Animated slideshow](slides/index.html)**

    ---

    The six-slide review deck. Arrow keys advance, `P` opens presenter mode with
    speaker notes, `ESC` shows the slide index.

-   **[Static plate (2× PNG)](images/careloop-ai-architecture-plate.png)**

    ---

    The same diagram as a print-ready raster, for slides and documents.

</div>

## What the demo does

A doctor pastes a note. One agent writes typed care cards — medication, test,
referral, next visit, general task — with due dates read straight out of the note.
Cards carry dependencies, so a card whose blocker is still open turns **at_risk**
on its own and heals the moment the blocker closes. A 28-diagnosis checklist asks
the model which expected items this note&rsquo;s cards miss, and offers them to the
doctor to approve or dismiss. An MCP server exposes the same records to agents
over six `careloop_*` tools, with no database credentials.

## Verified on the demo database

| Measure | Value |
| --- | --- |
| Notes processed end to end | 24 |
| Cards saved | 63 |
| Care-gap recommendations acted on | 21 |
| Cards closed with evidence | 9 |
| Patient messages triaged | 98 (26 urgent, 72 not urgent) |
| Urgent-item worst-case wait | 10 s (watcher poll interval) |
| MCP client test suite | 5 passed |

Counted directly from the demo Postgres volume on 7 October 2026. These are rows
you can query, not a benchmark.

## Honest limits

No EHR or FHIR feed — notes are pasted by hand. One shared demo password, no
per-user tokens on the MCP server. Urgency triage results are written to their own
schema but are not surfaced in the UI yet. There is no formal eval harness; the
five passing tests cover the MCP client, not the model.
"""

ARCHITECTURE_MD = """# Architecture

Four subsystems, one shared Postgres, and no component that a reviewer has to take
on faith.

## The shape of it

| Layer | What it is | Where it lives |
| --- | --- | --- |
| **React app** | What people actually see and use: patient and doctor/admin views over the same records, role-filtered | `Frontend/` (React 19 + Vite) |
| **API layer** | The rulebook every request passes through: auth, notes, cards, dependencies, care gaps | `Backend/app/main.py` (FastAPI) |
| **Note agent** | The only writer of cards. Reads a note, decides what is actionable, calls `save_card` / `close_card` | `Backend/app/agents/note_agent.py` |
| **Postgres** | One source of truth. Dependencies are just rows linking one card to another — no separate graph database | `docker-compose.yml` |
| **MCP server** | A pure REST client of our own API, so an agent gets exactly the permissions a clinician has | `mcp/server.py` |
| **UrgencyWatcher** | A sidecar that polls a watch directory and files triage results into its own schema | `UrgencyWatcher/watcher.py` |

## Data flow

```
browser ──/api/*──► Vite (dev proxy) ──► FastAPI :8000 ──► Postgres :5432
                                            │
                                            ├─► Gemini          (note extraction, care-gap check)
                                            ├─► MCP server :8100 (six careloop_* tools, REST only)
                                            └─► UrgencyWatcher   (10 s poll, own schema, no UI yet)
```

The React app talks only to Vite, which proxies `/api/*` to FastAPI. The note
agent is the only writer of cards. Gemini is the only model. The MCP server holds
no database credentials at all.

## Where the loop is closed

`close_card(card_id, evidence)` requires the phrase that proves the step happened.
Once a blocker closes, `propagate_risk_updates` re-evaluates everything that was
waiting on it, so the graph heals without anyone remembering to follow up.

## Honest limits

- No EHR or FHIR integration: a human pastes the note.
- One shared demo password (PBKDF2-SHA256, 100k iterations) and no per-user MCP tokens.
- Care-gap coverage uses a second model call; there is no eval harness behind it.
- Triage results exist in the database only — no UI surfaces them yet.
"""

PUBLISHING_MD = """# Publishing this site

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
`docs/`, `deck/` or the workflow republishes the site.

**Route B — `mkdocs gh-deploy` (branch-based).**

```bash
mkdocs gh-deploy --force
```

This **force-pushes** the `gh-pages` branch: anything else on that branch is
destroyed silently. Set Pages to *Source: Deploy from a branch → gh-pages*.

Either way the site lands at <https://workatustadarshajay.github.io/CareLoop-AI/>.
"""

MKDOCS_YML = """site_name: CareLoop AI — POC review
site_description: Healthcare Commitment Intelligence & Closed-Loop Care
site_url: https://workatustadarshajay.github.io/CareLoop-AI/
repo_url: https://github.com/workatustadarshajay/CareLoop-AI
repo_name: workatustadarshajay/CareLoop-AI
docs_dir: docs
site_dir: site
# False keeps every link predictable: page.md -> page.html, and the generated
# architecture.html / slides/index.html stay at the paths the deck links to.
use_directory_urls: false
theme:
  name: material
  palette:
    - media: "(prefers-color-scheme: light)"
      scheme: default
      primary: teal
      accent: teal
      toggle:
        icon: material/weather-night
        name: Switch to dark mode
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      primary: teal
      accent: cyan
      toggle:
        icon: material/weather-sunny
        name: Switch to light mode
  features:
    - navigation.instant
    - navigation.top
    - navigation.tracking
    - content.code.copy
    - search.suggest
    - toc.follow
  icon:
    repo: fontawesome/brands/github
markdown_extensions:
  - admonition
  - attr_list
  - md_in_html
  - tables
  - toc:
      permalink: true
      permalink_title: Link to this section
  - pymdownx.details
  - pymdownx.superfences
  - pymdownx.highlight
  - pymdownx.inlinehilite
nav:
  - Home: index.md
  - Architecture: architecture-notes.md
  - Interactive diagram: architecture.html
  - Animated slideshow: slides/index.html
  - Publishing: publishing.md
extra:
  generator: false
copyright: CareLoop AI — UST Claude POC review, 7 October 2026
"""

WORKFLOW_YML = """name: Publish site

# Publishes docs/ to GitHub Pages with the official Pages actions.
# One-time setup: Settings -> Pages -> Source = "GitHub Actions".
on:
  push:
    branches: [main]
    paths:
      - 'docs/**'
      - 'deck/**'
      - 'mkdocs.yml'
      - 'build_docs_site.py'
      - '.github/workflows/pages.yml'
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install MkDocs
        run: pip install "mkdocs-material==9.*"
      - name: Refresh docs/ from the diagram, plate and deck (when present)
        run: |
          if [ -d .archify ] && [ -f deck/index.html ]; then
            python3 build_docs_site.py
          else
            echo 'archify output or deck/ not committed - using the committed docs/'
          fi
      - name: Build site
        run: mkdocs build --strict
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: site

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
"""


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    if not DIAGRAM_CANDIDATES:
        raise SystemExit("no archify architecture HTML found under .archify/ — run archify first")
    diagram = DIAGRAM_CANDIDATES[-1] / "careloop-ai-architecture.html"
    if not DECK.joinpath("index.html").is_file():
        raise SystemExit("deck/index.html missing — run python3 build_careloop_slides.py first")
    if not PLATE.is_file():
        raise SystemExit("CareLoop_AI_architecture.png missing at repository root")

    # .md pages are generated, so re-create them every run.
    write(DOCS / "index.md", INDEX_MD)
    write(DOCS / "architecture-notes.md", ARCHITECTURE_MD)
    write(DOCS / "publishing.md", PUBLISHING_MD)

    # verbatim artefacts
    (DOCS / "images").mkdir(parents=True, exist_ok=True)
    shutil.copy2(diagram, DOCS / "architecture.html")
    shutil.copy2(PLATE, DOCS / "images/careloop-ai-architecture-plate.png")

    # the deck keeps its own relative asset paths, so copy it whole
    deck_out = DOCS / "slides"
    if deck_out.exists():
        shutil.rmtree(deck_out)
    shutil.copytree(DECK, deck_out, ignore=shutil.ignore_patterns("__probe.html"))

    # Keep GitHub Pages from running Jekyll over the site.
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")

    write(ROOT / "mkdocs.yml", MKDOCS_YML)
    write(ROOT / ".github/workflows/pages.yml", WORKFLOW_YML)

    files = sorted(p for p in DOCS.rglob("*") if p.is_file())
    total = sum(p.stat().st_size for p in files)
    print(f"docs/ from   {diagram.relative_to(ROOT)}")
    print(f"             {PLATE.name}, deck/ -> docs/slides/")
    print(f"docs/ files  {len(files)}  ({total / 1024 / 1024:.2f} MB)")
    for p in files:
        print(f"  {p.relative_to(ROOT)}  {p.stat().st_size // 1024} KB")
    print("wrote mkdocs.yml, .github/workflows/pages.yml")
    print("next: mkdocs build   (publishing is described in PUBLISHING.md)")


if __name__ == "__main__":
    main()
