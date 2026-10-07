# CareLoop AI

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
