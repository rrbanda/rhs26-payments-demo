"""Shared fixtures and marker configuration for rhs26-payments-demo tests."""

from __future__ import annotations

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "unit: unit tests (no network)")
    config.addinivalue_line("markers", "eval: ADK agent eval tests (need live LLM)")
    config.addinivalue_line("markers", "skill_eval: agentskills.io skill eval tests (need live agent)")


def pytest_collection_modifyitems(items):
    for item in items:
        path = str(item.fspath)
        if "test_agent_evals" in path:
            item.add_marker(pytest.mark.eval)
        elif "test_skill_evals" in path and "TestSkillEvalExecution" in item.nodeid:
            item.add_marker(pytest.mark.skill_eval)
        else:
            item.add_marker(pytest.mark.unit)
