# Demo notes

Two fictional notes used to show and test the note → cards flow. They contain invented
patient details only; never put real patient information in a demo database.

| File | What it is |
| --- | --- |
| `demo-visit-note.txt` | A primary-care visit note written as the visit conversation: quoted patient answers, objective findings, assessment, plan of eight items. Paste it as a **Doctor's note** to open a plan. |
| `demo-followup-note.txt` | The two-week update that follows. Paste it as an **Update note** to close the labs and watch a dependent card's risk clear. |

Both files are plain text that passes the app's own validation (1–12,000 characters, `NoteCreate`),
and `demo-visit-note.txt` matches exactly one checklist diagnosis — **type 2 diabetes** — so the
recommendations panel has a predictable subject. That was checked with the app's own
`detect_diagnoses()` / `load_checklist()` code, not by eye.

## Run the demo

Sign in at <http://localhost:5173> with password `password`.

1. **`admin`** → *Accounts* → **+ New account** → role **Patient**, name `Maria Delgado`. This gives the
   plan a clean patient instead of mixing it with the seeded demo data (the seed data is untouched
   either way).
2. **`coordinator`** (care coordinator) → **Choose patient…** → `Maria Delgado` → paste
   `samples/demo-visit-note.txt` into **Update note** → **Add update**.
   A doctor login works identically; a patient login has no note box at all.
3. The cards land under **Every next step, in one place**, and the eight plan items become cards with
   the due dates read out of the note.
4. **`dr_smith`** → **Show recommendations** shows the items the plan is missing. **Add as card** turns
   one into a card, **Dismiss** drops it.
5. Dependency beat: on the follow-up visit card use **+ Add Dependency** with the HbA1c card's id and a
   reason. The card flips to **at_risk**.
6. Paste `samples/demo-followup-note.txt` → the lab cards close as `verified_closed` and the
   dependent card returns to `open`.

Headless equivalent (the same calls the UI makes):

```bash
API=http://127.0.0.1:8000/api
TOKEN=$(curl -s -X POST $API/auth/login -H 'Content-Type: application/json' \
  -d '{"username":"coordinator","password":"password"}' \
  | python3 -c 'import sys, json; print(json.load(sys.stdin)["token"])')

python3 -c 'import json,pathlib; print(json.dumps({"text": pathlib.Path("samples/demo-visit-note.txt").read_text(), "patient_id": 13}))' > /tmp/note.json
curl -s -X POST $API/notes/process -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d @/tmp/note.json | python3 -m json.tool
```

## What the example actually produced

Measured on 12 October 2026 against the demo database (`gemini-3.6-flash`, real Gemini call):

| Plan item in the note | Card saved | Type | Due |
| --- | --- | --- | --- |
| metformin 500 mg twice daily | Start metformin 500 mg twice daily with food | medication | — |
| review tolerance in two weeks | Review metformin tolerance | general_task | +2 weeks |
| HbA1c at the lab | HbA1c at the lab | test | +3 months |
| fasting lipid panel | Fasting lipid panel at the lab | test | +3 months |
| retinal screening referral | Referral to retinal screening service for diabetic eye exam | referral | — |
| home glucose log | Check fasting glucose at home three mornings a week and keep a log | general_task | — |
| blood pressure at visits | Record blood pressure at home | general_task | — |
| follow-up visit in three months | Diabetes follow-up visit with glucose log and lab results | next_visit | +3 months |

Eight cards from eight items, five card types, and the relative dates resolved correctly
(visit date + 2 weeks and + 3 months). The background material in the note — family history, the
clinic glucose of 198, the ECG already done, the deferred foot check — produced no cards, which is
the behaviour the note agent's prompt asks for.

Recommendations raised for the note: **five** — foot examination, kidney function and urine albumin,
diabetes education or dietitian referral, hypoglycaemia safety advice, and the diabetes follow-up
visit. The first three are genuine gaps (the note defers the foot check and never mentions the other
two); the last two are cards that exist but whose wording the coverage model did not map back to the
checklist label, which is the honest limit of the check.

Follow-up note: closed three cards — HbA1c, the lipid panel, and "Review metformin tolerance" — and
left the referral open, because the note says the retinal screening appointment is *not arranged yet*.
With the follow-up visit card depending on both lab cards, it read `at_risk` before the follow-up and
`open` after it.

## Caveats

- Extraction and the care-gap coverage check are both Gemini calls. Card wording, the number of cards
  and the recommendation set can shift by one between runs; the counts above are what one real run
  produced, not a guarantee.
- The `patient_id` in the headless example is whatever patient you created; read it from
  `GET /api/patients` first.
