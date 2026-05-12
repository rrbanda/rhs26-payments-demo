"""agentskills.io skill eval runner for the Payment Operations agent.

Implements the full agentskills.io evaluation workflow:
1. Run each eval case WITH the skill (agent with SKILL.md loaded)
2. Run each eval case WITHOUT the skill (raw LLM, no skill instructions)
3. Grade assertions against both outputs
4. Compute delta (does the skill actually improve output?)
5. Produce grading.json, timing.json, benchmark.json per the spec
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

import requests

from shared.model_config import load_config

logger = logging.getLogger(__name__)

SKILL_DIR = "agents/payment_ops/skills/exception-repair"
AGENT_PORT = 8006


@dataclass
class AssertionResult:
    text: str
    passed: bool
    evidence: str


@dataclass
class GradingResult:
    eval_id: int
    prompt: str
    output: str
    assertion_results: list[AssertionResult]
    passed: int = 0
    failed: int = 0
    total: int = 0
    pass_rate: float = 0.0


@dataclass
class TimingResult:
    eval_id: int
    duration_ms: float
    total_tokens: int = 0
    response_length: int = 0


@dataclass
class ConfigResult:
    gradings: list[GradingResult] = field(default_factory=list)
    timings: list[TimingResult] = field(default_factory=list)
    pass_rate: float = 0.0
    mean_duration_ms: float = 0.0
    total_assertions: int = 0
    passed_assertions: int = 0


@dataclass
class BenchmarkResult:
    skill_name: str
    total_evals: int
    with_skill: ConfigResult
    without_skill: ConfigResult
    delta_pass_rate: float = 0.0
    delta_duration_ms: float = 0.0


def _send_a2a_task(base_url: str, message: str, timeout: int = 120) -> tuple[str, float]:
    """Send a prompt to the agent via A2A and return (response_text, duration_ms)."""
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "messageId": str(uuid.uuid4()),
                "parts": [{"kind": "text", "text": message}],
            },
        },
    }

    start = time.monotonic()
    resp = requests.post(base_url, json=payload, timeout=timeout)
    duration_ms = (time.monotonic() - start) * 1000
    resp.raise_for_status()

    data = resp.json()
    result = data.get("result", {})

    artifacts = result.get("artifacts", [])
    if artifacts:
        parts = artifacts[0].get("parts", [])
        if parts:
            return parts[0].get("text", ""), duration_ms

    status_msg = result.get("status", {}).get("message", {})
    for part in status_msg.get("parts", []):
        if part.get("kind") == "text" and part.get("text"):
            return part["text"], duration_ms

    return json.dumps(result), duration_ms


def _send_raw_llm(prompt: str, timeout: int = 60) -> tuple[str, float]:
    """Send prompt directly to raw LLM (no skill, no agent framework)."""
    cfg = load_config()["model"]["agent"]
    api_base = cfg["api_base"].rstrip("/")
    model_id = cfg["id"]
    api_key = cfg.get("api_key", "")

    start = time.monotonic()
    try:
        resp = requests.post(
            f"{api_base}/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json={
                "model": model_id,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
            },
            timeout=timeout,
        )
        duration_ms = (time.monotonic() - start) * 1000
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return content, duration_ms
    except Exception as exc:
        duration_ms = (time.monotonic() - start) * 1000
        logger.warning("Raw LLM call failed: %s", exc)
        return f"ERROR: {exc}", duration_ms


def _grade_assertions_with_llm(
    prompt: str,
    expected_output: str,
    actual_output: str,
    assertions: list[str],
) -> list[AssertionResult]:
    """Use LLM-as-judge to grade each assertion against actual output."""
    cfg = load_config()["model"]["agent"]
    api_base = cfg["api_base"].rstrip("/")
    model_id = cfg["id"]
    api_key = cfg.get("api_key", "")

    grading_prompt = (
        "You are an evaluation judge. Grade each assertion against "
        "the actual output.\n\n"
        f"PROMPT: {prompt}\n\n"
        f"EXPECTED OUTPUT: {expected_output}\n\n"
        f"ACTUAL OUTPUT: {actual_output}\n\n"
        "ASSERTIONS TO GRADE:\n"
    )
    for i, assertion in enumerate(assertions, 1):
        grading_prompt += f"{i}. {assertion}\n"

    grading_prompt += (
        "\nFor each assertion, respond with EXACTLY this JSON "
        "format (no other text):\n"
        "[\n"
        '  {"text": "...", "passed": true/false, '
        '"evidence": "specific quote or observation from output"}\n'
        "]\n"
        "Be strict: require concrete evidence for a PASS. "
        "If the output lacks clear evidence, mark FAIL."
    )

    try:
        resp = requests.post(
            f"{api_base}/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json={
                "model": model_id,
                "messages": [{"role": "user", "content": grading_prompt}],
                "temperature": 0.0,
            },
            timeout=60,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

        start = content.find("[")
        end = content.rfind("]") + 1
        if start >= 0 and end > start:
            parsed = json.loads(content[start:end])
            return [
                AssertionResult(
                    text=item.get("text", assertions[i] if i < len(assertions) else ""),
                    passed=bool(item.get("passed", False)),
                    evidence=item.get("evidence", ""),
                )
                for i, item in enumerate(parsed)
            ]
    except Exception as exc:
        logger.warning("LLM grading failed, falling back to heuristic: %s", exc)

    return _grade_assertions_heuristic(actual_output, assertions)


def _grade_assertions_heuristic(
    actual_output: str,
    assertions: list[str],
) -> list[AssertionResult]:
    """Fallback heuristic grading when LLM is unavailable."""
    results = []
    output_lower = actual_output.lower()

    for assertion in assertions:
        assertion_lower = assertion.lower()
        noise = {
            "should", "must", "the", "output", "response", "includes",
            "contains", "each", "with", "that", "from", "have", "this",
            "and", "for", "are",
        }
        keywords = [w for w in assertion_lower.split() if len(w) > 3 and w not in noise]
        matches = [k for k in keywords if k in output_lower]
        passed = len(matches) >= max(1, len(keywords) // 3)
        evidence = f"Keyword match: {matches}" if passed else f"No keyword match from: {keywords}"

        results.append(AssertionResult(text=assertion, passed=passed, evidence=evidence))

    return results


def _run_config(
    eval_cases: list[dict],
    send_fn,
    *,
    use_llm_grading: bool = True,
    timeout: int = 120,
) -> ConfigResult:
    """Run all eval cases through a send function and grade them."""
    gradings: list[GradingResult] = []
    timings: list[TimingResult] = []

    for case in eval_cases:
        eval_id = case["id"]
        prompt = case["prompt"]
        expected_output = case.get("expected_output", "")
        assertions = case.get("assertions", [])

        logger.info("  Eval %d: %s...", eval_id, prompt[:50])

        try:
            output, duration_ms = send_fn(prompt, timeout)
        except Exception as exc:
            logger.error("  Eval %d failed: %s", eval_id, exc)
            output = f"ERROR: {exc}"
            duration_ms = 0.0

        timings.append(
            TimingResult(
                eval_id=eval_id,
                duration_ms=duration_ms,
                response_length=len(output),
            )
        )

        if assertions:
            if use_llm_grading:
                assertion_results = _grade_assertions_with_llm(
                    prompt, expected_output, output, assertions
                )
            else:
                assertion_results = _grade_assertions_heuristic(output, assertions)
        else:
            assertion_results = []

        passed = sum(1 for r in assertion_results if r.passed)
        failed = len(assertion_results) - passed

        gradings.append(
            GradingResult(
                eval_id=eval_id,
                prompt=prompt,
                output=output,
                assertion_results=assertion_results,
                passed=passed,
                failed=failed,
                total=len(assertion_results),
                pass_rate=passed / len(assertion_results) if assertion_results else 0.0,
            )
        )

    total = sum(g.total for g in gradings)
    passed_total = sum(g.passed for g in gradings)
    overall_rate = passed_total / total if total else 0.0
    mean_dur = sum(t.duration_ms for t in timings) / len(timings) if timings else 0.0

    return ConfigResult(
        gradings=gradings,
        timings=timings,
        pass_rate=overall_rate,
        mean_duration_ms=mean_dur,
        total_assertions=total,
        passed_assertions=passed_total,
    )


def load_skill_evals() -> dict | None:
    """Load evals/evals.json from the skill directory."""
    evals_path = Path(SKILL_DIR) / "evals" / "evals.json"
    if not evals_path.exists():
        return None
    with open(evals_path) as f:
        return json.load(f)


def run_skill_evals(
    *,
    base_url: str | None = None,
    use_llm_grading: bool = True,
    timeout: int = 120,
    skip_baseline: bool = False,
) -> BenchmarkResult:
    """Run the full agentskills.io eval workflow.

    1. Run each eval WITH the skill (via A2A to the agent)
    2. Run each eval WITHOUT the skill (raw LLM, no instructions)
    3. Grade assertions against both outputs
    4. Compute delta proving the skill adds value
    """
    evals_data = load_skill_evals()
    if not evals_data:
        raise FileNotFoundError(f"No evals/evals.json found at {SKILL_DIR}")

    skill_name = evals_data["skill_name"]
    eval_cases = evals_data["evals"]

    if base_url is None:
        base_url = f"http://localhost:{AGENT_PORT}"

    logger.info("=== WITH SKILL (agent) ===")
    with_skill = _run_config(
        eval_cases,
        lambda prompt, t: _send_a2a_task(base_url, prompt, timeout=t),
        use_llm_grading=use_llm_grading,
        timeout=timeout,
    )

    if skip_baseline:
        without_skill = ConfigResult()
        logger.info("=== WITHOUT SKILL: skipped ===")
    else:
        logger.info("=== WITHOUT SKILL (raw LLM baseline) ===")
        without_skill = _run_config(
            eval_cases,
            lambda prompt, t: _send_raw_llm(prompt, timeout=t),
            use_llm_grading=use_llm_grading,
            timeout=timeout,
        )

    delta_pass = with_skill.pass_rate - without_skill.pass_rate
    delta_dur = with_skill.mean_duration_ms - without_skill.mean_duration_ms

    return BenchmarkResult(
        skill_name=skill_name,
        total_evals=len(eval_cases),
        with_skill=with_skill,
        without_skill=without_skill,
        delta_pass_rate=delta_pass,
        delta_duration_ms=delta_dur,
    )


def save_results(
    benchmark: BenchmarkResult,
    output_dir: str | Path,
    iteration: int = 1,
) -> None:
    """Save results in agentskills.io workspace structure."""
    base = Path(output_dir) / f"iteration-{iteration}"
    base.mkdir(parents=True, exist_ok=True)

    for config_name, config in [
        ("with_skill", benchmark.with_skill),
        ("without_skill", benchmark.without_skill),
    ]:
        if not config.gradings:
            continue
        for grading in config.gradings:
            eval_dir = base / f"eval-{grading.eval_id}" / config_name
            eval_dir.mkdir(parents=True, exist_ok=True)
            grading_data = {
                "assertion_results": [asdict(r) for r in grading.assertion_results],
                "summary": {
                    "passed": grading.passed,
                    "failed": grading.failed,
                    "total": grading.total,
                    "pass_rate": grading.pass_rate,
                },
            }
            with open(eval_dir / "grading.json", "w") as f:
                json.dump(grading_data, f, indent=2)
        for timing in config.timings:
            eval_dir = base / f"eval-{timing.eval_id}" / config_name
            eval_dir.mkdir(parents=True, exist_ok=True)
            with open(eval_dir / "timing.json", "w") as f:
                json.dump(asdict(timing), f, indent=2)

    benchmark_data = {
        "run_summary": {
            "with_skill": {
                "pass_rate": benchmark.with_skill.pass_rate,
                "time_ms": {"mean": benchmark.with_skill.mean_duration_ms},
                "assertions": {
                    "total": benchmark.with_skill.total_assertions,
                    "passed": benchmark.with_skill.passed_assertions,
                },
            },
            "without_skill": {
                "pass_rate": benchmark.without_skill.pass_rate,
                "time_ms": {"mean": benchmark.without_skill.mean_duration_ms},
                "assertions": {
                    "total": benchmark.without_skill.total_assertions,
                    "passed": benchmark.without_skill.passed_assertions,
                },
            },
            "delta": {
                "pass_rate": benchmark.delta_pass_rate,
                "time_ms": benchmark.delta_duration_ms,
            },
        },
    }
    with open(base / "benchmark.json", "w") as f:
        json.dump(benchmark_data, f, indent=2)

    logger.info(
        "Results saved to %s\n"
        "  with_skill:    %d/%d assertions (%.0f%%)\n"
        "  without_skill: %d/%d assertions (%.0f%%)\n"
        "  delta:         %+.0f%% pass rate",
        base,
        benchmark.with_skill.passed_assertions,
        benchmark.with_skill.total_assertions,
        benchmark.with_skill.pass_rate * 100,
        benchmark.without_skill.passed_assertions,
        benchmark.without_skill.total_assertions,
        benchmark.without_skill.pass_rate * 100,
        benchmark.delta_pass_rate * 100,
    )
