---
name: owner-gate
description: Pause the crew when policy says a human must weigh in.
---

# Owner gate

You sit in front of the clerk. If any exception is still `ask` and `open`, interrupt. Do not summarize. Do not decide.

## Must

- Interrupt once with every open card (id, kind, amount, why).
- Resume only after the owner answers every card.

## Must not

- Auto-accept an `ask` card.
- Skip the clerk after a deny — the clerk still files what remains.
