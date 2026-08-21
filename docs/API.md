# HTTP API

Server: `uvicorn till.main:app --port 8000`
App: `till.main:app`

| Method | Path | Effect |
| --- | --- | --- |
| GET | `/health` | `{"ok":"till"}` |
| GET | `/` | Night board (`web/index.html`) |
| GET | `/api/night` | Current `ShopNight.to_dict()` |
| GET | `/api/export` | Download the locked close as a local JSON audit artifact |
| POST | `/api/close` | **Resets** the seeded Tuesday, runs the graph until interrupt or lock |
| POST | `/api/decide` | Resume the open interrupt. Body below. |
| POST | `/api/reset` | Clear graph + restore fixture. Night is `open`. |
| POST | `/api/narrate` | Optional Gemini explanation of the observed close; never changes policy or packet state. |

## Decide body

```json
{
  "decisions": [
    {"id": "VAR-TILL", "action": "accept", "note": "Owner reviewed the recount."},
    {"id": "REF-4412", "action": "approve"}
  ]
}
```

`note` is optional and is limited to 240 characters. Till normalizes it to a single line and
keeps it with the decision in the tape, exception record, packet, and local JSON export so the
owner's stamp is explainable on the next review.

409 if no close is in progress or the night is not waiting.

`GET /api/export` returns `409` until the packet is locked. After a successful close it returns
`application/json` with `Content-Disposition: attachment` and this envelope:

```json
{
  "format": "till-close-v1",
  "boundary": "local-process",
  "night": {"status": "locked", "packet": {"id": "DEP-2026-08-11"}}
}
```

The file is a local audit copy. Till does not persist or upload it.

The request must include exactly one supported decision for every open ask card. The current
seeded flow supports `VAR-TILL: accept` and `REF-4412: approve | deny`. Unknown cards, duplicate
cards, missing cards, and unsupported actions return `422` without changing the night.

## Snapshot fields the board uses

- `shop`, `owner`, `date`, `register`, `status`
- `sales` / `sales_count`
- `drawer.expected` / `counted` / `variance` (also top-level `expected_cash`, `counted_cash`, `variance`)
- `tape[]` — `{agent, tool, text}`
- `open_asks[]` and alias `cards[]` — open ask exceptions
- `exceptions[]` — all exceptions
- `packet` — null until filed; then `{id, cash_to_drop, lines, decisions}`; each decision can
  include the owner's optional `note`
- `run` — present after close/decide: `{status, interrupts?}`

## Status values

`open` → `counting` / `waiting` → `locked`

Close interrupt: `run.status == "interrupted"`, `status == "waiting"`, `packet == null`.
