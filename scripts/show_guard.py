"""
Show what the SQL guard does with inputs a model might produce, and write the
outcomes to a Markdown table. No model is involved: the inputs are fixed here.

  python scripts/show_guard.py --db data/chinook.sqlite --out reports/guard-rejections.md

Three outcomes are possible for one input:
  rejected   a hard SQLGuardError: the SQL never reaches the database (writes, several
             statements, unparsable text)
  errors     the SQL parsed and is read-only but names things the schema does not have; the
             agent feeds these sentences back to the model for repair
  accepted   clean; the executor would run it read-only with a row cap and a timeout
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nl2sql.guard import SQLGuardError, validate  # noqa: E402
from nl2sql.schema import Schema  # noqa: E402


@dataclass(frozen=True)
class Case:
    label: str
    sql: str
    expected: str            # rejected | errors | accepted


CASES: List[Case] = [
    Case("write: DELETE", "DELETE FROM Customer", "rejected"),
    Case("write: INSERT", "INSERT INTO Genre (Name) VALUES ('x')", "rejected"),
    Case("write: UPDATE", "UPDATE Track SET UnitPrice = 0", "rejected"),
    Case("DDL: DROP", "DROP TABLE Invoice", "rejected"),
    Case("two statements", "SELECT 1; SELECT 2", "rejected"),
    Case("select then DROP", "SELECT * FROM Customer; DROP TABLE Customer", "rejected"),
    Case("PRAGMA", "PRAGMA table_info(Customer)", "rejected"),
    Case("unterminated string", "SELECT Name FROM Genre WHERE Name = 'Rock", "rejected"),
    Case("not SQL", "SELECT FROM WHERE", "rejected"),
    Case("empty reply", "", "rejected"),
    Case("unknown table", "SELECT Name FROM Genres", "errors"),
    Case("unknown column", "SELECT c.FullName FROM Customer c", "errors"),
    Case("unknown column, unqualified", "SELECT Revenue FROM Invoice", "errors"),
    Case("plain select", "SELECT Country, COUNT(*) AS customers FROM Customer GROUP BY Country", "accepted"),
    Case("select-list alias in ORDER BY", "SELECT Country, COUNT(*) AS n FROM Customer GROUP BY Country ORDER BY n DESC LIMIT 1", "accepted"),
    Case("join with aliases", "SELECT ar.Name, COUNT(*) AS albums FROM Artist ar JOIN Album al ON al.ArtistId = ar.ArtistId GROUP BY ar.ArtistId", "accepted"),
    Case("CTE", "WITH t AS (SELECT TrackId FROM PlaylistTrack GROUP BY TrackId HAVING COUNT(*) > 1) SELECT COUNT(*) FROM t", "accepted"),
]


def run_case(case: Case, schema: Schema) -> Tuple[str, str]:
    """(outcome, message) for one input."""
    try:
        _, errors = validate(case.sql, schema)
    except SQLGuardError as e:
        return "rejected", str(e)
    if errors:
        return "errors", " ".join(errors)
    return "accepted", ""


def run_all(schema: Schema) -> List[Tuple[Case, str, str]]:
    return [(c, *run_case(c, schema)) for c in CASES]


def _revision() -> str:
    try:
        sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, text=True).strip()
        return sha + (" (uncommitted changes present)" if dirty else "")
    except Exception:  # noqa: BLE001
        return "unknown"


def render(rows: List[Tuple[Case, str, str]], command: str) -> str:
    lines = ["# Guard outcomes for fixed inputs", "",
             f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} at revision {_revision()} with `{command}`. "
             "The inputs are written in `scripts/show_guard.py`; no model produced them. `rejected` means the SQL never reaches "
             "the database; `errors` means it parsed and is read-only but names unknown identifiers, and the sentences shown are "
             "what the agent feeds back to the model for repair; `accepted` means the executor would run it read-only with a "
             "row cap and a timeout.", "",
             "| Input | SQL | Outcome | Expected | Guard message |", "|---|---|---|---|---|"]
    for case, outcome, message in rows:
        flag = "" if outcome == case.expected else " **(unexpected)**"
        sql = case.sql.replace("|", "\\|") or "(empty)"
        lines.append(f"| {case.label} | `{sql}` | {outcome}{flag} | {case.expected} | {message.replace('|', '/')} |")
    unexpected = sum(1 for c, o, _ in rows if o != c.expected)
    lines += ["", f"{len(rows)} inputs, {unexpected} unexpected outcomes."]
    return "\n".join(lines)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Write the guard outcomes for a fixed list of inputs.")
    p.add_argument("--db", default=str(ROOT / "data" / "chinook.sqlite"))
    p.add_argument("--out", default=str(ROOT / "reports" / "guard-rejections.md"))
    args = p.parse_args(argv)
    rows = run_all(Schema.from_sqlite(args.db))
    text = render(rows, "python scripts/show_guard.py --db data/chinook.sqlite --out reports/guard-rejections.md")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    return 0 if all(o == c.expected for c, o, _ in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
