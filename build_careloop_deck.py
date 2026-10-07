#!/usr/bin/env python3
"""Fill the shared UST Claude POC review template with CareLoop AI content.

Route: ppt-master "Edit Native PPTX" (fill a raw template, keep its design).
Every edit is in place: text runs keep their original paragraph formatting,
the slide count stays 6, and the template's slide masters/layouts are untouched.

Run from the repository root:
    cd Backend && uv run --system-certs --with python-pptx python ../build_careloop_deck.py
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Emu
from lxml import etree

A = "http://schemas.openxmlformats.org/drawingml/2006/main"
ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "UST_Claude_Hackathon_Review_Final Template.pptx"
OUTPUT = ROOT / "UST_CareLoop_AI_POC_Review.pptx"
PLATE = (
    ROOT
    / ".archify/architecture-careloop-ai-20261007-092327/print"
    / "careloop-ai-architecture-slide.png"
)

USED = RGBColor(0x00, 0x6E, 0x74)  # the template's "Used" legend swatch
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

# (slide number, shape name, [(paragraph index whose style to copy, text), ...])
CONTENT: list[tuple[int, str, list[tuple[int, str]]]] = [
    # ---------------------------------------------------------------- slide 1
    (1, "Title 1", [(0, "CareLoop AI")]),
    (1, "Subtitle 2", [(0, "Claude POC review for Anthropic")]),
    (1, "Text Placeholder 3", [(0, "Team CareLoop AI"), (1, "7 October 2026")]),
    # ---------------------------------------------------------------- slide 2
    (2, "Rectangle 4", [(0, "Team: CareLoop AI   |   POC: CareLoop AI")]),
    (
        2,
        "Rectangle 6",
        [
            (0, "1.1  The idea"),
            (
                1,
                "Clinicians write notes as prose. The actionable parts \u2014 order the MRI, "
                "refer to neurology, start a statin \u2014 sit inside free text, so follow-up "
                "depends on memory and hand-chasing. Nothing checks whether the plan is "
                "complete, and nothing flags the patient waiting on a blocked step.",
            ),
            (
                2,
                "Example: \u201cMRI brain, routine\u201d in Tuesday\u2019s note only becomes a "
                "tracked task if someone retypes it.",
            ),
        ],
    ),
    (
        2,
        "Rectangle 7",
        [
            (0, "1.2  What the POC does"),
            (
                1,
                "Paste a doctor\u2019s note in the React app: a Gemini tool-calling agent saves "
                "each actionable item as a typed card in Postgres, a 28-condition checklist flags "
                "missed care, dependent cards turn at_risk, and MCP agents can close the loop.",
            ),
            (2, "Example: one note produced 3 cards (medication, test, next_visit) and 2 care-gap recommendations."),
        ],
    ),
    (2, "TextBox 8", [(0, "1.3  What is working versus mocked")]),
    (
        2,
        "Rectangle 9",
        [
            (0, "WORKING"),
            (1, "Note \u2192 typed cards via save_card / close_card (five card types)"),
            (1, "Care-gap recommendations from a 28-diagnosis checklist"),
            (1, "Dependency-driven at_risk, healed when the blocker closes"),
            (1, "MCP server (6 tools), urgency triage, reminders, plain language"),
        ],
    ),
    (
        2,
        "Rectangle 10",
        [
            (0, "MOCKED OR PLANNED"),
            (1, "No EHR or FHIR feed: notes are pasted, the inbox is a watched folder"),
            (1, "Demo accounts share one password; no per-user MCP tokens yet"),
            (2, "Triage results stored in urgency.messages but not shown in the UI"),
        ],
    ),
    (2, "TextBox 11", [(0, "1.4  Market analysis")]),
    (
        2,
        "Rectangle 12",
        [
            (0, "Geographic relevance and market size"),
            (
                1,
                "Regions: US and EU, where value-based care and audit rules make closed-loop "
                "follow-up a paid requirement. North America is the largest AI care-coordination "
                "market and APAC the fastest growing (Mordor Intelligence, 2026).",
            ),
            (
                2,
                "Example: chronic-care management billing needs evidence that every ordered test was followed up.",
            ),
            (
                4,
                "Approx. market size: USD 2.15 bn in 2026, rising to USD 6.24 bn by 2031. "
                "Source: Mordor Intelligence, AI-Based Care Coordination Market, 2026",
            ),
            (
                5,
                "Expected growth: 23.79% CAGR, 2026\u20132031. Source: Mordor Intelligence, 2026 "
                "(vendor forecast \u2014 an estimate, not a neutral measurement)",
            ),
            (
                7,
                "Our own bottom-up sizing, and every figure we derived ourselves, is marked as an estimate.",
            ),
        ],
    ),
    (
        2,
        "Rectangle 13",
        [
            (0, "Target customers"),
            (
                1,
                "Ambulatory and specialist clinics with 10\u2013200 clinicians and high note volumes; "
                "bought by clinical leadership, used daily by doctors, nurses and the follow-up desk.",
            ),
            (2, "Example: a 40-doctor multi-specialty clinic chasing 300+ open follow-ups a month."),
        ],
    ),
    # ---------------------------------------------------------------- slide 3
    (3, "Title 1", [(0, "02  The model\u2019s role and architecture")]),
    (
        3,
        "TextBox 3",
        [(0, "Show what the model does, which features we used, and how the parts connect")],
    ),
    (3, "Rectangle 4", [(0, "Team: CareLoop AI   |   POC: CareLoop AI")]),
    (3, "TextBox 6", [(0, "2.1  What the model does versus what code does")]),
    (
        3,
        "Rectangle 7",
        [
            (0, "GEMINI DOES"),
            (1, "Reads the note and decides what is actionable, and each item\u2019s type"),
            (1, "Writes card text and due dates, and spots the follow-up that closes a card"),
            (1, "Judges which expected care items the cards cover"),
        ],
    ),
    (
        3,
        "Rectangle 8",
        [
            (0, "CODE DOES"),
            (1, "Validates and persists cards in one transaction; no SQL from the model"),
            (1, "Dependency graph, at_risk, reminders, auth, checklist matching"),
            (1, "Urgency triage runs locally on the laya router, with no LLM call"),
        ],
    ),
    (3, "TextBox 9", [(0, "2.2  Model features used (shade each cell)")]),
    (
        3,
        "Rectangle 28",
        [(1, "2.3  Architecture diagram")],
    ),
    (
        3,
        "Rectangle 29",
        [
            (0, "2.4  Models and access"),
            (
                1,
                "Gemini 3.8 Flash (gemini-3.8-flash) does note extraction, the tool calls, coverage "
                "checks and plain-language rewrites, called through the Gemini API with LangChain.",
            ),
            (
                2,
                "The laya router (PyTorch on CPU) classifies patient-message urgency on the machine. "
                "This build runs on Gemini, so the template\u2019s Claude-specific rows above are mapped "
                "to the capability we actually used.",
            ),
        ],
    ),
    # ---------------------------------------------------------------- slide 4
    (4, "Title 1", [(0, "03  How it works")]),
    (
        4,
        "TextBox 3",
        [(0, "Explain the steps the agent takes, the tools it uses, and how it is prompted")],
    ),
    (4, "Rectangle 4", [(0, "Team: CareLoop AI   |   POC: CareLoop AI")]),
    (
        4,
        "TextBox 12",
        [
            (
                0,
                "Why this pattern: one agent loop with two narrow write tools keeps the plan "
                "faithful to the note.",
            )
        ],
    ),
    (
        4,
        "Rectangle 13",
        [
            (1, "3.2  Workflow diagram"),
            (2, "1  Doctor pastes the note (up to 12,000 characters) and presses Process note."),
            (2, "2  The API stores the note, then hands the agent the note plus the patient\u2019s open cards."),
            (2, "3  Gemini calls save_card once per actionable item; close_card closes a card the note confirms, with its evidence phrase."),
            (2, "4  Risk propagation re-checks every dependent card: still blocked \u2192 at_risk, unblocked \u2192 open."),
            (2, "5  The care-gap check matches diagnoses, asks the model which expected items the cards miss, and raises review flags."),
            (2, "6  HUMAN CHECK: the React app shows the doctor each recommendation to approve or dismiss, and patients their own cards and reminders."),
        ],
    ),
    (
        4,
        "Rectangle 16",
        [
            (0, "3.4  SYSTEM PROMPT EXCERPT (5 to 10 lines)"),
            (1, "<role>Extract actionable items from a doctor\u2019s note and keep the patient\u2019s card list accurate.</role>"),
            (2, "<task>Call save_card once per distinct actionable item; never combine items. Types: medication, test, referral, next_visit, general_task.</task>"),
            (3, "<rules>If the note confirms an open card was completed, call close_card with its id. Never close a card the note does not clearly confirm.</rules>"),
            (4, "<output_format>Do not return a list instead of calling the tools. Reply with one sentence on what was saved and closed.</output_format>"),
            (5, "Excerpt from Backend/app/prompts/note_agent.txt, mapped onto the four blocks above."),
        ],
    ),
    # ---------------------------------------------------------------- slide 5
    (5, "Title 1", [(0, "04  Testing, gaps and questions")]),
    (
        5,
        "TextBox 3",
        [(0, "Show how we checked the POC, what is missing, and where we want advice")],
    ),
    (5, "Rectangle 4", [(0, "Team: CareLoop AI   |   POC: CareLoop AI")]),
    (
        5,
        "Rectangle 6",
        [
            (0, "4.1  How we checked it works"),
            (1, "Ran the MCP test suite: 5 tests, all passing (close-card flow, risk flags, tool plumbing)."),
            (1, "Processed 24 real notes end to end: 63 cards saved, 9 closed with evidence, 1 dependent card correctly at_risk."),
            (1, "Raised 21 care-gap recommendations across those notes; a doctor approved or dismissed every one."),
            (1, "Triaged 98 patient messages with the watcher: 26 urgent, 72 not urgent, none lost."),
            (1, "Frontend is React 19 on Vite: role-based card lists, recommendations, reminders, status and due-date edits."),
            (1, "Judged the output by hand: every card had to be traceable to one sentence in the note."),
        ],
    ),
    (
        5,
        "Rectangle 7",
        [
            (0, "4.2  Safety and guardrails"),
            (1, "In place: notes capped at 12,000 characters; cards validated against a typed schema."),
            (1, "The agent can only call save_card and close_card, so it cannot touch the database directly."),
            (1, "A card closes only when the note supplies the confirming phrase, which is stored as evidence."),
            (2, "Not done yet: no prompt-injection tests, no per-user tokens for the MCP server, one shared demo password."),
        ],
    ),
    (
        5,
        "Rectangle 8",
        [
            (0, "4.3  Known gaps and next steps"),
            (1, "Gaps: text-only notes (no scan or PDF), no EHR or FHIR feed, triage results not shown in the UI."),
            (1, "The MCP close call still has no evidence field in the API, so an agent closure is less auditable than a doctor\u2019s."),
            (2, "Next: FHIR intake, a per-patient timeline, an audit log for every closure, and scoped MCP tokens."),
        ],
    ),
    (
        5,
        "Rectangle 9",
        [
            (0, "4.4  QUESTIONS FOR ANTHROPIC (up to 3)"),
            (1, "Q1 (see slide 3): Should note extraction stay one agent with two write tools, or a deterministic extractor with the model only for phrasing? Today the agent decides what is actionable."),
            (1, "Q2 (see slide 4): What is the safest permission shape for a clinical MCP server \u2014 may an agent close a card, or must a human confirm every closure?"),
            (1, "Q3 (see slide 5): Which Claude features would you use to make care-gap reasoning auditable \u2014 citations over the note, structured outputs, or an eval harness?"),
        ],
    ),
]

# 2.2 feature grid -> "Used" (the rest of the template cells stay "Not used")
FEATURE_USED = ["Rectangle 10", "Rectangle 11", "Rectangle 15"]  # tool use, MCP servers, structured outputs
# 3.1 pattern row -> shaded as used
PATTERN_USED = ["Rectangle 9", "Rectangle 10"]  # router, multi-step agent with tools

TABLE_ROW_H = 360000  # fits two wrapped lines of 9.5pt text in the template's table

TOOL_ROWS = [
    ["save_card", "Saves one actionable item as a typed card, with its due date", "Write"],
    ["close_card", "Closes a card the note confirms is done; stores the evidence", "Write"],
    ["careloop_list_cards", "Lists a patient\u2019s cards with status and due dates", "Read"],
    ["careloop_close_card", "Closes a card over MCP (REST + login)", "Write"],
    ["careloop_flag_card_risk", "Flags a card at_risk with a reason for the clinician", "Write"],
]

NOTES = {
    1: (
        "CareLoop AI is the proof of concept we built for this review. It starts from the most "
        "ordinary artefact in a clinic, the doctor\u2019s note, and ends with a closed loop: a typed "
        "plan in the database, the care items nobody ordered, the patients who are blocked, and AI "
        "agents able to act on the same records over MCP."
    ),
    2: (
        "The idea comes from a simple observation: the note is where clinical intent lives, and it is "
        "the one place nothing is tracked. Everything after the note is manual, so we made the note "
        "produce structured, typed work. Be honest in this section: the note pipeline, the care-gap "
        "checklist, risk propagation and the MCP server all run end to end, while the clinic feed, the "
        "logins and the triage screen are still thin. For the market slide, say the figures are vendor "
        "forecasts and that our own sizing is an estimate."
    ),
    3: (
        "Point at the split first: the model decides meaning, and ordinary code owns every durable fact. "
        "The agent can only call two write tools, so it cannot invent a database change. We shade three "
        "features: tool use for the card calls, MCP servers because we ship one, and structured outputs "
        "because every card arrives through a typed schema. Nothing else on that grid is ticked, and we "
        "would rather say that than overstate it. The architecture plate is a live HTML diagram in the "
        "repository, so reviewers can open it and click through the same picture."
    ),
    4: (
        "Walk the workflow left to right and pause on step six, the doctor, because that is where the "
        "design deliberately keeps a person. Risk propagation is the part worth dwelling on: a card that "
        "depends on an open test turns at_risk by itself, and heals when the test lands. On the tools, "
        "the two in-process tools write cards, and the MCP server exposes six read-and-write tools over "
        "REST with no database credentials. The prompt excerpt is verbatim; the full prompt is a text "
        "file in the repository."
    ),
    5: (
        "These numbers come from the running demo, not from a benchmark: 24 notes, 63 cards, 21 "
        "recommendations and 98 triaged messages. Say plainly what is missing, because the guardrails "
        "that exist are the interesting part and the gaps are what we want help with. Then ask the three "
        "questions in order, most important first, and give Anthropic room to answer them."
    ),
}


def tx_body(shape):
    return shape.text_frame._txBody


def set_lines(tx, lines: list[tuple[int, str]]) -> None:
    """Rebuild a text body, copying the formatting of the source paragraph at that index."""
    src = tx.findall(f"{{{A}}}p")
    if not src:
        return
    built = []
    for style_idx, text in lines:
        model = src[min(style_idx, len(src) - 1)]
        if not model.findall(f"{{{A}}}r") and len(src) > 1:
            model = src[1]
        new_p = deepcopy(model)
        for br in new_p.findall(f"{{{A}}}br"):
            new_p.remove(br)
        runs = new_p.findall(f"{{{A}}}r")
        # drop any run that carries no text container
        for run in runs[1:]:
            new_p.remove(run)
        if runs:
            keep = runs[0]
            for child in keep.findall(f"{{{A}}}t"):
                keep.remove(child)
            t = etree.SubElement(keep, f"{{{A}}}t")
            t.text = text
        built.append(new_p)
    for p in src:
        tx.remove(p)
    for p in built:
        tx.append(p)


def shape_by_name(slide, name: str):
    for shp in slide.shapes:
        if shp.name == name:
            return shp
    raise KeyError(f"{name!r} not on slide")


def fill_cell(shape, colour: RGBColor) -> None:
    shape.fill.solid()
    shape.fill.fore_color.rgb = colour
    for para in shape.text_frame.paragraphs:
        for run in para.runs:
            run.font.color.rgb = WHITE


def build_tools_table(slide) -> None:
    frame = shape_by_name(slide, "Table 15")
    table = frame.table
    tbl = frame._element.graphic.graphicData.tbl
    rows = tbl.findall(f"{{{A}}}tr")
    while len(rows) < len(TOOL_ROWS) + 1:
        new_row = deepcopy(rows[-1])
        tbl.append(new_row)
        rows = tbl.findall(f"{{{A}}}tr")
    for row_el in rows:
        row_el.set("h", str(TABLE_ROW_H))
    frame.height = Emu(TABLE_ROW_H * len(rows))
    for row_idx, values in enumerate([["Tool", "What it does", "Read / write"]] + TOOL_ROWS):
        for col_idx, value in enumerate(values):
            cell = table.cell(row_idx, col_idx)
            set_lines(cell.text_frame._txBody, [(0, value)])


def place_plate(slide) -> None:
    panel = shape_by_name(slide, "Rectangle 28")
    body_pr = tx_body(panel).find(f"{{{A}}}bodyPr")
    if body_pr is not None:
        body_pr.set("anchor", "t")
    top = panel.top + Emu(430000)
    max_w, max_h = panel.width - Emu(160000), panel.height - Emu(530000)
    ratio = 2944 / 1904
    width = Emu(int(max_h * ratio))
    if width > max_w:
        width, height = max_w, Emu(int(max_w / ratio))
    else:
        height = max_h
    left = panel.left + Emu(int((panel.width - width) / 2))
    slide.shapes.add_picture(str(PLATE), left, top, width=width, height=height)


def main() -> None:
    prs = Presentation(str(TEMPLATE))
    assert len(prs.slides) == 6, f"template must stay at 6 slides, found {len(prs.slides)}"

    for slide_no, name, lines in CONTENT:
        set_lines(tx_body(shape_by_name(prs.slides[slide_no - 1], name)), lines)

    slide3 = prs.slides[2]
    for name in FEATURE_USED:
        fill_cell(shape_by_name(slide3, name), USED)
    for name in PATTERN_USED:
        fill_cell(shape_by_name(prs.slides[3], name), USED)

    build_tools_table(prs.slides[3])
    # keep clearance below the taller tools table
    prompt_box = shape_by_name(prs.slides[3], "Rectangle 16")
    table_bottom = shape_by_name(prs.slides[3], "Table 15").top + Emu(TABLE_ROW_H * 6)
    prompt_box.top = table_bottom + Emu(90000)

    place_plate(slide3)

    for slide_no, text in NOTES.items():
        prs.slides[slide_no - 1].notes_slide.notes_text_frame.text = text

    prs.save(str(OUTPUT))
    print(f"wrote {OUTPUT.name}: {len(prs.slides)} slides")
    for idx, slide in enumerate(prs.slides, 1):
        notes = slide.notes_slide.notes_text_frame.text if slide.has_notes_slide else ""
        print(f"  slide {idx}: {len(slide.shapes)} shapes, notes {len(notes)} chars, pictures "
              f"{sum(1 for s in slide.shapes if s.shape_type == 13)}")


if __name__ == "__main__":
    main()
