"""
CLI: inspect a schema, ask one question, or run the evaluation harness.

  python -m nl2sql.cli schema --db data/chinook.sqlite
  python -m nl2sql.cli ask --db data/chinook.sqlite --llm hf:Qwen/Qwen2.5-Coder-1.5B-Instruct "Top 5 countries by customers"
  python -m nl2sql.cli eval --db data/chinook.sqlite --llm hf:... --golden golden/chinook_golden.json --report reports/run.md
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Optional, Sequence

from .agent import NL2SQLAgent
from .evaluate import evaluate, load_golden, save_report
from .examples import ExampleBank
from .llm import make_llm
from .schema import Schema


def _agent(args) -> NL2SQLAgent:
    llm = make_llm(args.llm)
    return NL2SQLAgent(args.db, llm, examples=ExampleBank.load(args.examples), max_repairs=args.max_repairs,
                       trace_dir=args.trace_dir)


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="nl2sql", description="Schema-grounded NL-to-SQL agent")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("schema", help="print the schema card and join graph")
    s.add_argument("--db", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", required=True)
    common.add_argument("--llm", default="mock", help="mock | oracle:<golden.json> | hf:<model-id> | openai:<model>")
    common.add_argument("--examples", default=None, help="JSON file of few-shot examples")
    common.add_argument("--max-repairs", type=int, default=2)
    common.add_argument("--trace-dir", default="traces")

    a = sub.add_parser("ask", parents=[common], help="answer one question")
    a.add_argument("question")

    e = sub.add_parser("eval", parents=[common], help="run the golden set")
    e.add_argument("--golden", required=True)
    e.add_argument("--report", required=True, help="markdown report path")
    e.add_argument("--json", default=None, help="optional JSON results path")
    e.add_argument("--judge", default=None, help="LLM spec for the optional equivalence judge")
    e.add_argument("--note", default=None, help="paragraph to put at the top of the report (provenance, caveats)")

    args = p.parse_args(argv)

    if args.cmd == "schema":
        schema = Schema.from_sqlite(args.db)
        print(schema.card())
        print("\nJoin graph:")
        for t, edges in schema.join_graph().items():
            for other, fk in edges:
                if fk.table == t:
                    print(f"  {fk.as_join()}")
        return 0

    agent = _agent(args)
    if args.cmd == "ask":
        res = agent.ask(args.question)
        print(json.dumps({k: v for k, v in res.to_dict().items() if k != "attempts"}, indent=2, default=str))
        return 0 if res.status == "ok" else 1

    golden = load_golden(args.golden)
    judge = make_llm(args.judge) if args.judge else None
    try:
        from tqdm import tqdm
        progress = lambda it: tqdm(list(it), desc="evaluating")  # noqa: E731
    except ImportError:
        progress = None
    report = evaluate(agent, golden, judge=judge, progress=progress)
    save_report(report, args.report, args.json)
    if args.note:
        from pathlib import Path
        md = Path(args.report)
        title, _, rest = md.read_text(encoding="utf-8").partition("\n")
        md.write_text(f"{title}\n\n> {args.note}\n{rest}", encoding="utf-8")
    print(json.dumps(report.summary(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
