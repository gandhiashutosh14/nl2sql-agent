import json
import pathlib

import pytest

from nl2sql.agent import NL2SQLAgent
from nl2sql.evaluate import evaluate, load_golden, rows_match
from nl2sql.examples import ExampleBank
from nl2sql.executor import run_query
from nl2sql.guard import SQLGuardError, validate
from nl2sql.llm import MockLLM
from nl2sql.prompts import extract_sql, generation_messages, parse_judge
from nl2sql.schema import Schema

ROOT = pathlib.Path(__file__).resolve().parents[1]
DB = str(ROOT / "data" / "chinook.sqlite")
GOLDEN = str(ROOT / "golden" / "chinook_golden.json")
EXAMPLES = str(ROOT / "examples" / "chinook_examples.json")


@pytest.fixture(scope="module")
def schema():
    return Schema.from_sqlite(DB)


# ---------------------------------------------------------------------------
# Schema grounding
# ---------------------------------------------------------------------------
def test_schema_loads_all_tables_with_keys(schema):
    assert len(schema.tables) == 11
    assert schema.tables["Track"].has_column("Milliseconds")
    assert "Track(" in schema.card() and "-> Album.AlbumId" in schema.card()
    assert schema.resolve_table("track") == "Track"


def test_join_path_walks_foreign_keys(schema):
    path = schema.join_path("Track", "Artist")
    assert [fk.as_join() for fk in path] == ["Track.AlbumId = Album.AlbumId", "Album.ArtistId = Artist.ArtistId"]
    # Genre and MediaType only meet through Track: two hops, found by BFS over the undirected FK graph
    assert [fk.as_join() for fk in schema.join_path("Genre", "MediaType")] == [
        "Track.GenreId = Genre.GenreId", "Track.MediaTypeId = MediaType.MediaTypeId"]
    assert schema.join_path("Track", "Track") == []
    assert schema.join_path("Track", "NoSuchTable") == []


def test_join_hints_and_table_mentions(schema):
    assert schema.join_hints(["Customer", "Invoice"]) == ["Invoice.CustomerId = Customer.CustomerId"]
    mentioned = schema.tables_mentioned("How many invoice lines and tracks are there per genre?")
    assert {"InvoiceLine", "Track", "Genre"} <= set(mentioned)


# ---------------------------------------------------------------------------
# Guard
# ---------------------------------------------------------------------------
def test_guard_rejects_writes_and_multiple_statements(schema):
    with pytest.raises(SQLGuardError):
        validate("DELETE FROM Customer", schema)
    with pytest.raises(SQLGuardError):
        validate("SELECT 1; SELECT 2", schema)
    with pytest.raises(SQLGuardError):
        validate("SELECT * FROM Customer; DROP TABLE Customer", schema)


def test_guard_turns_tokenizer_and_parser_failures_into_repairable_errors(schema):
    # An unterminated string literal fails in sqlglot's tokenizer, not its parser; both must become SQLGuardError.
    with pytest.raises(SQLGuardError, match="does not parse"):
        validate("SELECT Name FROM Genre WHERE Name = 'Rock", schema)
    with pytest.raises(SQLGuardError, match="does not parse"):
        validate("SELECT FROM WHERE", schema)


def test_guard_reports_unknown_columns_with_suggestions(schema):
    _, errors = validate("SELECT c.FullName FROM Customer c", schema)
    assert len(errors) == 1
    assert "FullName" in errors[0] and "FirstName" in errors[0]


def test_guard_accepts_aliases_joins_and_ctes(schema):
    _, errors = validate(
        "SELECT ar.Name, COUNT(*) AS n FROM Artist ar JOIN Album al ON al.ArtistId = ar.ArtistId GROUP BY ar.ArtistId", schema)
    assert errors == []
    _, errors = validate(
        "WITH t AS (SELECT TrackId FROM PlaylistTrack GROUP BY TrackId HAVING COUNT(*) > 1) SELECT COUNT(*) FROM t", schema)
    assert errors == []
    _, errors = validate("SELECT Name FROM Genres", schema)
    assert errors and "Unknown table" in errors[0]


def test_guard_allows_select_list_aliases_in_order_group_and_having(schema):
    _, errors = validate(
        "SELECT Country, COUNT(*) AS customers FROM Customer GROUP BY Country ORDER BY customers DESC LIMIT 1", schema)
    assert errors == []
    _, errors = validate(
        "SELECT strftime('%Y', InvoiceDate) AS year, SUM(Total) AS revenue FROM Invoice GROUP BY year HAVING revenue > 0", schema)
    assert errors == []


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------
def test_executor_caps_rows_and_returns_errors_instead_of_raising():
    r = run_query(DB, "SELECT TrackId FROM Track", row_limit=10)
    assert r.ok and len(r.rows) == 10 and r.truncated
    r = run_query(DB, "SELECT nope FROM Track")
    assert not r.ok and "nope" in r.error
    r = run_query(DB, "INSERT INTO Genre (Name) VALUES ('x')")
    assert not r.ok  # read-only connection


# ---------------------------------------------------------------------------
# Examples and prompts
# ---------------------------------------------------------------------------
def test_example_retrieval_prefers_lexically_similar_questions():
    bank = ExampleBank.load(EXAMPLES)
    top = bank.retrieve("How much revenue did Blues genre tracks generate?", k=2)
    assert "Jazz" in top[0].question


def test_extract_sql_handles_fences_and_bare_statements():
    assert extract_sql("Sure:\n```sql\nSELECT 1;\n```") == "SELECT 1"
    assert extract_sql("SELECT Name FROM Genre; thanks") == "SELECT Name FROM Genre"
    assert extract_sql("I cannot do that") is None
    assert parse_judge("YES\nbecause") is True and parse_judge("no.") is False and parse_judge("maybe") is None


def test_generation_prompt_carries_schema_hints_and_shots(schema):
    bank = ExampleBank.load(EXAMPLES)
    msgs = generation_messages("Which artist made 'Big Ones'?", schema.card(), schema.join_hints(["Album", "Artist"]),
                               bank.retrieve("Which artist made 'Big Ones'?"))
    user = msgs[1]["content"]
    assert "Album.ArtistId = Artist.ArtistId" in user and "```sql" in user and "Question: Which artist made" in user


# ---------------------------------------------------------------------------
# Agent: repair loop and confidence
# ---------------------------------------------------------------------------
def test_agent_repairs_a_bad_column_once(tmp_path):
    llm = MockLLM(["```sql\nSELECT COUNT(*) FROM Customers\n```", "```sql\nSELECT COUNT(*) AS n FROM Customer\n```"])
    agent = NL2SQLAgent(DB, llm, trace_dir=str(tmp_path))
    res = agent.ask("How many customers are there?")
    assert res.status == "ok" and res.rows == [(59,)]
    assert res.repairs_used == 1 and res.confidence == 0.7
    assert [a.kind for a in res.attempts] == ["generate", "repair"]
    assert "Unknown table" in res.attempts[0].guard_errors[0]
    assert "Unknown table 'Customers'" in llm.calls[1][1]["content"]  # the error was fed back
    trace = (tmp_path / "traces.jsonl").read_text(encoding="utf-8")
    assert json.loads(trace.splitlines()[0])["status"] == "ok"


def test_agent_gives_up_after_the_repair_budget():
    llm = MockLLM(["```sql\nSELECT Nope FROM Customer\n```"])
    res = NL2SQLAgent(DB, llm, max_repairs=2).ask("How many customers are there?")
    assert res.status == "failed" and res.repairs_used == 2 and len(res.attempts) == 3 and res.confidence == 0.0


def test_agent_blocks_write_statements_even_if_the_model_insists():
    llm = MockLLM(["```sql\nDELETE FROM Customer\n```"])
    res = NL2SQLAgent(DB, llm, max_repairs=1).ask("Remove all customers")
    assert res.status == "failed"
    assert all("Only SELECT" in e for a in res.attempts for e in a.guard_errors)


# ---------------------------------------------------------------------------
# Evaluation harness
# ---------------------------------------------------------------------------
def test_rows_match_ignores_order_case_and_numeric_type():
    assert rows_match([(1, "usa"), (2.0, "Uk")], [(2, "UK"), (1.0, "USA")])
    assert not rows_match([(1,)], [(1,), (1,)])
    assert rows_match([(3.14159,)], [("3.14",)])


@pytest.mark.parametrize("case", load_golden(GOLDEN), ids=lambda c: c.id)
def test_every_golden_reference_query_runs_and_returns_a_real_answer(case):
    r = run_query(DB, case.sql)
    assert r.ok, r.error
    assert len(r.rows) >= 1
    # A single-cell answer must not be 0 or NULL: that would mean the question targets data the DB does not have.
    if len(r.rows) == 1 and len(r.columns) == 1:
        assert r.rows[0][0] not in (0, None), f"{case.id} returns an empty answer"


def test_harness_scores_a_perfect_and_a_wrong_model():
    golden = load_golden(GOLDEN)[:5]
    answers = {g.question: g.sql for g in golden}

    def oracle(messages):
        user = messages[-1]["content"]
        for q, sql in answers.items():
            if user.rstrip().endswith("Question: " + q):
                return f"```sql\n{sql}\n```"
        return "```sql\nSELECT 1\n```"

    perfect = evaluate(NL2SQLAgent(DB, MockLLM(oracle)), golden)
    assert perfect.summary()["result_match"] == 1.0 and perfect.summary()["execution_success"] == 1.0

    wrong = evaluate(NL2SQLAgent(DB, MockLLM(["```sql\nSELECT 1 AS x\n```"])), golden, judge=MockLLM(["NO\nwrong"]))
    s = wrong.summary()
    assert s["execution_success"] == 1.0 and s["result_match"] == 0.0 and s["judge_rescued"] == 0
    assert "## Mismatches" in wrong.to_markdown()
