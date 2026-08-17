# Decisions

## Track

**Professional Agents.** Everyday will be full of bill / calendar / warranty clones. Grand is chosen from all tracks; this is a named job (shop owner) with a repeating close.

## Product shape

Crew of roles defined by `SKILL.md`, not a chatbot. Background close + Decision Inbox. Matches the brief: run autonomously, surface only when a human must weigh in.

## Domain

Night register close at a one-register hardware store. Fully synthetic. No Plaid, no POS OAuth, no real cash. Demoable in one click.

## Why not the other ideas

- Medical-claim chase: high impact, easy to look fake without real EOBs, FAQ warns off real health data
- Body-shop supplements: needs photo theater
- School-closure pods: Good Neighbor, stronger Gold EV, weaker “I would use this tomorrow” for this panel
- Official examples (bills, family calendar, warranties, food-bank matching): crowded, Creativity dies

## Technical

- Strands graph is the only `start_close` / `resume_close` path
- Nodes are deterministic `MultiAgentBase` so the judge path needs no model key
- HITL is `BeforeNodeCallEvent` on the clerk node, looping while ask cards are open
- Policy is one module (`till/policy.py`)
- The first cut exposes only decisions that have a complete implementation. Variance
  `recount`/`investigate` buttons are deferred until a real follow-up workflow exists; the
  current owner action is `accept`.

## UI

Hardware-shop night desk: kraft tape, stamp red, register LED. Home surface is the board, not a prompt box. Opening `index.html` via `file:` tells you to use the server.
