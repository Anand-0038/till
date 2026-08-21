# Demo script (≤ 5 minutes)

Record this. Voiceover is enough. No face required.

## 0:00–0:25 — Problem

Dana Reyes closes Oak & Bit Hardware alone. Forty minutes after lockup: count the drawer, hunt voids, decide the short, file the drop. One missed stamp and the deposit is a lie.

## 0:25–0:40 — Who / why

Till is a night crew, not another app. Cashier, auditor, clerk are skill files. Dana only sees cards policy cannot close.

## 0:40–2:10 — Quiet work

Click **Run night close**.

Show the tape print:

- cashier COUNT expected 1240.50 counted 1228.00 var −12.50
- auditor AUTO on VOID-19 and NS-7
- auditor ASK on VAR-TILL and REF-4412

Deposit stays unfiled.

## 2:10–3:20 — Decision

Inbox: two cards.

1. VAR-TILL −$12.50 — **accept**
2. REF-4412 $89 refund — **approve**

Optionally add a short owner note to a card, such as `Recount reviewed by Dana.` The note is
carried into the owner tape and the local packet export; leaving it blank keeps the main demo
fast.

Say: the crew already did the safe work. These two need a human.

## 3:20–4:10 — Outcome

Packet **DEP-2026-08-11**. Cash drop **1228.00**. Night **LOCKED**. Clerk only ran after the inbox emptied.

## 4:10–4:50 — Architecture

One slide: cashier → auditor → owner-gate interrupt → clerk. Strands graph. Policy in one file. Skills are the jobs.

After showing the locked packet, click **Export audit** once. The browser saves a local JSON
copy of the packet and close trace; say explicitly that it is a local download, not cloud storage.

## 4:50–5:00 — Close

“Dana opened Till twice. The crew closed the store.”

## Backup if the UI flakes

```bash
curl -sS -X POST http://127.0.0.1:8000/api/close
curl -sS -X POST http://127.0.0.1:8000/api/decide \
  -H 'Content-Type: application/json' \
  -d '{"decisions":[{"id":"VAR-TILL","action":"accept"},{"id":"REF-4412","action":"approve"}]}'
```

## Capture plan

Capture two local browser states, not a fabricated “live” dashboard:

1. **Waiting gate:** after **Run night close**, show the tool-aware tape, two open cards,
   the blocked clerk, and the held packet.
2. **Locked outcome:** stamp `accept` and `approve`, then show the same board with zero open
   cards, the clerk's `file_deposit` line, and packet `DEP-2026-08-11`.

Keep the terminal or a small architecture slide available for the Strands proof point. The
screenshots in the README are local evidence only; a future public video must be recorded and
uploaded separately before it is described as a submission asset.
