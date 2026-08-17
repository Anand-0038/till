# Till — spec

Professional Agents. A shop owner staffs a night crew with skill files. The crew closes the register. The owner only weighs in.

## Who

Dana Reyes, owner-operator of **Oak & Bit Hardware**. One register. No back office. Close used to take 40 minutes after lockup.

## The loop

1. Cashier reads the day's tenders and counts the drawer.
2. Auditor checks voids, refunds, no-sales, and drawer variance against policy.
3. Safe work is done. Risky work becomes a Decision Inbox card.
4. Owner approves or rejects each card.
5. Clerk files the deposit packet and locks the night.

## Policy (source of truth)

| Event | Auto | Ask |
| --- | --- | --- |
| Tender totals match POS | file | — |
| Drawer variance ≤ $10 | accept as variance | — |
| Drawer variance > $10 | — | accept |
| Refund ≤ $50 with receipt | post | — |
| Refund > $50 | — | approve / deny |
| Void with manager code | accept | — |
| Void without manager code | — | accept / reverse |
| No-sale after 21:00 | note on packet | — |

Never invent cash. Never file a deposit while a card is open.

## Demo path (must work with no cloud keys)

Seeded Tuesday. 47 sales. One $89 refund. Drawer short $12.50. One late no-sale.

1. Owner hits **Run night close**.
2. Timeline shows cashier → auditor. Two cards appear. Deposit is blocked.
3. Owner accepts the $12.50 short as variance, approves the refund.
4. Clerk files packet `DEP-2026-08-11`. Night status is **locked**.
5. Audit names every agent, tool, and decision.

## Surfaces

- Night board (not a chat box)
- Crew timeline
- Decision Inbox
- Deposit packet (the artifact)
- Local audit export (only after the packet locks)
- Policy table

## Stack

Strands `GraphBuilder` + `BeforeNodeCallEvent` interrupt. Each role is a node that loads its job contract from `skills/<role>/SKILL.md`. Tools mutate a fixture shop. FastAPI + one static UI. The deterministic local path needs no model provider or cloud key; optional narration is outside the close decision path.
