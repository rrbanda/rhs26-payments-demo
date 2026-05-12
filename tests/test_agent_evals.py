"""ADK agent evaluation tests for the Payment Operations agent.

Uses Google ADK's AgentEvaluator to validate agent quality:
- Tool trajectory: agent calls the right tools in the right order
- Response quality: agent responses match reference responses (ROUGE-1)

Requires live LLM endpoint. Run with: pytest -m eval
"""

from __future__ import annotations

import logging

import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator

logger = logging.getLogger(__name__)


@pytest.mark.eval
@pytest.mark.asyncio
async def test_agent_eval():
    """Evaluate payment_ops agent tool trajectory and response quality."""
    try:
        await AgentEvaluator.evaluate(
            agent_module="agents.payment_ops",
            eval_dataset_file_path_or_dir="agents/payment_ops/evals/",
            num_runs=1,
        )
    except TypeError as exc:
        if "NoneType" in str(exc):
            pytest.skip(
                f"ADK inference returned None (known ADK bug in local_eval_service.py): {exc}"
            )
        raise
