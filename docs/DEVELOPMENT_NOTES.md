# Development notes

How this project was built. It was written from scratch.

## Why this project exists

The author's professional work includes schema-grounded NL-to-SQL systems whose code cannot be
published. This repository re-implements the engineering pattern on the public Chinook sample
database: schema
grounding with foreign-key join paths, curated examples, a read-only guard, a bounded repair loop
driven by real error messages, evidence traces, and an evaluation harness. No employer code,
prompts or data were used or consulted.

## First build, 2026-09-16

### Planning

- Public database: Chinook (SQLite build from the lerocha/chinook-database repository, invoice
  dates 2021 to 2025 in this build).
- Golden set: 30 questions written for this project with reference SQL, verified to execute and to
  return a non-empty answer by a test. Phrased to name the columns wanted, because the primary
  metric is deterministic result matching.
- Model: no API key was available, so a local `Qwen/Qwen2.5-Coder-1.5B-Instruct` on the laptop's
  RTX 4050 (6 GB) was used for the real runs. Tests use a scripted mock.

### Iterations

1. `schema.py` (introspection, schema card, BFS join paths, join hints, table mentions),
   `guard.py` (sqlglot parse, read-only enforcement, identifier validation with alias and CTE
   handling), `executor.py` (read-only URI connection, row cap, interrupt-based timeout),
   `examples.py`, `prompts.py`, `llm.py` (mock, local HF, OpenAI-compatible), `agent.py`
   (bounded repair loop, confidence from repair count, JSONL traces), `evaluate.py`, `cli.py`.
2. 47 tests, including a harness self-test with an oracle model that must score 100%.
3. Three full evaluation runs of the golden set with the local model.

### Debugging (found by tests and real runs)

- The oracle self-test scored 4/5: the guard flagged `ORDER BY customers` as an unknown column
  because `customers` was a select-list alias. Aliases are now collected and allowed in ORDER BY,
  GROUP BY and HAVING, with a test.
- A test assumed Genre and MediaType had no join path; Chinook is fully connected through Track,
  so the test now asserts the two-hop path instead.
- The first real run crashed: the model emitted a query sqlglot's *tokenizer* rejected, and the
  guard only caught parser errors. Any `SqlglotError` is now a repairable guard error, with a test
  for an unterminated string literal.
- Golden question g08 asked about 2013, a year with no invoices in this build, and an example
  referred to 2010. Both retargeted; a test now fails if a single-cell golden answer is 0 or NULL.
- Run 1 analysis (24/30 matches) showed the model adding joins the question never asked for in
  three cases, once dropping a GROUP BY as a result. Cause: the agent expanded join hints with
  tables from similar examples even when the question named its own tables. Hints are now
  restricted to tables the question names, and the prompt states "do not add joins that are not
  required" and the minute-to-millisecond rule (the model had converted 5 minutes to 500,000 ms).

### Verification

| Check | Result |
|---|---|
| `pytest -q` | 47 passed |
| `nl2sql schema --db data/chinook.sqlite` | 11 tables, 8 foreign keys printed |
| Evaluation run 1 (before the join-hint fix) | execution 29/30, result match 24/30, repairs 0/1/2: 24/5/1, median 2.1 s |
| Evaluation run 2 (final, committed report) | see README and `reports/` |

### What is and is not claimed

Result-match numbers are on one database and 30 questions the author wrote; they are a sanity
check for the agent, not a benchmark of the model. The LLM-as-judge path exists and is tested with
a mock but was not used for the committed numbers.

## Second increment, 2026-09-16: evidence without a model

The model was not re-run. Instead, the second increment made what already exists verifiable by
someone with no GPU.

- Added `oracle:<golden.json>` as a model spec: it replays the reference SQL for the question in
  the prompt. Running the harness with it is a check of the harness, guard, executor and matcher
  on all 30 cases, and is labelled as such in the report title and a note.
- Added `scripts/show_guard.py`, which pushes 17 fixed inputs through the guard and writes the
  outcome and message for each; a test asserts every expected outcome.
- Added a provenance note to the committed model report: it was produced before the join-hint and
  prompt tightening, and at that time golden g08 asked about 2013 rather than 2023. Neither fact
  was visible in the report file before.
- Wrote the "What is measured, and how" table in the README.

| Check | Result |
|---|---|
| `pytest -q` | 50 passed (47 existing, 3 new in `tests/test_evidence.py`) |
| `nl2sql eval --llm oracle:golden/chinook_golden.json ...` | see `reports/oracle-harness.md` |
| `python scripts/show_guard.py` | see `reports/guard-rejections.md`, 0 unexpected outcomes |
