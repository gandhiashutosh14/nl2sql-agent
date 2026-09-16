"""
Prompt contracts. Kept in one place so a reviewer can see exactly what the
model is told, and so tests can assert on the structure.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence

from .examples import Example

SYSTEM = """You are a careful SQLite analyst. You translate a business question into ONE read-only SQL query.

Rules:
- Use only the tables and columns listed in the schema. Never invent names.
- Join only the tables the question needs, using the JOIN conditions given in the hints. Do not add joins that are not required to answer the question.
- SQLite dialect: dates are TEXT like '2023-05-07 00:00:00'; use strftime('%Y', col) for years.
- Convert units carefully: 1 minute = 60000 milliseconds.
- Prefer explicit column lists over SELECT * and give aggregates clear aliases.
- Return the SQL inside a ```sql fenced block and nothing else."""


def _fence(sql: str) -> str:
    return f"```sql\n{sql.strip()}\n```"


def generation_messages(question: str, schema_card: str, join_hints: Sequence[str],
                        examples: Sequence[Example]) -> List[Dict[str, str]]:
    parts = [f"Schema:\n{schema_card}"]
    if join_hints:
        parts.append("Join hints:\n" + "\n".join(f"- {h}" for h in join_hints))
    if examples:
        shots = "\n\n".join(f"Question: {ex.question}\n{_fence(ex.sql)}" for ex in examples)
        parts.append(f"Examples of the house style:\n\n{shots}")
    parts.append(f"Question: {question}")
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": "\n\n".join(parts)}]


def repair_messages(question: str, schema_card: str, join_hints: Sequence[str],
                    previous_sql: str, errors: Sequence[str]) -> List[Dict[str, str]]:
    problems = "\n".join(f"- {e}" for e in errors)
    user = (
        f"Schema:\n{schema_card}\n\n"
        + ("Join hints:\n" + "\n".join(f"- {h}" for h in join_hints) + "\n\n" if join_hints else "")
        + f"Question: {question}\n\n"
        f"Your previous query:\n{_fence(previous_sql)}\n\n"
        f"It failed for these reasons:\n{problems}\n\n"
        "Write a corrected query that fixes every listed problem. Return only the ```sql block."
    )
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def judge_messages(question: str, reference_sql: str, reference_preview: str,
                   candidate_sql: str, candidate_preview: str) -> List[Dict[str, str]]:
    user = (
        "Two SQL queries were written for the same question. Decide whether the CANDIDATE answers the "
        "question as correctly as the REFERENCE, judging by meaning and by the result previews. Minor "
        "differences in column names, ordering or formatting do not matter; different entities, filters, "
        "aggregations or row sets do.\n\n"
        f"Question: {question}\n\n"
        f"REFERENCE SQL:\n{reference_sql}\nREFERENCE result preview:\n{reference_preview}\n\n"
        f"CANDIDATE SQL:\n{candidate_sql}\nCANDIDATE result preview:\n{candidate_preview}\n\n"
        "Answer with exactly one word on the first line, YES or NO, then one sentence of reason."
    )
    return [{"role": "system", "content": "You are a strict but fair SQL reviewer."},
            {"role": "user", "content": user}]


_FENCE_RE = re.compile(r"```(?:sql)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)


def extract_sql(text: str) -> Optional[str]:
    """Pull the SQL out of a model reply: fenced block first, else the first SELECT/WITH statement."""
    if not text:
        return None
    m = _FENCE_RE.search(text)
    if m and m.group(1).strip():
        return m.group(1).strip().rstrip(";").strip()
    m = re.search(r"(?is)\b(select|with)\b.*", text)
    if m:
        candidate = m.group(0).split(";")[0].strip()
        return candidate or None
    return None


def parse_judge(text: str) -> Optional[bool]:
    first = (text or "").strip().splitlines()[0].strip().upper() if (text or "").strip() else ""
    if first.startswith("YES"):
        return True
    if first.startswith("NO"):
        return False
    return None
