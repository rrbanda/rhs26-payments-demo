# Payment Operations Agent — Demo Narrative

**Session**: Payments, Reimagined — Wed May 13, B404
**Segment**: Raghu — Agents at the Seam (~12 min, starting ~12:10)
**URL**: https://payment-ops-rhs26-payments-demo.apps.cluster-6crhb.6crhb.sandbox1011.opentlc.com

---

## Structure: TELL → SHOW → TELL

Each beat follows the same rhythm: frame what you're about to show (TELL), do it live (SHOW), then land the point (TELL).

---

## Beat 1 — Frame the Seam (1 min)

### TELL

> "Phil just walked you through where the cost actually concentrates in payments — the operational seams. Exception handling, repairs, sanctions triage. The work that sits *between* the platforms.
>
> What I'm going to show you is one of those seams, live. A payment exception repair workflow. An agent that sits at the boundary between the payment gateway, the settlement system, the sanctions screening engine, and a fraud model — and does the diagnosis work that today takes an analyst 30 to 45 minutes per exception.
>
> This is built with Google's Agent Development Kit running on OpenShift. The tools the agent calls are mock implementations today — same signatures as the real APIs, returning realistic data. The point isn't the mock data. The point is the *pattern*: an agent with clear boundaries, supervised by humans, earning trust through evidence."

*Open the browser to the ADK Dev UI. The chat interface should be visible with `payment_ops` selected.*

---

## Beat 2 — The Exception Queue (1 min)

### TELL

> "Let's start where an operator starts their day — the exception queue."

### SHOW

**Type**: `Show me today's exception queue.`

*Agent calls `get_exception_queue` and returns 4 exceptions.*

### TELL

> "Four exceptions, four different types. A missing BIC — that's a data quality issue. An amount mismatch — that's a reconciliation break. A sanctions screening hold — compliance. A duplicate payment — dedup logic. Each one comes from a different system, each one needs different context to resolve. Today, an operator opens four different screens in four different applications to work one of these. Let's pick the first one."

---

## Beat 3 — Multi-System Diagnosis (3 min)

### TELL

> "Watch what happens when I ask the agent to diagnose. It's going to reach into multiple systems — just like an analyst would, but in seconds, not minutes."

### SHOW

**Type**: `Diagnose exception EXC-2024-0847. Show me your full diagnosis with all evidence before recommending any action.`

*Agent calls 5-6 tools in sequence. The Events panel on the right shows each tool call in real time.*

### TELL (while the agent is working, narrate the right panel)

> "Look at what's happening on the right side. The agent just pulled the exception detail from the exception management system. Now it's retrieving the original SWIFT MT103 message — that's the actual payment instruction. It found that field 57A — the beneficiary bank BIC — is empty. That's the root cause.
>
> Now it's looking up the counterparty. The beneficiary has a German IBAN — DE89 — so the agent resolves the BIC from the IBAN bank identifier and confirms the bank is an active SWIFT member.
>
> Next: fraud score. The ML model scores this at 0.03 — essentially zero risk. And finally, it checks repair history — this pattern, missing BIC, has been resolved successfully 97% of the time over the last 147 cases. Average automated resolution: 4 minutes. Average manual resolution: 38 minutes.
>
> That's five systems, correlated, with a diagnosis, in under 15 seconds."

*Point to the structured JSON output in the chat.*

> "The agent presents a structured diagnosis: root cause, evidence chain, fraud risk, recommended action, confidence level, and whether it needs human approval. This isn't a black box — every conclusion is traceable to a specific tool call and a specific data point."

---

## Beat 4 — Human in the Loop (2 min)

### TELL

> "Now here's the key part. The agent doesn't just fix it. It *recommends* and *waits*. This is what we call Assist mode — the agent does the investigation, the human makes the call."

### SHOW

**Type**: `Approved. Submit the repair for EXC-2024-0847.`

*Agent calls `submit_repair` and returns confirmation with audit trail.*

### TELL

> "The repair is submitted with a full audit trail — timestamp, operator ID, action taken, evidence cited. It's queued for the 15-minute SLA review. Every action is logged, every decision is traceable. That's not optional in regulated environments — that's table stakes.
>
> What just took us 30 seconds end-to-end? That's a 38-minute manual process compressed to under a minute, with better evidence documentation than most analysts produce."

---

## Beat 5 — Earning Autonomy (2 min)

### TELL (no demo for this beat — narrate over the screen)

> "So you might ask: if the agent gets it right 97% of the time, why does a human still need to approve?
>
> The answer is: *today* they do. But the architecture supports a progression.
>
> Level one — Assist — is what you just saw. Agent investigates, human decides. This is where you start.
>
> Level two — Supervised. The agent executes the repair automatically for known patterns. The human reviews *after the fact*. You get there after 30 days of shadow mode with 95% or better accuracy, and a compliance sign-off.
>
> Level three — Autonomous. The agent handles the pattern end-to-end. Humans monitor via dashboards, not individual cases.
>
> The critical thing: this progression happens *per exception type*, not as a blanket switch. Missing BIC auto-repair might reach level three. Sanctions decisions stay at level one forever — that's policy, not technology.
>
> This is how you build trust in regulated environments. You don't deploy AI and hope. You deploy it in assist mode, you measure, you build evidence, and you expand scope based on data."

---

## Beat 6 — Same Pattern, Different Seam (2 min)

### TELL

> "One more thing. The same agent, the same architecture, handles a completely different type of exception. Let me show you."

### SHOW

**Type**: `Now check the sanctions hold on EXC-2024-0853. Full diagnosis please.`

*Agent calls `get_exception_detail`, `check_sanctions_status`, `get_payment_message`, `get_fraud_score`, `get_repair_history`.*

### TELL (while agent works)

> "Different seam now. This is a sanctions screening hold. The beneficiary name — Ahmed Holdings LLC — triggered an OFAC partial match. The agent screens the entity, finds a fuzzy name match with score 0.31 — 'Ahmed' versus 'Ahmad', a common transliteration variant. Different jurisdictions — Abu Dhabi versus Dubai. No matching aliases or addresses.
>
> The agent assesses this as a likely false positive. And 91% of sanctions holds historically are exactly that. But — and this is critical —"

*Point to the compliance note in the response.*

> "The agent explicitly says: compliance officer sign-off is required. Policy CP-BSA-012. It will not release this hold on its own. It provides the analysis, the evidence, the recommendation. The compliance officer makes the call.
>
> That's the same pattern. Different seam, different data sources, different compliance constraints — but the same architecture: agent at the boundary, tools reaching into systems, human in the loop where policy requires it."

---

## Close (1 min)

### TELL

> "So what did you just see?
>
> An agent sitting at the operational seam that Phil described — the expensive space between the platforms. It correlates data from five systems in seconds. It cites evidence for every conclusion. It respects compliance boundaries. And it creates an audit trail that's better than what most manual processes produce today.
>
> The mock tools you saw return realistic data. In production, you swap the function body — the signature stays the same. The agent doesn't know the difference. The same skill definition, the same ADK patterns, the same A2A protocol — running on OpenShift, deployed through the same pipeline as any other microservice.
>
> This is what's now possible. Not next year. Now. And it starts with picking one seam, instrumenting it, proving value, and expanding from there."

---

## Emergency Fallback

If the agent or LLM is slow or unresponsive:

> "The agent is thinking — it's calling five different systems. While it works, let me tell you what it's doing..."

Then narrate the tool calls from the Events panel. The story holds either way.

If the UI is completely down, switch to narrating the architecture:

> "Let me walk you through what the agent does, using the same data it would show you live..."

Use the mock exception scenarios table from the README.

---

## Key Numbers to Remember

| Fact | Number |
|------|--------|
| Manual resolution time (missing BIC) | 38 minutes |
| Agent-assisted resolution time | Under 1 minute |
| Historical auto-repair success rate | 97% over 147 cases |
| Fraud score for EXC-0847 | 0.03 (low) |
| Sanctions match score for EXC-0853 | 0.31 (fuzzy) |
| False positive rate for sanctions holds | 91% |
| Shadow mode requirement | 30 days, >= 95% accuracy |
| Tools called per diagnosis | 5-6 |

---

## Prompts (copy-paste ready)

```
Show me today's exception queue.
```

```
Diagnose exception EXC-2024-0847. Show me your full diagnosis with all evidence before recommending any action.
```

```
Approved. Submit the repair for EXC-2024-0847.
```

```
Now check the sanctions hold on EXC-2024-0853. Full diagnosis please.
```
