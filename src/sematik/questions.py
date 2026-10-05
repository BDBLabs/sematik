"""Ambiguity-as-first-class-object: when more interpretations than one remain,
a SemanticQuestion blocks conversion until a human answers (spec §15), and the
request is dropped into requests/ on disk (issue T-... workflow)."""

from __future__ import annotations

import pathlib
import textwrap
import time

from .model import SemanticQuestion


def rank_questions(questions: list[SemanticQuestion]) -> list[SemanticQuestion]:
    """Rank by uncertainty × record impact × downstream fanout (spec §16)."""
    for q in questions:
        fanout = len(q.downstream_consequences)
        q.rank = q.affected_records * max(len(q.candidate_interpretations), 1) * max(fanout, 1)
    return sorted(questions, key=lambda q: q.rank, reverse=True)


def render_request(q: SemanticQuestion, out_dir: str | pathlib.Path) -> pathlib.Path:
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    path = out / f"{ts}-question-{q.id}.md"
    body = textwrap.dedent(f"""\
        # Semantic Question {q.id}

        ## Affected concept
        {q.concept}

        ## Candidate interpretations
        {chr(10).join(f'- {c}' for c in q.candidate_interpretations)}

        ## Records affected
        {q.affected_records}

        ## Downstream consequences
        {chr(10).join(f'- {c}' for c in q.downstream_consequences)}

        ## Examples
        {q.examples}

        ## Requested decision
        Which interpretation is correct? Reply by editing the line below
        and mark `Decision:` as one of the candidate interpretations,
        or leave blank to block production conversion.

        Decision:
        """)
    path.write_text(body)
    return path
