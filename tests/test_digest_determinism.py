"""I-13: every digest that reaches a manifest is a function of content only.

A Mapping gets a uuid4 id by default. The plan digest and therefore the run
manifest hash must not depend on it (spec §22 reproducibility, §69
determinism, ADR-0004). Each test reproduces the counterexample against the
real compile -> run path.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from helpers import approved_mapping, prov
from sematik.compiler import CompilationError, PlanStep, compile_mapping
from sematik.runner import run_conversion

ROOT = Path(__file__).resolve().parents[1]
ROWS = [{"_id": i, "x": i} for i in range(5)]


def _built():
    m = approved_mapping(target_artifact="t")
    p = compile_mapping(m, [PlanStep("copy", {"from": "x", "to": "t"})])
    return m, p


def _run(rows, plan, mapping):
    return run_conversion(rows, plan, mapping, source_snapshot="snap",
                          domain_pack_version="p", engine_version="e",
                          provenance_of=prov)


def test_equal_content_mappings_have_distinct_ids_but_equal_digests():
    (m1, p1), (m2, p2) = _built(), _built()
    assert m1.id != m2.id
    assert m1.digest() == m2.digest()
    assert p1.digest() == p2.digest()


def test_manifest_hash_equal_for_independently_built_equal_content():
    (m1, p1), (m2, p2) = _built(), _built()
    assert _run(ROWS, p1, m1).manifest_hash() == _run(ROWS, p2, m2).manifest_hash()


def test_plan_digest_still_changes_when_behavior_or_approval_changes():
    m, p = _built()
    other = compile_mapping(m, [PlanStep("copy", {"from": "z", "to": "t"})])
    assert other.digest() != p.digest()                      # steps
    m_other = approved_mapping(target_artifact="t", approved_by="someone-else")
    p_other = compile_mapping(m_other, [PlanStep("copy", {"from": "x", "to": "t"})])
    assert p_other.digest() != p.digest()                    # approver
    m_ver = approved_mapping(target_artifact="t", version="2.0.0")
    p_ver = compile_mapping(m_ver, [PlanStep("copy", {"from": "x", "to": "t"})])
    assert p_ver.digest() != p.digest()                      # version


def test_plan_is_still_bound_to_its_own_mapping_instance():
    """Dropping the id from the digest must not let a plan run under a
    different mapping object: bound_to() keeps the id check."""
    (m1, p1), (m2, _) = _built(), _built()
    assert p1.bound_to(m1)
    assert not p1.bound_to(m2)
    with pytest.raises(CompilationError, match="not bound"):
        _run(ROWS, p1, m2)


_CHILD = """
from helpers import approved_mapping, prov
from sematik.compiler import PlanStep, compile_mapping
from sematik.runner import run_conversion
m = approved_mapping(target_artifact="t")
p = compile_mapping(m, [PlanStep("copy", {"from": "x", "to": "t"})])
run = run_conversion([{"_id": i, "x": i} for i in range(5)], p, m,
                     source_snapshot="snap", domain_pack_version="p",
                     engine_version="e", provenance_of=prov)
print(run.manifest_hash())
"""


def test_manifest_hash_identical_across_processes_and_hash_seeds():
    outs = set()
    for seed in ("0", "1", "42"):
        env = {**os.environ, "PYTHONHASHSEED": seed,
               "PYTHONPATH": os.pathsep.join([str(ROOT / "src"),
                                              str(ROOT / "tests")])}
        r = subprocess.run([sys.executable, "-c", _CHILD], capture_output=True,
                           text=True, env=env, cwd=ROOT)
        assert r.returncode == 0, r.stderr
        outs.add(r.stdout.strip())
    assert len(outs) == 1, outs
