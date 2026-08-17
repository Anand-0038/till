# Architecture

Rendered diagram: [architecture.png](architecture.png). The SVG source is
[architecture.svg](architecture.svg).

```text
                    ┌──────────────────────────┐
                    │  Owner  (Dana)           │
                    │  Decision Inbox only     │
                    └────────────┬─────────────┘
                                 │ approve / deny
                                 ▼
┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐
│ cashier    │ → │ auditor    │ → │ owner-gate │ → │ clerk      │
│ SKILL.md   │   │ SKILL.md   │   │ interrupt  │   │ SKILL.md   │
│ count      │   │ policy     │   │ HITL       │   │ file packet│
└─────┬──────┘   └─────┬──────┘   └─────┬──────┘   └─────┬──────┘
      │                │                │                │
      ▼                ▼                ▼                ▼
 tools: count_drawer   audit_exceptions apply_decisions  file_deposit
        classify_tenders
                                 │
                                 ▼
                    fixture shop  (synthetic Tuesday)
```

- **Strands GraphBuilder** — sequential crew, clerk blocked until the gate passes.
- **BeforeNodeCallEvent** — interrupt in front of clerk when any `ask` card is open.
- **Skills** — `skills/<role>/SKILL.md` is the job description for that node.
- **Policy** — `till/policy.py` is the only table that decides auto vs ask.
- **Deterministic local path** — nodes are `MultiAgentBase` and call tools. No Bedrock or model
  key is required, and no model is allowed to decide cash policy.
- **UI** — tape + inbox + packet. Chat is not the product.

Export this diagram to PNG for the Devpost “Architecture Diagram” field.
