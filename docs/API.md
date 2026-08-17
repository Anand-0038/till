# HTTP API

Server: `uvicorn till.main:app --port 8000`
App: `till.main:app`

| Method | Path | Effect |
| --- | --- | --- |
| GET | `/health` | `{"ok":"till"}` |
| GET | `/` | Night board (`web/index.html`) |
| GET | `/api/night` | Current `ShopNight.to_dict()` |
| POST | `/api/close` | **Resets** the seeded Tuesday, runs the graph until interrupt or lock |
| POST | `/api/decide` | Resume the open interrupt. Body below. |
| POST | `/api/reset` | Clear graph + restore fixture. Night is `open`. |

## Decide body

```json
{
  "decisions": [
    {"id": "VAR-TILL", "action": "accept"},
    {"id": "REF-4412", "action": "approve"}
  ]
}
```

409 if no close is in progress or the night is not waiting.

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
- `packet` — null until filed; then `{id, cash_to_drop, lines, decisions}`
- `run` — present after close/decide: `{status, interrupts?}`

## Status values

`open` → `counting` / `waiting` → `locked`

Close interrupt: `run.status == "interrupted"`, `status == "waiting"`, `packet == null`.
