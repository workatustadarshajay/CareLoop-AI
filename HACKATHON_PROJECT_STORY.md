# CareLoop AI — Project Story

> The "About the project" submission text, formatted in Markdown with LaTeX math.
> Paste the sections below into the hackathon form (Devpost-style fields render
> Markdown and `$...$` / `$$...$$` equations).

---

## What inspired us

The seed of CareLoop AI was a simple, uncomfortable observation: **a doctor's note
is not a to-do list, but it should be.** A single visit produces a dozen small,
consequential commitments — start this medication, order that MRI, refer to
neurology, book a follow-up in six weeks. The clinician is diligent when writing
them. The system, however, stores them as prose. After the visit ends, completion
is tracked by human memory, and memory is exactly the wrong place for a task that
someone's health depends on.

Missed clinical follow-up is a well-known failure mode: the test that is ordered
but never checked, the referral that is sent but never scheduled, the medication
that is started but never reconciled. The work is not hard — it is *unowned*.

We did not want to build another chatbot that summarizes notes. Summarization
adds another wall of text nobody re-reads. We wanted the opposite: **extraction
into structure, and structure that stays alive.** Every actionable sentence
should become a real, typed object with a state, an owner, and a lifecycle. From
that conviction, CareLoop AI was born: a note goes in, and a *living care plan*
comes out — one that notices its own gaps, flags its own blockers, and closes its
own loops as evidence arrives.

And because the plan is a real data structure, it becomes something an AI agent
can safely act on. That is where the second inspiration came in: the Model
Context Protocol. If the plan is structured, we can hand an agent exactly the
tools it needs — and not one database credential more.

---

## How we built it

### The pipeline

CareLoop AI is four cooperating services that share one PostgreSQL database.

1. **Intake.** A clinician submits a free-text note (up to 12,000 characters)
   through the React frontend, or via `POST /api/notes/process`.
2. **Extraction.** A Gemini **tool-calling** agent reads the note and calls a
   `save_card` tool once per actionable item. The agent does not free-form an
   answer we then have to parse; it emits structured tool calls that map directly
   onto rows. Each card is typed as `medication`, `test`, `referral`,
   `next_visit`, or `general_task`, and starts `open`.
3. **Interpretation.** The backend matches the note's content against a
   care-gap checklist and proposes anything the clinician likely intended but
   omitted, and it links cards into a dependency graph so blockers become
   visible.
4. **Agency.** An MCP server exposes the plan as typed tools so any MCP-capable
   assistant can read and act on it.

### Making the plan self-healing

Three mechanisms make the plan more than a static table.

**Care-gap checks.** We encoded guidance for 28 conditions — heart failure, type
2 diabetes, COPD, chronic kidney disease, pregnancy, post-operative care, and
more — each into a checklist of 5–10 expected items. For a diagnosis $d$ with
expected item set $E_d$ and present plan items $P$, coverage is simply

$$
C_d = \frac{\lvert E_d \cap P\rvert}{\lvert E_d\rvert}, \qquad C_d \in [0, 1]
$$

and the plan's overall completeness across the diagnoses $D$ present in the note
is the mean

$$
\bar{C} = \frac{1}{\lvert D\rvert} \sum_{d \in D} C_d .
$$

Anything with a low per-diagnosis $C_d$ becomes a *suggestion*, never an
automatic order: the doctor clicks **Add as card** or **Dismiss**. The
regression is deliberate — a guideline is a prompt, not a prescription.

**Risk propagation.** Cards form a directed dependency graph. If card $j$
depends on card $i$, then as long as the upstream card is unresolved the
downstream card is not truly "open" — it is *blocked*. We encode that as

$$
\text{state}(j) =
\begin{cases}
\texttt{at\_risk} & \text{if } \exists\, i \in \mathrm{deps}(j) \text{ with } \text{state}(i) \neq \texttt{closed} \\
\texttt{open} & \text{otherwise.}
\end{cases}
$$

In the demo, a neurology follow-up sits `at_risk` because it is waiting on the MRI
result first. The blocker is *visible*, instead of silently overdue.

**Auto-closure.** When a follow-up note arrives — for example, "MRI completed" —
the system matches it to the open card, closes it as `verified_closed` with the
supporting evidence attached, and re-evaluates the dependency graph so the
downstream `at_risk` flag clears on its own. This is what we mean by *closing the
loop*: the plan heals itself as reality catches up, and completion is recorded
with provenance rather than assumed.

Anything still due within the reminder window (`REMINDER_DAYS`, default 3) raises
a reminder, so the plan also knows what is *about to* go wrong.

### Handing the plan to agents — safely

The most deliberate architectural decision was making the MCP server a **pure
REST client**. It holds no database credentials, opens no connection pool, and
imports nothing from the backend application. It only ever speaks HTTP to the
FastAPI layer, through a small typed tool surface:

`careloop_list_patients`, `careloop_list_cards`, `careloop_get_card`,
`careloop_close_card`, `careloop_flag_card_risk`, `careloop_list_notes`.

That constraint is a feature. An AI agent gets a narrow, auditable, permissioned
surface instead of raw SQL, and the backend remains the single place where
clinical rules and authorization live. We proved the loop end to end twice: the
Gemini MCP client ran **seven autonomous tool calls** — reading the plan, closing
the upstream MRI card with evidence, and watching the dependent risk flag clear.

### A second signal: message triage

We also built an **urgency watcher**. It polls a folder of incoming patient
messages, classifies each one's urgency with the `laya` router, and stores the
verdict in Postgres. Each message $x$ is routed to the most probable class

$$
\hat{u} = \arg\max_{u \in \{\texttt{urgent},\, \texttt{medium},\, \texttt{not\_urgent}\}} P(u \mid x),
$$

and both the decision and its confidence are persisted, so a care team can
triage incoming messages by urgency rather than by arrival order. Confidence and
the routed model are stored alongside the label, because a triage system that
cannot explain itself will not be trusted.

### Stack

- **Backend:** Python, FastAPI, Pydantic, `asyncpg`; a Gemini tool-calling agent
  (default model `gemini-3.8-flash`).
- **Frontend:** React 19, TypeScript, Vite.
- **Database:** PostgreSQL via Docker Compose.
- **Agent layer:** an HTTP MCP server (pure REST client, `httpx`), a Gemini MCP
  demo client, and a dependency-free MCP demo client.
- **Triage:** the `laya` router for message urgency.
- **Testing:** a `pytest` suite around the Gemini MCP client (5 passing).

---

## What we learned

**1. Tool calling beats parsing.** The single biggest quality jump came from
making the LLM emit *structured tool calls* instead of prose we then parse. The
model's job shrinks to a well-typed function call, and the failure modes shrink
with it. Agent reliability is largely a schema-design problem.

**2. The hard part of agentic systems is the permission boundary, not the
model.** The moment we stopped thinking of the agent as "the thing that does the
work" and started thinking of it as "the thing that calls a narrow tool
surface," the design got simpler and far more defensible. A pure-REST MCP server
with no database credentials is a security posture, and it happened to be easier
to build, too.

**3. State machines are the hidden architecture.** `open`, `at_risk`,
`verified_closed`, `done` — most of the product's intelligence is just a careful
set of legal transitions over a dependency graph. Modeling the graph explicitly
is what let risk *propagate* instead of merely being stored.

**4. Clinical software must be a suggestion engine, not an autopilot.** The
care-gap checklist was most useful when it proposed and the clinician disposed.
We deliberately kept humans in the loop, and that made the tool feel trustworthy
rather than threatening.

**5. Reproducibility is a feature of the pitch.** Getting every service to start
in one documented order — database, backend, frontend, MCP server — with a
written command reference, mattered as much to a demo as the model quality did.

---

## The challenges we faced

**Structured extraction from messy prose.** Real notes mix abbreviations,
hedges, and implicit intent ("recheck A1c in 3 months" is a `test` *and* a
follow-up). We iterated on the tool schema and the note-to-card prompt until the
agent's tool calls mapped cleanly onto typed cards, then added the care-gap layer
to catch what extraction alone missed.

**Making dependencies visible without over-flagging.** Early risk propagation was
too eager — everything downstream lit up. We tuned the rule to flag a dependent
card only when its upstream prerequisite is genuinely unresolved, so `at_risk`
stays a meaningful signal rather than noise.

**Closing the loop with evidence.** Auto-closing on a follow-up note is only safe
if the match is defensible. We required a closure to record the evidence that
justified it, and we kept `verified_closed` distinct from `done` so an automatic
match never masquerades as a human's confirmation.

**A narrow, credential-free agent surface.** It would have been faster to let the
MCP server talk to Postgres directly. Refusing that shortcut forced us to design
a typed REST surface, handle auth propagation, and accept the real limitations
that come with it (no get-by-id for every object, no free-form risk reason in the
response). The constraint made the system both safer and easier to reason about.

**Infrastructure friction.** A TLS-inspecting proxy on the machine meant every
managed Python command needed system certificates, and CPU-only PyTorch had to be
pinned to avoid pulling gigabytes of CUDA libraries with no GPU to use them. We
lost real time to this and eventually documented it, which is why the project
ships a single command reference that just works.

---

## What's next

Closer integration between the urgency watcher and the care plan (triage a
message, then open a card directly from it), a first-class closure-evidence field
in the API, and richer dependency types beyond simple prerequisites — so the plan
can model "this drug before that procedure" as naturally as it models "this
result before that referral."
