"""Print the ADR-0006 section 10 retrieval baselines (offline, deterministic).

    PYTHONPATH=src python3 scripts/eval_retrieval.py

Measures lexical-only and glossary-expanded lexical retrieval over the
PROVISIONAL labeled CPASF set. Dense and hybrid baselines are NOT computed
here: they require a live embedding call, which must go through the egress
gate (rank_semantic_candidates) and is not part of this offline script.
"""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from sematik.cpasf_pack import cpasf_pack  # noqa: E402
from sematik.hybrid import retrieve  # noqa: E402
from sematik.lexical import BM25Index, Glossary  # noqa: E402
from sematik.retrieval_eval import LabeledQuery, evaluate_retriever  # noqa: E402

FIXTURE = pathlib.Path(__file__).resolve().parent.parent / "tests/fixtures/retrieval_eval_cpasf.json"


def main() -> None:
    data = json.loads(FIXTURE.read_text())
    print(f"STATUS: {data['meta']['status']}\n{data['meta']['review_required']}\n")
    cases = [LabeledQuery(c["id"], c["query"], frozenset(c["relevant"]), tuple(c["tags"]))
             for c in data["cases"]]
    pack = cpasf_pack()
    variants = {
        "lexical only": BM25Index(pack.canonical_concepts),
        "lexical + glossary": BM25Index(pack.canonical_concepts, glossary=Glossary(pack.glossary)),
    }
    print(f"{'variant':20} {'R@1':>6} {'R@5':>6} {'R@10':>6} {'MRR':>6}  false-abstain  false-retrieve")
    for name, index in variants.items():
        r = evaluate_retriever(cases, lambda q, i=index: retrieve(q, lexical=i))
        print(f"{name:20} {r.recall_at[1]:6.2f} {r.recall_at[5]:6.2f} {r.recall_at[10]:6.2f} "
              f"{r.mrr:6.2f}  {len(r.abstained_on_answerable):>13}  {len(r.answered_on_unanswerable):>14}")
        print(f"{'':20} by tag @5: " + ", ".join(f"{t}={v[5]:.2f}" for t, v in sorted(r.recall_by_tag.items())))
        if r.answered_on_unanswerable:
            print(f"{'':20} answered an unanswerable query: {', '.join(r.answered_on_unanswerable)}")
    print("\ndense / hybrid baselines: not measured (requires a governed live embedding run)")


if __name__ == "__main__":
    main()
