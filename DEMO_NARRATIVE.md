# Payment Operations Agent — Demo Narrative

**Session**: Payments, Reimagined — Wed May 13, B404
**Segment**: Raghu — Agents at the Seam (~12 min, starting ~12:10)
**URL**: https://payment-ops-rhs26-payments-demo.apps.cluster-6crhb.6crhb.sandbox1011.opentlc.com

---

## Structure: TELL → SHOW → TELL

Each beat follows the same rhythm: frame what you're about to show and why it matters technically (TELL), do it live (SHOW), then land the architectural insight (TELL).

---

## Beat 1 — Frame the Seam (1 min)

### TELL

> "Phil just walked you through where the cost actually concentrates in payments — the operational seams. Exception handling, repairs, sanctions triage. The work that sits *between* the platforms.
>
> What I'm going to show you is one of those seams, live. A payment exception repair workflow powered by an AI agent.
>
> Architecturally, here's what's running. This is a Google ADK agent — that's the Agent Development Kit, Google's open-source framework for building AI agents. The agent is defined using the agentskills.io specification — an open standard for packaging agent capabilities as portable, testable, versionable skill definitions. Think of a skill like an API contract, but for agent behavior: it declares what the agent can do, what tools it needs, and how it should reason through a problem.
>
> The agent is served over the A2A protocol — Agent-to-Agent — which is a JSON-RPC standard for agent interoperability. Any client, any UI, any orchestrator can discover this agent and talk to it.
>
> It's running on OpenShift right now, managed by Kagenti — that's an open-source cloud-native platform for deploying and operating AI agents in production. Kagenti is framework-neutral: it doesn't care whether your agent is built with Google ADK, LangGraph, CrewAI, or anything else. What Kagenti provides is the production infrastructure that agent frameworks don't — lifecycle management, zero-trust security, networking, and observability. Think of it as the Kubernetes-native operations layer for agents.
>
> On this cluster, Kagenti runs a controller that manages agent deployments as Kubernetes workloads. It integrates Keycloak for OAuth/OIDC authentication, so every request to the agent goes through an identity layer. In our Skills Marketplace production setup, it also injects an AuthBridge sidecar — an Envoy-based proxy that handles JWT validation, SPIFFE workload identity, and policy enforcement at the network edge. The health endpoints, the agent card discovery, the A2A protocol endpoint — those all pass through AuthBridge transparently.
>
> For this demo, the agent is deployed as a standard OpenShift container with a Route. In production, Kagenti adds the security and observability layers on top — same agent code, same container, but with identity, auth, tracing, and lifecycle management handled by the platform.
>
> The tools the agent calls are mock implementations today — same function signatures as real payment APIs, returning realistic data. In production you swap the function body; the agent doesn't know the difference. The LLM — Gemini 2.5 Flash, running through a LlamaStack inference endpoint — is the only live system."

*Open the browser to the ADK Dev UI. Point to the interface briefly.*

> "This is the ADK Dev UI. On the left you have the chat — that's where I interact with the agent. On the right, the Events panel — that shows every tool call the agent makes in real time. You'll see the agent's reasoning chain as it happens."

---

## Beat 2 — The Exception Queue (1 min)

### TELL

> "Let's start where a payments operations analyst starts their morning — the exception queue. In any payments shop, this is the backlog of transactions that failed automated processing. They're sitting in a workflow system waiting for human investigation."

### SHOW

**Type**: `Show me today's exception queue.`

*Agent calls `get_exception_queue` and returns 4 exceptions.*

### TELL

> "Four exceptions, each from a different failure domain. Let me walk through them because these are real patterns that Phil's team deals with.
>
> First — a missing BIC. BIC is the Bank Identifier Code — the SWIFT address of a bank. Field 57A in a SWIFT MT103 message. If it's empty or invalid, the payment can't route to the beneficiary's bank. This is the most common exception type — it's a data quality problem at the origination point.
>
> Second — an amount mismatch. The instructed amount doesn't match the settlement amount. USD 50,000 instructed, USD 5,000 settled. Could be a decimal error, could be a partial fill, could be something worse. This is a reconciliation break between the payment instruction system and the settlement engine.
>
> Third — a sanctions screening hold. The beneficiary name triggered a partial match against the OFAC SDN list — that's the U.S. Treasury's Specially Designated Nationals list. The screening engine flagged it; a human has to clear it. This is a compliance exception.
>
> Fourth — a duplicate payment. Same reference, same amount, same beneficiary, submitted twice four hours apart. The dedup engine caught it. Usually an operational error — someone hit send twice — but it needs confirmation.
>
> Each of these comes from a *different* upstream system, needs data from *different* sources to resolve, and has *different* compliance constraints. Today, an analyst opens four different applications to work one of these. Let's pick the first one and see what the agent does."

---

## Beat 3 — Multi-System Diagnosis (3 min)

### TELL

> "I'm going to ask the agent to diagnose this exception. Watch the Events panel on the right — you'll see the agent make a series of tool calls. Each tool represents a different system it's reaching into. This is the key architectural concept: the agent is an *orchestrator* at the seam. It doesn't replace any of the underlying systems. It reaches into them, correlates data across them, and synthesizes a diagnosis."

### SHOW

**Type**: `Diagnose exception EXC-2024-0847. Show me your full diagnosis with all evidence before recommending any action.`

*Agent starts calling tools. The Events panel shows each call in real time.*

### TELL (narrate the Events panel as tool calls appear)

> "First thing the agent does — see `load_skill` in the Events panel. That's the agentskills.io pattern in action. The agent is loading a *skill definition* — a file called SKILL.md that encodes the exception repair methodology. Let me explain what that is, because it's a key concept.
>
> A skill is a portable, versionable specification for how an agent should behave. It's a Markdown file with YAML frontmatter — same idea as a Kubernetes manifest or an OpenAPI spec, but for agent behavior. Our exception-repair skill defines an 8-step diagnostic methodology: review the queue, pull the exception, retrieve the payment message, cross-reference external data, check historical patterns, formulate a diagnosis, recommend an action, present structured output. It also declares compliance constraints — like 'never auto-repair amount mismatches' and 'sanctions decisions require human sign-off.'
>
> The skill has L3 reference documents underneath it — SWIFT message format guides, approved repair procedures, ISO 20022 error code mappings. The agent can read those references at runtime via `load_skill_resource` when it needs field-level detail. Think of the skill as the *methodology* and the references as the *domain knowledge*. Both are version-controlled, testable artifacts — not prompt strings buried in application code.
>
> The agentskills.io spec also defines an eval format. Each skill has test cases — prompt, expected output, assertions. You can measure whether the skill actually improves agent output compared to a raw LLM without the skill. That's how you prove the skill adds value, and it's how you catch regressions when you update the methodology.
>
> Now watch the domain tool calls.
>
> `get_exception_detail` — pulls the full exception record from the exception management system. The agent now knows the type is 'missing_bic', the payment reference, the error code E001, who the originator and beneficiary are.
>
> `get_payment_message` — retrieves the actual SWIFT MT103 — that's the ISO 15022 standard message format for a single customer credit transfer. It's the source of truth for what was instructed. The agent reads the MT103 fields — it finds field 57A, Account With Institution, is empty. That's the missing BIC. The beneficiary is Schmidt Manufacturing GmbH with a German IBAN starting with DE89.
>
> Now it has to *resolve* the BIC. Third call — `get_counterparty_info`. The agent derives candidate BIC codes from the IBAN country code. DE means Germany; the bank code in the IBAN maps to a German clearing bank — either Deutsche Bank or Commerzbank. The agent looks up the BIC, confirms the bank is an active SWIFT member. That's the proposed repair value.
>
> Fourth — `get_fraud_score`. This is the predictive model layer. A fraud detection model scores every transaction on a 0-to-1 scale based on originator history, beneficiary jurisdiction, amount patterns, and timing signals. This payment scores 0.03 — essentially no risk. The originator has 847 clean transactions in the last 12 months. That's a machine learning model output that the agent consumes as a *tool* — the model is a callable service, not embedded in the agent.
>
> Fifth — `get_repair_history`. This is the operational analytics layer. Over the last 90 days, there have been 147 missing-BIC exceptions. 97% were resolved automatically by looking up the BIC from the IBAN. Average automated resolution: 4 minutes. Average *manual* resolution: 38 minutes. That historical success rate becomes the agent's confidence basis for its recommendation."

*Point to the structured output in the chat.*

> "Now look at the diagnosis. The agent doesn't just say 'fix it.' It presents structured output: root cause, an evidence chain citing *which tool returned what data*, the fraud risk level, the recommended repair action, a confidence level with the historical basis for that confidence, and whether human approval is required.
>
> Every conclusion traces back to a tool call. Every tool call is visible in the Events panel. This is the opposite of a black box — it's a glass box. An auditor can reconstruct every decision the agent made."

---

## Beat 4 — Human in the Loop (2 min)

### TELL

> "Now here's the critical design choice. The agent has diagnosed the problem and it knows the fix. But it does *not* execute the repair autonomously. It recommends and waits.
>
> This is Assist mode — one of three autonomy levels baked into the architecture. In Assist mode, the agent does the investigation, the human makes the call. The agent cannot call `submit_repair` until the operator explicitly approves. That's not a suggestion in the prompt — it's a hard constraint in the agent's instruction set.
>
> This matters in regulated environments. SR 11-7 — the Fed's model risk management guidance — requires human oversight of model-driven decisions. You don't get around that by calling it an 'agent' instead of a 'model.' The oversight has to be real, and it has to be auditable."

### SHOW

**Type**: `Approved. Submit the repair for EXC-2024-0847.`

*Agent calls `submit_repair` and returns confirmation with audit trail.*

### TELL

> "The repair is submitted. Look at what comes back — a structured audit record. Timestamp in UTC. Operator identifier — in production that would be the authenticated user from the SSO system. The action taken: 'add_bic'. The evidence chain that justified the action. And the approval status: 'pending_human_review' — meaning even after the agent submits, there's a review gate before the repair hits the settlement system.
>
> That 38-minute manual process — pulling up the exception, opening the SWIFT message viewer, looking up the BIC in a counterparty database, checking the fraud system, documenting the finding, submitting the repair — just happened in under a minute. And the documentation is *better* than what most analysts produce, because the agent cites every data source it used."

---

## Beat 5 — Earning Autonomy (2 min)

### TELL (no demo for this beat — narrate over the screen)

> "The natural question is: if the agent gets it right 97% of the time, why does a human still approve every one?
>
> The answer is: *today* they do. But the architecture is designed for a trust progression.
>
> Level one — Assist — is what you just saw. Agent investigates, human decides. This is where every agent starts in a regulated environment. You're building a track record.
>
> Level two — Supervised. The agent executes low-risk repairs automatically — it calls `submit_repair` without waiting for approval. But the human reviews *after the fact*, on a dashboard. You get to level two after 30 days of shadow mode — the agent runs in parallel with the human, both produce a recommendation, you measure agreement. 95% or better accuracy, plus a compliance sign-off, earns the agent supervised authority. And the skill evals I mentioned earlier — the agentskills.io test cases — are what you run continuously to make sure the agent's accuracy doesn't degrade as you update the skill or switch LLM versions.
>
> Level three — Autonomous. The agent handles the full lifecycle end-to-end. Humans monitor aggregate metrics — resolution rate, accuracy, exception volume trends — not individual cases.
>
> The critical architectural point: this progression is *per exception type*, not a blanket switch. Missing BIC auto-repair might reach level three — it's a well-understood pattern with a 97% success rate and no compliance sensitivity. Sanctions decisions? Those stay at level one permanently. That's not a technology limitation — that's policy. BSA/AML regulations require human sign-off on sanctions determinations regardless of how good the model is.
>
> This is how you build trust with regulators, with risk committees, with the operations team. You don't deploy AI and hope. You deploy it in assist mode, you measure in shadow mode, you build evidence, and you expand scope based on data. The agent earns its autonomy."

---

## Beat 6 — Same Pattern, Different Seam (2 min)

### TELL

> "One more thing. I want to show you that this isn't a one-trick demo. The same agent, the same architecture, the same agentskills.io skill definition handles a completely different type of exception — one with very different compliance constraints."

### SHOW

**Type**: `Now check the sanctions hold on EXC-2024-0853. Full diagnosis please.`

*Agent calls `get_exception_detail`, `check_sanctions_status`, `get_payment_message`, `get_fraud_score`, `get_repair_history`.*

### TELL (while agent works, narrate the Events panel)

> "Different seam now. The agent pulls the exception — this is a sanctions screening hold. It calls `check_sanctions_status` with the beneficiary name 'Ahmed Holdings LLC.' This simulates what a screening engine does — it runs the entity name against OFAC, EU, and UN sanctions lists and returns a match result.
>
> The result: a fuzzy name match with a score of 0.31 out of 1.0. The matched entry is 'AHMAD HOLDINGS' in Dubai. The differences: 'Ahmed' versus 'Ahmad' — a common Arabic transliteration variant. The searched entity is in Abu Dhabi; the listed entity is in Dubai. No matching aliases, no matching addresses. The screening tool itself calls this a likely false positive.
>
> The agent cross-references: fraud score is 0.18 — low. The originator, Meridian Partners, has 156 clean transactions in the last year. The repair history shows 91% of sanctions holds are released as false positives after compliance review.
>
> But here's where the agent's behavior fundamentally changes from the BIC repair."

*Point to the compliance note in the response.*

> "The agent says: recommended action is 'release_false_positive.' But it explicitly states: *compliance officer sign-off is required — policy CP-BSA-012.* It will not call `submit_repair` even if I tell it to. This is a hard constraint in the agent's instruction set — sanctions decisions require human sign-off under BSA/AML regulations, period.
>
> Same agent. Same framework. Same tools. But the *behavior* adapts to the compliance context of the exception type. The agent provides the analysis that takes a compliance officer from a 45-minute investigation to a 2-minute review. But the human makes the final call.
>
> That's the same architectural pattern Phil described — clear contracts at the seams, well-defined boundaries between what the technology does and what the human does. The agent respects those boundaries by design, not by accident."

---

## Close (1 min)

### TELL

> "So what did you just see? Let me be precise about it.
>
> An AI agent built on Google ADK using the agentskills.io open specification. It's served over the A2A protocol — standard JSON-RPC, discoverable via a well-known agent card endpoint. It runs on OpenShift, managed by Kagenti — the open-source platform that handles agent lifecycle, security, and observability so the agent developer doesn't have to.
>
> The agent has eight callable tools — each one a Python function that wraps an API call to a payment system. Today those return mock data. In production, you swap the function body — the signature, the docstring, the return type stay the same. The agent, the LLM, the skill definition — none of them change. That's the swap-ready pattern.
>
> The skill definition — the SKILL.md file — encodes the diagnostic methodology: which tools to call, in what order, how to interpret the results, what compliance constraints to enforce. It's a versionable, testable artifact. It has its own eval suite — you can measure whether the skill actually improves agent output versus a raw LLM without the skill. That's the agentskills.io standard.
>
> The agent correlates data from five systems in seconds. It cites evidence for every conclusion. It respects compliance boundaries that are encoded in its instructions, not bolted on after the fact. And it creates an audit trail that meets the documentation standard regulators expect.
>
> This is what's possible now. Not next year. And it starts the same way Phil described — you pick one seam, you instrument it, you prove value, and you expand from there. The technology is ready. The question is whether your architecture gives you the clean boundaries to deploy it."

---

## Emergency Fallback

If the agent or LLM is slow or unresponsive:

> "The agent is thinking — it's making multiple tool calls to different systems. While it works, let me show you what's happening in the Events panel..."

Then narrate the tool calls from the Events panel. The story holds either way because you're explaining the architecture, not just reading output.

If the UI is completely down, switch to narrating the architecture:

> "Let me walk you through what the agent does, using the same data it would show you live..."

Use the mock exception scenarios table from the README. The narrative carries without the live demo because the technical content is in the TELL, not just the SHOW.

---

## Key Numbers to Remember

| Fact | Number | Source |
|------|--------|--------|
| Manual resolution time (missing BIC) | 38 minutes | `get_repair_history("missing_bic")` |
| Agent-assisted resolution time | Under 1 minute | Observed in demo |
| Historical auto-repair success rate | 97% over 147 cases | `get_repair_history("missing_bic")` |
| Fraud score for EXC-0847 | 0.03 (low) | `get_fraud_score("MT103-REF-20250513-A")` |
| Sanctions match score for EXC-0853 | 0.31 (fuzzy) | `check_sanctions_status("Ahmed Holdings LLC")` |
| False positive rate for sanctions holds | 91% | `get_repair_history("sanctions_hold")` |
| Shadow mode requirement | 30 days, >= 95% accuracy | `references/repair-procedures.md` |
| Tools called per diagnosis | 5-7 depending on exception type | Observed in Events panel |

---

## Technical Concepts Cheat Sheet

If an audience member asks, here's the precise terminology:

| Concept | What It Is |
|---------|-----------|
| **Kagenti** | Open-source cloud-native platform for deploying AI agents in production (github.com/kagenti/kagenti). Framework-neutral — works with ADK, LangGraph, CrewAI, etc. Provides lifecycle management, zero-trust security (AuthBridge + SPIFFE/SPIRE), Keycloak OAuth/OIDC, OTel observability, and A2A/MCP protocol networking. Runs on Kubernetes/OpenShift. |
| **Google ADK** | Open-source Agent Development Kit from Google. Provides Agent class, tool registration, session management, A2A serving, and eval framework. |
| **agentskills.io** | Open specification for packaging agent capabilities as portable skills. A skill is a SKILL.md file (YAML frontmatter + Markdown instructions) with optional references, evals, and scripts. |
| **A2A Protocol** | Agent-to-Agent protocol. JSON-RPC-based standard for agent interoperability. Agents are discoverable via `/.well-known/agent-card.json` and callable via `message/send`. |
| **SWIFT MT103** | ISO 15022 standard message format for single customer credit transfers. Field :57A is the Account With Institution (beneficiary bank BIC). |
| **BIC** | Bank Identifier Code. 8 or 11 character SWIFT address. Can be derived from IBAN country code + bank code. |
| **OFAC SDN** | Office of Foreign Assets Control, Specially Designated Nationals list. U.S. Treasury sanctions watchlist. |
| **LiteLlm** | Open-source Python library that provides a unified interface to 100+ LLM providers. ADK uses it to connect to any OpenAI-compatible endpoint. |
| **LlamaStack** | Meta's open-source inference serving platform. Running on OpenShift, proxying to Gemini 2.5 Flash via an OpenAI-compatible API. |
| **SR 11-7** | Federal Reserve supervisory guidance on model risk management. Requires inventory, validation, and ongoing monitoring of models used in decision-making. |
| **CP-BSA-012** | (Demo) Compliance policy requiring human sign-off on all sanctions screening decisions under BSA/AML regulations. |
| **Shadow mode** | Agent runs in parallel with the human operator. Both produce recommendations independently. Agreement rate is measured over 30 days to build evidence for expanded autonomy. |

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
