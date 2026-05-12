# Demo Handoff Guide

Everything you need to run the Payments demo. No secrets in this file.

---

## Live Demo URL

**ADK Web UI**: https://payment-ops-rhs26-payments-demo.apps.cluster-6crhb.6crhb.sandbox1011.opentlc.com

Open in any browser. The agent is `payment_ops`. The chat interface is on the left, tool call traces on the right.

---

## Pre-Demo Checklist (5 min before)

1. Open the URL above in your browser
2. Confirm the ADK Dev UI loads and shows `payment_ops` in the sidebar
3. Click "NEW SESSION" to start fresh
4. Verify the LLM is responding -- type "hello" and confirm you get a reply
5. If the pod is down, redeploy (see Recovery section below)
6. Have this file open on a second screen or printed for reference

---

## The 4 Prompts (copy-paste ready)

### Prompt 1 -- Exception Queue

```
Show me today's exception queue.
```

**Expected**: Agent calls `get_exception_queue` and lists 4 exceptions:
- EXC-2024-0847: Missing BIC, high priority, USD 125K
- EXC-2024-0851: Amount Mismatch, critical priority, USD 50K
- EXC-2024-0853: Sanctions Hold, high priority, EUR 87.5K
- EXC-2024-0856: Duplicate Payment, medium priority, GBP 23.75K

**Response time**: ~3-5 seconds

---

### Prompt 2 -- Diagnose Missing BIC

```
Diagnose exception EXC-2024-0847. Show me your full diagnosis with all evidence before recommending any action.
```

**Expected**: Agent calls 5-7 tools (visible in Events panel on right):
- `get_exception_detail` -- pulls exception record
- `get_payment_message` -- retrieves SWIFT MT103, finds field :57A empty
- `get_counterparty_info` -- resolves German BIC from IBAN (DEUTDEFF or COBADEFF)
- `get_fraud_score` -- returns 0.03 (low risk)
- `get_repair_history` -- 97% success rate over 147 cases

Returns structured diagnosis with evidence chain, confidence level, and recommended action `add_bic`.

**Response time**: ~10-20 seconds

---

### Prompt 3 -- Approve and Submit Repair

```
Approved. Submit the repair for EXC-2024-0847.
```

**Expected**: Agent calls `submit_repair` and returns audit record with:
- Timestamp
- Action: add_bic
- Approval status: pending_human_review
- Audit ID

**Response time**: ~3-5 seconds

---

### Prompt 4 -- Sanctions Triage

```
Now check the sanctions hold on EXC-2024-0853. Full diagnosis please.
```

**Expected**: Agent calls:
- `get_exception_detail` -- sanctions_hold type
- `check_sanctions_status` -- fuzzy match 0.31, Ahmed vs Ahmad
- `get_payment_message` -- confirms beneficiary details
- `get_fraud_score` -- 0.18 (low)
- `get_repair_history` -- 91% released as false positives

Recommends `release_false_positive` but **explicitly states compliance officer sign-off required (CP-BSA-012)**. Will NOT auto-submit.

**Response time**: ~15-25 seconds

---

## What to Say at Each Step

See [DEMO_NARRATIVE.md](DEMO_NARRATIVE.md) for the full Tell-Show-Tell talk track with technical depth. Key points to hit:

| Beat | Key Message |
|------|-------------|
| Queue | "Four types, four systems, four different screens today -- the agent sees them all in one place" |
| Diagnosis | "Five systems correlated in under 15 seconds -- narrate the Events panel as tools appear" |
| Approval | "Agent recommends and waits -- Assist mode. 38-minute manual process in under a minute" |
| Autonomy (narrate) | "Per-exception-type progression: Assist, Supervised, Autonomous. 30-day shadow mode. Sanctions stays at Assist forever -- that's policy" |
| Sanctions | "Same agent, different seam, different compliance constraints. Agent says compliance sign-off required and will not submit on its own" |

---

## Key Numbers

| Fact | Number |
|------|--------|
| Manual resolution (missing BIC) | 38 minutes |
| Agent-assisted resolution | Under 1 minute |
| Auto-repair success rate | 97% over 147 cases |
| Fraud score (EXC-0847) | 0.03 |
| Sanctions match score (EXC-0853) | 0.31 fuzzy |
| Sanctions false positive rate | 91% |
| Shadow mode requirement | 30 days, >= 95% accuracy |

---

## Recovery

### If the agent is slow

> "The agent is thinking -- it's calling five different systems. While it works, let me tell you what it's doing..."

Narrate the tool calls from the Events panel. The story holds.

### If the pod is down

From a terminal with `oc` logged in:

```bash
# Check pod status
oc get pods -n rhs26-payments-demo

# If no pods running, restart
oc rollout restart deployment/payment-ops -n rhs26-payments-demo

# Watch it come back
oc rollout status deployment/payment-ops -n rhs26-payments-demo

# Verify
curl -sk https://payment-ops-rhs26-payments-demo.apps.cluster-6crhb.6crhb.sandbox1011.opentlc.com/
```

### If the cluster is unreachable

Run locally as backup:

```bash
cd rhs26-payments-demo
pip install -e .
PYTHONPATH=. LLM_MODEL_ID="openai/gemini/models/gemini-2.5-flash" \
  LLM_API_BASE="https://llamastack-llamastack.apps.cluster-6crhb.6crhb.sandbox1011.opentlc.com/v1" \
  LLAMASTACK_API_KEY="not-needed" \
  NEO4J_PASSWORD="notused" \
  adk web --host 0.0.0.0 --port 8006 --session_service_uri memory:// agents
```

Then open http://localhost:8006.

### If the LLM endpoint is down

The demo narrative is designed to work as a walkthrough without a live agent. Use the mock exception table from the README and narrate the architecture. The technical content is in the TELL, not just the SHOW.

---

## Source Code

**GitHub**: https://github.com/rrbanda/rhs26-payments-demo

**OpenShift Project**: `rhs26-payments-demo`

**Tech Stack**:
- Google ADK (Agent Development Kit) with agentskills.io skills
- A2A protocol (JSON-RPC agent interoperability)
- Gemini 2.5 Flash via LlamaStack on OpenShift
- 8 mock payment tools (no real payment systems)
- Python 3.12, deployed as a container
