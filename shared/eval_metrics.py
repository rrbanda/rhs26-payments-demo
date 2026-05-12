"""Custom ADK evaluation metrics for the Payment Operations agent.

Provides a tool_coverage metric that verifies the agent uses at least one
domain-specific payment tool (not just SkillToolset framework tools like
load_skill or load_skill_resource).
"""

from __future__ import annotations

import statistics

from google.adk.evaluation.conversation_scenarios import ConversationScenario
from google.adk.evaluation.eval_case import IntermediateData, Invocation
from google.adk.evaluation.eval_metrics import EvalMetric, EvalStatus
from google.adk.evaluation.evaluator import EvaluationResult, PerInvocationResult

DOMAIN_TOOLS = frozenset(
    {
        "get_exception_queue",
        "get_exception_detail",
        "get_payment_message",
        "get_counterparty_info",
        "check_sanctions_status",
        "get_repair_history",
        "get_fraud_score",
        "submit_repair",
    }
)


def tool_coverage(
    eval_metric: EvalMetric,
    actual_invocations: list[Invocation],
    expected_invocations: list[Invocation] | None,
    conversation_scenario: ConversationScenario | None,
) -> EvaluationResult:
    """Check that the agent invoked at least one domain-specific payment tool.

    Scores 1.0 if any tool call in the invocation matches a known payment
    domain tool, 0.0 otherwise. Catches regressions where the agent stops
    using payment tools and relies only on SkillToolset framework tools.
    """
    per_invocation_results: list[PerInvocationResult] = []

    for invocation in actual_invocations:
        tool_names: set[str] = set()
        idata = invocation.intermediate_data
        if isinstance(idata, IntermediateData) and idata.tool_uses:
            for tool_use in idata.tool_uses:
                if tool_use.name is not None:
                    tool_names.add(tool_use.name)

        used_domain_tool = bool(tool_names & DOMAIN_TOOLS)
        score = 1.0 if used_domain_tool else 0.0
        eval_status = EvalStatus.PASSED if used_domain_tool else EvalStatus.FAILED

        per_invocation_results.append(
            PerInvocationResult(
                actual_invocation=invocation,
                score=score,
                eval_status=eval_status,
            )
        )

    if not per_invocation_results:
        return EvaluationResult(
            overall_score=0.0,
            overall_eval_status=EvalStatus.NOT_EVALUATED,
        )

    scores = [r.score for r in per_invocation_results if r.score is not None]
    average_score = statistics.mean(scores) if scores else 0.0
    threshold = 0.8
    if eval_metric.criterion is not None and eval_metric.criterion.threshold is not None:
        threshold = eval_metric.criterion.threshold
    overall_status = EvalStatus.PASSED if average_score >= threshold else EvalStatus.FAILED

    return EvaluationResult(
        overall_score=average_score,
        overall_eval_status=overall_status,
        per_invocation_results=per_invocation_results,
    )
