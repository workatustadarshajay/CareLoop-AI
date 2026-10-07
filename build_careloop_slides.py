#!/usr/bin/env python3
"""Build the animated CareLoop AI slide show (guizang-ppt-skill, Swiss · IKB).

Route: the skill's template-swiss.html shell keeps all animation, presenter mode,
audience sync and WebGL/ASCII backgrounds; this script only swaps in the six
registered-layout pages, the deck title and the speaker notes.

Layouts used (all registered in references/swiss-layout-lock.md):
  S01 Index Cover · S04 Six Cells · S11 Horizontal Timeline · S22 Image Hero ·
  S15 Matrix + Hero Stat · S10 Split Closing
Every class used here was verified to exist in template-swiss.html's <style>.

Run from the repository root:
    python3 build_careloop_slides.py
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKILL = ROOT / ".agents/skills/guizang-ppt-skill"
TEMPLATE = SKILL / "assets/template-swiss.html"
LUCIDE = SKILL / "assets/lucide.min.js"
DECK_DIR = ROOT / "deck"
OUT = DECK_DIR / "index.html"
PLATE = (
    ROOT
    / ".archify/architecture-careloop-ai-20261007-092327/print"
    / "careloop-ai-architecture-slide.png"
)

TITLE = "CareLoop AI · note to closed loop"

SLIDES = """
<!-- ============================================================
     01 · S01 Index Cover · IKB full bleed + ASCII breathing field
     ============================================================ -->
<section class="slide accent" data-animate="statement" data-slide-id="cover" data-layout="S01">
  <div class="canvas-card">
    <canvas class="ascii-bg" aria-hidden="true"></canvas>
    <div class="chrome-min">
      <div class="l">CareLoop AI · UST Claude POC review · Team CareLoop AI</div>
      <div class="r">SS · 26.10.07 · 01 / 06</div>
    </div>

    <div style="flex:1;padding:0;display:grid;grid-template-rows:auto 1fr auto;gap:2.6vh">
      <div data-anim="kicker" class="t-meta" style="color:rgba(255,255,255,.78);letter-spacing:.22em">HEALTHCARE · AGENTIC CARE PLANS · MCP</div>

      <h1 data-anim="title" style="align-self:center;font-family:var(--sans),var(--sans-zh);font-weight:200;font-size:min(9.6vw,17vh);line-height:.94;letter-spacing:-.03em;color:#fff">Close the <span style="font-style:italic;font-weight:300">loop</span> on every doctor&rsquo;s note.</h1>

      <div data-anim="bottom" style="display:grid;grid-template-rows:auto auto;gap:1.6vh;border-top:1px solid rgba(255,255,255,.22);padding-top:2vh">
        <div data-anim="lead" class="lead" style="max-width:56ch;color:rgba(255,255,255,.86)">A note becomes typed care cards, the care nobody ordered gets flagged, blocked patients surface themselves, and AI agents act on the same records over MCP.</div>
        <div style="display:flex;justify-content:space-between;align-items:end">
          <div class="t-meta" style="color:rgba(255,255,255,.6)">Live demo · FastAPI · Postgres · Gemini · React 19</div>
          <div class="t-meta" style="color:rgba(255,255,255,.6)">→ swipe / arrow keys · P presenter · ESC overview</div>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- ============================================================
     02 · S04 Six Cells · the POC in six statements
     ============================================================ -->
<section class="slide" data-animate="grid-reveal" data-slide-id="overview" data-layout="S04">
  <div class="canvas-card">
    <div class="chrome-min">
      <div class="l">02 / 06 · POC overview</div>
      <div class="r">SIX CELLS · S04</div>
    </div>

    <div class="kicker accent">What it is</div>
    <h2 class="h-xl" data-anim="line" style="margin-bottom:2.4vh">The note <span class="underline-accent">is</span> the plan.</h2>

    <div class="sub-grid-3-2">
      <article class="sub-card">
        <span class="nb-corner">01</span>
        <i data-lucide="file-warning" class="lucide"></i>
        <div class="ttl">The problem</div>
        <p class="desc">Actionable lines sit inside prose. Ordering the MRI, starting the statin, chasing the referral &mdash; all of it lives in someone&rsquo;s memory.</p>
      </article>

      <article class="sub-card">
        <span class="nb-corner">02</span>
        <i data-lucide="list-checks" class="lucide"></i>
        <div class="ttl">What it does</div>
        <p class="desc">One pasted note becomes typed cards in Postgres &mdash; medication, test, referral, next_visit, general_task &mdash; with due dates read out of the note.</p>
      </article>

      <article class="sub-card accent">
        <span class="nb-corner">03</span>
        <i data-lucide="alert-triangle" class="lucide"></i>
        <div class="ttl">At-risk patients</div>
        <p class="desc">Cards carry dependencies. A card turns <strong>at_risk</strong> while its blocker is open, and heals itself the moment the blocker closes.</p>
      </article>

      <article class="sub-card">
        <span class="nb-corner">04</span>
        <i data-lucide="clipboard-check" class="lucide"></i>
        <div class="ttl">Care gaps</div>
        <p class="desc">A 28-diagnosis checklist asks the model which expected care items this note&rsquo;s cards miss, and offers them to the doctor to approve or dismiss.</p>
      </article>

      <article class="sub-card">
        <span class="nb-corner">05</span>
        <i data-lucide="plug" class="lucide"></i>
        <div class="ttl">Agent surface</div>
        <p class="desc">An MCP server exposes six <code>careloop_*</code> tools over REST, so any agent can read, flag and close the same cards a clinician sees.</p>
      </article>

      <article class="sub-card">
        <span class="nb-corner">06</span>
        <i data-lucide="unplug" class="lucide"></i>
        <div class="ttl">What is mocked</div>
        <p class="desc">No EHR or FHIR feed (notes are pasted), one shared demo password, no per-user MCP tokens, and triage results are not shown in the UI yet.</p>
      </article>
    </div>
  </div>
</section>

<!-- ============================================================
     03 · S11 Horizontal Timeline · paste to closure
     ============================================================ -->
<section class="slide dark" data-animate="timeline-walk" data-slide-id="how-it-works" data-layout="S11">
  <div class="canvas-card">
    <div class="chrome-min">
      <div class="l">03 / 06 · How it works</div>
      <div class="r">FIVE STEPS · ONE HUMAN</div>
    </div>

    <div class="kicker accent">From paste to closure</div>
    <h2 class="h-xl" data-anim="line" style="margin-bottom:4vh">Five steps. One human check.</h2>

    <div class="timeline-h">
      <div class="tl-row">
        <div class="th-node up">
          <span class="dot"></span>
          <span class="label">
            <span class="yr">01 · PASTE</span>
            <span class="name">Doctor pastes the note</span>
            <span class="desc">Up to 12,000 characters, saved in the same transaction as its cards.</span>
          </span>
        </div>
        <div class="th-node down">
          <span class="dot"></span>
          <span class="label">
            <span class="yr">02 · EXTRACT</span>
            <span class="name">Agent writes typed cards</span>
            <span class="desc">save_card once per item; close_card stores the phrase that proves it was done.</span>
          </span>
        </div>
        <div class="th-node up accent">
          <span class="dot"></span>
          <span class="label">
            <span class="yr">03 · RISK</span>
            <span class="name">Dependents turn at_risk</span>
            <span class="desc">Risk propagates through the dependency graph and clears when the blocker closes.</span>
          </span>
        </div>
        <div class="th-node down">
          <span class="dot"></span>
          <span class="label">
            <span class="yr">04 · GAPS</span>
            <span class="name">Care gaps are offered</span>
            <span class="desc">A coverage check flags missing items; the doctor approves or dismisses each one.</span>
          </span>
        </div>
        <div class="th-node up">
          <span class="dot"></span>
          <span class="label">
            <span class="yr">05 · ACT</span>
            <span class="name">Agents close the loop</span>
            <span class="desc">MCP clients read, flag and close the same cards &mdash; and must supply evidence.</span>
          </span>
        </div>
      </div>
    </div>

    <div class="t-meta" style="margin-top:3vh">Local router classifies patient-message urgency &mdash; no model call, no network</div>
  </div>
</section>

<!-- ============================================================
     04 · S22 Image Hero · the architecture, drawn from the code
     ============================================================ -->
<section class="slide" data-animate="image-hero" data-slide-id="architecture" data-layout="S22">
  <div class="canvas-card" style="padding:0;display:flex;flex-direction:column;overflow:hidden">
    <div data-anim="img" style="position:relative;flex:0 0 54%;overflow:hidden;background:var(--grey-1)">
      <img src="images/22-architecture.png" alt="CareLoop AI architecture: React app and Vite proxy, FastAPI API, note agent, Gemini, Postgres, MCP server with six careloop tools, and the UrgencyWatcher triage sidecar"
           loading="eager" style="position:absolute;inset:0;width:100%;height:100%;object-fit:contain;object-position:center center">
      <div class="chrome-min" style="position:absolute;top:0;left:0;right:0;padding:5.6vh 5vw 0;color:var(--text-helper)">
        <div class="l">04 / 06 · Architecture</div>
        <div class="r">S22 · SOURCED TO CODE</div>
      </div>
      <div data-anim="title-block" style="position:absolute;left:5vw;top:12vh;background:var(--paper);padding:2.4vh 2.4vw;max-width:34vw">
        <div style="font-family:var(--sans),var(--sans-zh);font-weight:200;font-size:min(4vw,7vh);line-height:1;letter-spacing:-.035em;color:var(--text-primary)">
          Four<br>subsystems
        </div>
      </div>
    </div>

    <div data-anim="kpi" class="image-hero-body">
      <div style="max-width:46ch;font-family:var(--sans),var(--sans-zh);font-size:max(15px,1.15vw);line-height:1.55;font-weight:400;color:var(--text-primary)">
        The React app talks only to Vite, which proxies <code>/api/*</code> to FastAPI. The note agent is the only writer of cards, Gemini is the only model,
        Postgres holds the state, the MCP server is a pure REST client with no database credentials, and UrgencyWatcher files triage results into its own schema.
        <span class="body-sm" style="display:block;margin-top:1.2vh">Open the interactive version: the same diagram, clickable, in the project docs.</span>
      </div>
      <div class="image-hero-stats" style="gap:3vw">
        <div style="display:flex;flex-direction:column;gap:.6vh"><div style="height:1px;background:var(--ink)"></div><div class="t-meta">Components</div><div style="font-family:var(--sans);font-weight:200;font-size:min(4.6vw,7.6vh);line-height:.95;letter-spacing:-.04em">14</div><div style="height:1px;background:var(--border-subtle);margin-top:auto"></div><p class="body-sm">Every node carries the file and line that proves it</p></div>
        <div style="display:flex;flex-direction:column;gap:.6vh"><div style="height:1px;background:var(--ink)"></div><div class="t-meta">MCP tools</div><div style="font-family:var(--sans);font-weight:200;font-size:min(4.6vw,7.6vh);line-height:.95;letter-spacing:-.04em">6</div><div style="height:1px;background:var(--border-subtle);margin-top:auto"></div><p class="body-sm">list_patients, list_cards, get_card, close_card, flag_card_risk, list_notes</p></div>
        <div style="display:flex;flex-direction:column;gap:.6vh"><div style="height:1px;background:var(--accent)"></div><div class="t-meta">Direct DB access</div><div style="font-family:var(--sans);font-weight:200;font-size:min(4.6vw,7.6vh);line-height:.95;letter-spacing:-.04em;color:var(--accent)">0</div><div style="height:1px;background:var(--border-subtle);margin-top:auto"></div><p class="body-sm">Agents act through the API, never through the database</p></div>
      </div>
    </div>
  </div>
</section>

<!-- ============================================================
     05 · S15 Matrix + Hero Stat · what the running demo proves
     ============================================================ -->
<section class="slide" data-animate="four-cards" data-slide-id="proof" data-layout="S15">
  <div class="canvas-card">
    <div class="chrome-min">
      <div class="l">05 / 06 · Evidence</div>
      <div class="r">MEASURED ON THE DEMO · 07.10.26</div>
    </div>

    <div class="kicker accent">Not a benchmark</div>
    <h2 class="h-xl" data-anim="line" style="margin-bottom:1.6vh">What the running demo proves.</h2>

    <div class="grid-6" data-anim="up" style="margin-top:1vh">
      <div class="stat-card accent-top">
        <span class="stat-label">Notes processed</span>
        <span class="stat-nb">24</span>
        <span class="stat-note">Real notes through the agent, end to end</span>
      </div>
      <div class="stat-card accent-top">
        <span class="stat-label">Cards saved</span>
        <span class="stat-nb">63</span>
        <span class="stat-note">Typed, due-dated, listed in the UI</span>
      </div>
      <div class="stat-card accent-top">
        <span class="stat-label">Recommendations</span>
        <span class="stat-nb">21</span>
        <span class="stat-note">Care gaps a doctor approved or dismissed</span>
      </div>
      <div class="stat-card accent-top">
        <span class="stat-label">Messages triaged</span>
        <span class="stat-nb">98</span>
        <span class="stat-note">26 urgent, 72 not urgent, none lost</span>
      </div>
      <div class="stat-card accent-top">
        <span class="stat-label">Closed with evidence</span>
        <span class="stat-nb">9</span>
        <span class="stat-note">Cards closed only when the note confirmed it</span>
      </div>
      <div class="stat-card accent-top">
        <span class="stat-label">MCP test suite</span>
        <span class="stat-nb">5<span class="stat-unit">/ 5</span></span>
        <span class="stat-note">Close-card flow, risk flags, tool plumbing</span>
      </div>
    </div>

    <div style="display:flex;justify-content:space-between;align-items:end;border-top:1px solid var(--border-subtle);padding-top:2.4vh;margin-top:2.4vh">
      <div class="lead" style="max-width:54ch;text-align:left">Every number above is a row you can query in the demo database &mdash; and one dependent card is sitting at_risk because its blocker is genuinely open.</div>
      <div class="t-meta">pytest mcp · 5 passed · 0 failed</div>
    </div>
  </div>
</section>

<!-- ============================================================
     06 · S10 Split Closing · questions for the reviewers
     ============================================================ -->
<section class="slide split" data-animate="split-statement" data-slide-id="closing" data-layout="S10">
  <div class="canvas-card">
    <div class="split-half">
      <div class="half b-accent" style="padding:5.6vh 3.6vw 4.4vh;justify-content:space-between;position:relative;overflow:hidden">
        <canvas class="ascii-bg" aria-hidden="true"></canvas>
        <div class="chrome-min" style="margin-bottom:0;position:relative;z-index:1">
          <div class="l">06 / 06</div>
          <div class="r">CLOSING</div>
        </div>

        <div data-anim="manifesto" style="display:flex;flex-direction:column;gap:2vh;position:relative;z-index:1">
          <div class="t-meta" style="color:rgba(255,255,255,.78);letter-spacing:.22em;margin-bottom:1.6vh">QUESTIONS FOR ANTHROPIC</div>
          <h2 style="font-family:var(--sans),var(--sans-zh);font-size:min(6.4vw,11.5vh);line-height:.94;letter-spacing:-.025em;font-weight:200;color:#fff">Close the loop.<br>Then <span style="font-style:italic;font-weight:300">keep it</span> closed.</h2>
          <div style="font-family:var(--sans),var(--sans-zh);font-size:max(14px,1vw);line-height:1.6;color:rgba(255,255,255,.82);font-weight:400;max-width:38ch;margin-top:1.4vh">The demo closes cards, flags risk and answers over MCP. What we do not know yet is how much of that a model should be allowed to do alone.</div>
        </div>

        <div data-anim="signature" style="display:flex;justify-content:space-between;align-items:end;border-top:1px solid rgba(255,255,255,.22);padding-top:2vh;position:relative;z-index:1">
          <div class="t-meta" style="color:rgba(255,255,255,.62)">Team CareLoop AI</div>
          <div class="t-meta" style="color:rgba(255,255,255,.62)">26.10.07</div>
        </div>
      </div>

      <div class="half" style="padding:5.6vh 3.6vw 4.4vh;justify-content:space-between">
        <div class="chrome-min">
          <div class="l">Three questions</div>
          <div class="r">SHAPE · PERMISSIONS · AUDIT</div>
        </div>

        <ul class="takeaway-list" style="display:flex;flex-direction:column;gap:0;list-style:none;margin:0;padding:0">
          <li style="display:grid;grid-template-columns:auto 1fr;gap:1.6vw;align-items:start;padding:2.4vh 0;border-top:1px solid var(--border-subtle)">
            <div style="font-family:var(--sans);font-weight:200;font-size:min(3.6vw,6.4vh);line-height:.9;color:var(--text-primary)">Q1</div>
            <div>
              <h3 style="font-family:var(--sans),var(--sans-zh);font-weight:400;font-size:max(17px,1.55vw);line-height:1.2;letter-spacing:-.015em;color:var(--text-primary);margin-bottom:1vh">One agent, or an extractor plus a model?</h3>
              <p style="font-family:var(--sans),var(--sans-zh);font-size:max(15px,.9vw);line-height:1.55;color:var(--text-secondary)">Today a single tool-calling agent decides what is actionable and writes every card. Would you keep that, or hand extraction to deterministic code and use the model only for judgement and phrasing?</p>
            </div>
          </li>
          <li style="display:grid;grid-template-columns:auto 1fr;gap:1.6vw;align-items:start;padding:2.4vh 0;border-top:1px solid var(--border-subtle)">
            <div style="font-family:var(--sans);font-weight:200;font-size:min(3.6vw,6.4vh);line-height:.9;color:var(--text-primary)">Q2</div>
            <div>
              <h3 style="font-family:var(--sans),var(--sans-zh);font-weight:400;font-size:max(17px,1.55vw);line-height:1.2;letter-spacing:-.015em;color:var(--text-primary);margin-bottom:1vh">May an agent close a clinical card?</h3>
              <p style="font-family:var(--sans),var(--sans-zh);font-size:max(15px,.9vw);line-height:1.55;color:var(--text-secondary)">Our MCP tools can close and flag cards. What is the safest permission shape for a clinical server &mdash; scoped tools, an approval step, or human-only closure?</p>
            </div>
          </li>
          <li style="display:grid;grid-template-columns:auto 1fr;gap:1.6vw;align-items:start;padding:2.4vh 0;border-top:1px solid var(--border-subtle);border-bottom:2px solid var(--accent)">
            <div style="font-family:var(--sans);font-weight:200;font-size:min(3.6vw,6.4vh);line-height:.9;color:var(--accent)">Q3</div>
            <div>
              <h3 style="font-family:var(--sans),var(--sans-zh);font-weight:400;font-size:max(17px,1.55vw);line-height:1.2;letter-spacing:-.015em;color:var(--accent);margin-bottom:1vh">How would you make care-gap reasoning auditable?</h3>
              <p style="font-family:var(--sans),var(--sans-zh);font-size:max(15px,.9vw);line-height:1.55;color:var(--text-secondary)">Which features would you reach for &mdash; citations back to the note, structured outputs, or an eval harness on the checklist?</p>
            </div>
          </li>
        </ul>

        <div data-anim="foot" class="t-meta" style="color:var(--text-helper);text-align:right">→ 完 · END OF FIELD NOTE</div>
      </div>
    </div>
  </div>
</section>
"""

NOTES = """const SPEAKER_NOTES = [
  {
    id: 'cover', title: 'CareLoop AI — note to closed loop', section: '开场', minutes: 0.8,
    purpose: 'Establish the one-line promise and the shape of the demo',
    talk: [
      'Open on the sentence, not the stack: a note goes in, a closed loop comes out.',
      'Say what the loop means: typed cards, care gaps, at-risk patients, and agents that act on the same records.',
      'Name the four pieces once — web app, API and agent, Postgres, MCP — and promise the architecture slide.'
    ],
    transition: 'Move from the promise into the six facts that explain it', cue: 'Pause, confirm the audience screen is synced'
  },
  {
    id: 'overview', title: 'The note is the plan', section: '概览', minutes: 2.5,
    purpose: 'Explain the idea, what works today, and what is still mocked',
    talk: [
      'Start with the problem in the clinician’s words: the plan exists, it is just buried in prose.',
      'Card 02 is the core mechanic — one save_card call per item, five types, due dates read from the note.',
      'Card 03 is the part people remember: dependents go at_risk on their own and heal when the blocker closes.',
      'Card 04: the checklist has 28 diagnoses and the coverage test is a second model call.',
      'Be honest on card 06 — no EHR feed, shared demo password, triage not surfaced yet.'
    ],
    transition: 'Turn the six facts into the five steps of the pipeline', cue: 'Point at the accent card when you say at_risk'
  },
  {
    id: 'how-it-works', title: 'Five steps, one human check', section: '流程', minutes: 2.5,
    purpose: 'Walk the pipeline and show where a person stays in charge',
    talk: [
      'Walk the axis left to right; each step is one sentence.',
      'Step 02 is where the model writes, and it can only call save_card and close_card.',
      'Step 03 is the differentiator: risk is derived from the dependency graph, not from a prompt.',
      'Step 04 is the human check — the doctor approves or dismisses every recommendation.',
      'Step 05 is the agent surface: six MCP tools over REST, with no database credentials.'
    ],
    transition: 'Show the whole system on one diagram', cue: 'Slow down at step 04 — this is the safety story'
  },
  {
    id: 'architecture', title: 'Four subsystems', section: '架构', minutes: 2,
    purpose: 'Prove the diagram is the real system, not a sketch',
    talk: [
      'Read the diagram as data flow: browser to Vite to FastAPI to Postgres, with the agent as the only card writer.',
      'The MCP server is a client of our own API, so an agent gets exactly the permissions the clinician has.',
      'UrgencyWatcher is the sidecar: it triages messages with a local model and writes to its own schema.',
      'Offer the interactive version — the same picture with every node traceable to a file and line.'
    ],
    transition: 'Back the picture with numbers from the running demo', cue: 'Mention the accent metric: zero direct database access'
  },
  {
    id: 'proof', title: 'What the running demo proves', section: '证据', minutes: 2,
    purpose: 'Give reviewers countable evidence and the honest limits',
    talk: [
      'State the source: these are rows in the demo database on 7 October, not a benchmark.',
      'Lead with 24 notes and 63 cards, then 21 recommendations a doctor acted on.',
      '98 triaged messages shows the sidecar works; 5 of 5 tests passing is the only green build claim.',
      'Say the limit out loud: no formal eval harness yet, and the tests cover the MCP client.'
    ],
    transition: 'Close by asking for the decisions we cannot make alone', cue: 'Do not rush the numbers — reviewers write them down'
  },
  {
    id: 'closing', title: 'Questions for Anthropic', section: '收束', minutes: 1.5,
    purpose: 'Leave with three specific questions and a clear closing line',
    talk: [
      'Ask Q1 first — it is a design question about where the model belongs.',
      'Q2 is the one we most want an answer to: who is allowed to close a clinical card.',
      'Q3 asks for the audit tooling you would choose, and why.',
      'Finish on the line: close the loop, then keep it closed.'
    ],
    transition: 'Stop talking and open the floor', cue: 'Pause two seconds, then thank the reviewers'
  }
];
"""


def main() -> None:
    html = TEMPLATE.read_text(encoding="utf-8")

    # 1. deck title
    html = html.replace(
        "<title>[必填] 替换为 PPT 标题 · Deck Title</title>",
        f"<title>{TITLE}</title>",
    )

    # 2. swap the two示例 pages for the six registered-layout pages
    start = html.index("<!-- ============ 示例:第 1 页")
    end = html.index("</div>\n\n<div id=\"nav\">")
    html = html[:start] + SLIDES.strip() + "\n\n" + html[end:]

    # 3. speaker notes, keyed by data-slide-id
    notes_start = html.index("const SPEAKER_NOTES = [")
    notes_end = html.index("window.__SPEAKER_NOTES__ = SPEAKER_NOTES;")
    html = html[:notes_start] + NOTES + html[notes_end:]

    # 4. icons: swap the unpkg CDN tag for the vendored copy, so the deck renders
    #    its icons with no network (headless checks, offline review, GitHub Pages).
    cdn_icons = (
        '<script src="https://unpkg.com/lucide@latest/dist/umd/lucide.min.js"></script>\n'
        "<script>lucide.createIcons();</script>"
    )
    local_icons = (
        "<!-- Lucide vendored locally: icons must render with no network -->\n"
        '<script src="./assets/lucide.min.js"></script>\n'
        "<script>if(window.lucide&&window.lucide.createIcons)window.lucide.createIcons();</script>"
    )
    if cdn_icons not in html:
        raise SystemExit("lucide CDN tag not found — template changed, update this patch")
    html = html.replace(cdn_icons, local_icons)

    DECK_DIR.mkdir(exist_ok=True)
    (DECK_DIR / "images").mkdir(exist_ok=True)
    (DECK_DIR / "assets").mkdir(exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    # the template imports ./assets/motion.min.js with a CDN fallback next to it
    shutil.copy2(SKILL / "assets/motion.min.js", DECK_DIR / "assets/motion.min.js")
    shutil.copy2(LUCIDE, DECK_DIR / "assets/lucide.min.js")
    shutil.copy2(PLATE, DECK_DIR / "images/22-architecture.png")

    slides = re.findall(r'<section class="slide[^"]*"[^>]*data-slide-id="([^"]+)"', html)
    layouts = re.findall(r'data-layout="(S\d+)"', html)
    recipes = re.findall(r'data-animate="([^"]+)"', html)
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")
    print(f"  slides  : {len(slides)} -> {slides}")
    print(f"  layouts : {layouts}")
    print(f"  recipes : {recipes}")
    leftover = re.findall(r"\[必填\][^<]{0,40}", html)
    print(f"  leftover placeholders: {len(leftover)} {leftover[:3]}")


if __name__ == "__main__":
    main()
