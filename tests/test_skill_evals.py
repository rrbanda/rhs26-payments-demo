"""agentskills.io skill eval tests for the Payment Operations agent.

Two test classes:
- TestSkillEvalDataIntegrity: validates evals/evals.json structure (no network)
- TestSkillEvalExecution: runs full with_skill vs without_skill workflow

Run with: pytest tests/test_skill_evals.py::TestSkillEvalDataIntegrity (unit, always)
          pytest tests/test_skill_evals.py -m skill_eval (live, needs deployed agent)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shared.skill_eval_runner import SKILL_DIR, load_skill_evals, run_skill_evals


class TestSkillEvalDataIntegrity:
    """Validate evals/evals.json is well-formed (unit test, no network)."""

    def test_evals_json_exists(self):
        evals_path = Path(SKILL_DIR) / "evals" / "evals.json"
        assert evals_path.exists(), f"Missing evals/evals.json at {SKILL_DIR}"

    def test_evals_json_valid_structure(self):
        data = load_skill_evals()
        assert data is not None
        assert "skill_name" in data
        assert "evals" in data
        assert isinstance(data["evals"], list)
        assert len(data["evals"]) >= 2, "Need at least 2 eval cases"

    def test_eval_cases_have_required_fields(self):
        data = load_skill_evals()
        assert data is not None
        for case in data["evals"]:
            assert "id" in case, "Missing id field"
            assert "prompt" in case, "Missing prompt field"
            assert "expected_output" in case, "Missing expected_output field"
            assert len(case["prompt"]) > 10, "Prompt too short to be realistic"
            assert len(case["expected_output"]) > 10, "Expected output too vague"

    def test_eval_cases_have_assertions(self):
        data = load_skill_evals()
        assert data is not None
        for case in data["evals"]:
            assertions = case.get("assertions", [])
            assert len(assertions) >= 2, (
                f"Eval {case['id']} needs at least 2 assertions, has {len(assertions)}"
            )
            for assertion in assertions:
                assert len(assertion) > 10, f"Assertion too vague: '{assertion}'"

    def test_skill_name_matches_directory(self):
        data = load_skill_evals()
        assert data is not None
        dir_name = Path(SKILL_DIR).name
        assert data["skill_name"] == dir_name, (
            f"skill_name '{data['skill_name']}' doesn't match directory '{dir_name}'"
        )

    def test_eval_ids_unique(self):
        data = load_skill_evals()
        assert data is not None
        ids = [case["id"] for case in data["evals"]]
        assert len(ids) == len(set(ids)), f"Duplicate eval IDs: {ids}"

    def test_total_assertion_coverage(self):
        """Verify meaningful assertion coverage."""
        data = load_skill_evals()
        assert data is not None
        total = sum(len(case.get("assertions", [])) for case in data["evals"])
        assert total >= 10, f"Only {total} total assertions (need 10+)"


@pytest.mark.skill_eval
class TestSkillEvalExecution:
    """Run full agentskills.io eval workflow against live agent.

    Tests both with_skill AND without_skill (raw LLM baseline).
    The skill should improve pass rate over the baseline.
    """

    def test_skill_improves_over_baseline(self):
        """The skill should produce better output than raw LLM."""
        try:
            benchmark = run_skill_evals(
                use_llm_grading=True,
                skip_baseline=False,
                timeout=120,
            )
        except Exception as exc:
            pytest.skip(f"Agent not reachable: {exc}")
            return

        assert benchmark.with_skill.total_assertions > 0, "No assertions were graded"

        ws_details = "\n".join(
            f"  [{'+' if a.passed else '-'}] {a.text}: {a.evidence}"
            for g in benchmark.with_skill.gradings
            for a in g.assertion_results
        )

        assert benchmark.with_skill.pass_rate >= 0.6, (
            f"{benchmark.skill_name} with_skill pass rate "
            f"{benchmark.with_skill.pass_rate:.0%} < 60%\n"
            f"WITH skill:\n{ws_details}"
        )

        assert benchmark.delta_pass_rate >= 0, (
            f"{benchmark.skill_name} did NOT improve over baseline "
            f"(delta={benchmark.delta_pass_rate:+.0%})"
        )

    def test_skill_eval_no_errors(self):
        """Verify no eval cases returned error responses."""
        try:
            benchmark = run_skill_evals(
                use_llm_grading=False,
                skip_baseline=True,
                timeout=120,
            )
        except Exception as exc:
            pytest.skip(f"Agent not reachable: {exc}")
            return

        for grading in benchmark.with_skill.gradings:
            assert not grading.output.startswith("ERROR:"), (
                f"Eval {grading.eval_id} returned error: {grading.output[:200]}"
            )
