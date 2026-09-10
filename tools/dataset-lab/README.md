# IAQ Dataset Lab

This is a standalone local question-bank viewer. It does not use the IAQ web
app, does not create assessment sessions, and does not write to Postgres.

It reads:

- `data/assessment/five_domains/banks/*.jsonl`
- `data/assessment/five_domains/assets/{domain}/`
- `data/assessment/verbal/jsonl/*_en_*.jsonl`

## Run it

From the IAQ project root:

```powershell
python tools/dataset-lab/server.py
```

Then open [http://127.0.0.1:8787](http://127.0.0.1:8787). Keep the terminal
running while you inspect the questions. Stop it with `Ctrl+C`.

## What it does

- Loads the banks directly from disk and reports counts.
- Resolves each generated record's `image_path` to its matching image.
- Randomizes questions and avoids repeats during the current browser run.
- Samples domains evenly when **All loaded datasets** is selected, so the larger
  verbal research bank does not dominate inspection.
- Uses the image as the complete visual question for abstract, logical,
  numerical, and spatial items, with clean A–D selection labels only.
- Runs working-memory items as a manual study → hide → recall flow. Ordered
  sequence items use digit entry; cell-set items use an empty recall grid.
- Keeps answer keys and rules out of the initial question payload.
- Reveals the answer and rule only after you click **Check answer**.
- Separates structural/content issues from human-review and readiness warnings.
- Flags missing fields, bad answer indices, answer mismatches, missing images,
  incomplete memory protocols, unreviewed items, uncalibrated items, and
  non-production items.
- Labels all records as local research data; it never changes lifecycle state.

## Local API notes

- `GET /api/item` returns the safe display payload. Visual option arrays and
  memory answers are not sent to the browser as selectable choices.
- `GET /api/memory/recall?id=...` returns only the recall configuration for a
  valid memory item.
- `POST /api/check` accepts either `{id, answer_index}` for multiple-choice
  records or `{id, response_type, response}` for memory records.

The verbal folder contains LogiQA research records. They are shown for content
inspection only and are not automatically treated as deployable IAQ verbal
items.
