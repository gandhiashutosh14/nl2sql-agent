"""The two evidence paths that run without a model: the oracle harness run and the guard-outcome script."""
import pathlib
import sys

from nl2sql.agent import NL2SQLAgent
from nl2sql.evaluate import evaluate, load_golden
from nl2sql.llm import OracleLLM, make_llm
from nl2sql.schema import Schema

ROOT = pathlib.Path(__file__).resolve().parents[1]
DB = str(ROOT / "data" / "chinook.sqlite")
GOLDEN = str(ROOT / "golden" / "chinook_golden.json")
sys.path.insert(0, str(ROOT / "scripts"))
import show_guard  # noqa: E402


def test_oracle_llm_replays_reference_sql_and_is_labelled_as_such():
    llm = make_llm(f"oracle:{GOLDEN}")
    assert isinstance(llm, OracleLLM) and llm.name.startswith("oracle:")
    golden = load_golden(GOLDEN)
    reply = llm.complete([{"role": "user", "content": "Schema: ...\n\nQuestion: " + golden[0].question}])
    assert golden[0].sql in reply
    assert "SELECT 1" in llm.complete([{"role": "user", "content": "Question: something nobody asked"}])


def test_oracle_scores_every_golden_case_and_a_stranger_scores_none():
    golden = load_golden(GOLDEN)
    report = evaluate(NL2SQLAgent(DB, OracleLLM(GOLDEN)), golden)
    s = report.summary()
    assert s["cases"] == len(golden) and s["execution_success"] == 1.0 and s["result_match"] == 1.0
    assert s["repairs_histogram"] == {0: len(golden)}
    # Executes on every case (SELECT 1 is valid SQL) but matches no reference: the matcher is not trivially satisfied.
    stranger = evaluate(NL2SQLAgent(DB, OracleLLM(GOLDEN)), [type(g)(id="x", question="unknown?", sql=g.sql) for g in golden[:3]])
    assert stranger.summary()["execution_success"] == 1.0 and stranger.summary()["result_match"] == 0.0


def test_show_guard_outcomes_match_their_expectations():
    rows = show_guard.run_all(Schema.from_sqlite(DB))
    assert len(rows) == len(show_guard.CASES) >= 15
    for case, outcome, message in rows:
        assert outcome == case.expected, (case.label, outcome, message)
        if outcome != "accepted":
            assert message
    by_label = {c.label: (o, m) for c, o, m in rows}
    assert "Only SELECT" in by_label["write: DELETE"][1]
    assert "found 2" in by_label["two statements"][1]
    assert "does not parse" in by_label["unterminated string"][1]
    assert "Unknown table" in by_label["unknown table"][1] and "FirstName" in by_label["unknown column"][1]
    text = show_guard.render(rows, "test")
    assert "0 unexpected outcomes" in text
