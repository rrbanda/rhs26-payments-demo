# Payments, Reimagined — Agent at the Operational Seam

**Red Hat Summit 2026 Demo** | Wed May 13, B404

A Google ADK agent that diagnoses and repairs payment exceptions by correlating data across SWIFT, settlement, sanctions, and fraud systems. Built with [agentskills.io](https://agentskills.io) skill patterns and served via the A2A (Agent-to-Agent) protocol.

## What This Demonstrates

An AI agent sitting at the **operational seam** between payment platforms — the expensive, manual space where exceptions concentrate. The agent:

1. Reviews a queue of payment exceptions (missing BIC, amount mismatch, sanctions hold, duplicate)
2. Pulls the original SWIFT MT103 message and cross-references counterparty, sanctions, and fraud data
3. Checks historical repair patterns and ML fraud scores
4. Presents a structured diagnosis with evidence and confidence level
5. Recommends a repair action — but **waits for human approval** before executing

All payment tools return **mock data** — no real payment systems required. The LLM is the only live dependency.

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Copy env and edit if needed
cp .env.example .env

# Run locally
PYTHONPATH=. uvicorn agents.payment_ops.server:app --host 0.0.0.0 --port 8006

# Test health
curl http://localhost:8006/healthz

# Agent card (A2A discovery)
curl http://localhost:8006/.well-known/agent-card.json

# Send a prompt via A2A JSON-RPC
curl -X POST http://localhost:8006/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "messageId": "msg-1",
        "parts": [{"kind": "text", "text": "Show me today'\''s exception queue."}]
      }
    }
  }'
```

Or use the ADK dev UI:
```bash
adk web agents/payment_ops
```

## Demo Script (12 minutes)

| Beat | Prompt | What Happens |
|------|--------|-------------|
| 1. Frame the seam | "Show me today's exception queue" | Agent lists 4 pending exceptions with priorities |
| 2. Integration point | "Diagnose exception EXC-2024-0847" | Agent pulls data from 5 mock systems, identifies missing BIC |
| 3. Predictive models | (automatic) | Agent checks fraud score (0.03) and repair history (97% success) |
| 4. Human in the loop | "Approved. Submit the repair." | Agent submits repair with audit trail |
| 5. Earning autonomy | (narrate) | Shadow mode, measured accuracy, gated expansion |
| 6. Pattern generalizes | "Check the sanctions hold on EXC-2024-0853" | Same agent triages sanctions false positive |

## Mock Exception Scenarios

| ID | Type | Root Cause | Agent Action |
|----|------|-----------|-------------|
| EXC-2024-0847 | Missing BIC | :57A field empty in MT103 | Looks up DEUTDEFF, recommends BIC repair |
| EXC-2024-0851 | Amount Mismatch | USD 50K vs 5K | Flags discrepancy, escalates (policy CP-PAY-007) |
| EXC-2024-0853 | Sanctions Hold | OFAC fuzzy match (0.31) | Identifies false positive, notes compliance sign-off required |
| EXC-2024-0856 | Duplicate Payment | Same ref submitted twice | Recommends reject, links to original |

## Architecture

```
agents/payment_ops/
├── agent.py                    # ADK Agent + SkillToolset + 8 mock tools
├── server.py                   # A2A server via to_a2a() on port 8006
├── skills/exception-repair/
│   ├── SKILL.md                # agentskills.io repair methodology
│   └── references/
│       ├── swift-message-formats.md
│       ├── repair-procedures.md
│       └── iso20022-error-codes.md
└── evals/                      # ADK eval datasets (3 scenarios)

shared/
├── payment_tools.py            # 8 mock tools (SWIFT, sanctions, fraud, repair)
├── model_config.py             # Config loader (config.yaml + env vars)
└── health.py                   # /healthz + /readyz endpoints
```

## Deploy to OpenShift via Kagenti

```bash
# Prereqs: oc login, Kagenti installed
scripts/deploy_kagenti.sh
```

Or via container build:
```bash
docker build -t payment-ops -f Dockerfile .
docker run -p 8006:8000 -e NEO4J_PASSWORD=notused payment-ops
```

## Run Tests

```bash
NEO4J_PASSWORD=notused pytest tests/ -v
```

## License

Apache 2.0
