# Status

Local demo is built and tested. Submission kit for Devpost is not.

## Done

- Product: Till, Professional track, Oak & Bit night close
- Spec, policy table, four role skills
- Strands `GraphBuilder` + `BeforeNodeCallEvent` interrupt/resume
- Optional real Strands `Agent` auditor review: Gemini-backed read-only tool call and bounded
  owner summary, with deterministic policy fallback
- FastAPI: `/health`, `/api/night`, `/api/export`, `/api/close`, `/api/decide`, `/api/reset`, static board at `/`
- Locked close can be exported through `/api/export` or the board's **Export audit** control as a
  local JSON artifact; export is rejected before the packet is locked
- Board: Run night close, Decision Inbox, register tape, deposit packet, and optional owner
  rationale notes that travel into the local audit packet. Not a chat home.
- User-supplied POS-neutral close packets: validated `POST /api/close` input and compact board
  editor run through the same policy graph; malformed packets fail before graph execution.
- Optional Gemini explanation: a real provider call can summarize the observed tape and decision
  state without entering the deterministic cash-policy path; missing credentials fail closed.
- Judge assets: rendered architecture diagram, waiting-state screenshot, locked-state screenshot,
  and originality/attribution note
- Apache-2.0 license
- Tests: policy caps and receipt requirement, atomic decision validation, deposit guard, graph
  interrupt/resume, HTTP close→decide, invalid HTTP decision handling, initial empty state,
  tool-aware tape, optional model-review contract, and skill files

## Last test run

```
31 passed
```

Graph close pauses on `VAR-TILL` + `REF-4412`, packet is null. Decide accept + approve locks
`DEP-2026-08-11` with cash-to-drop `1228.00`; an optional owner note is preserved in the tape,
packet, and local JSON export. A separate API regression runs a Northstar Bike & Repair packet
through the same graph and locks `DEP-2026-08-21` after its derived variance is stamped.

## Not done (needed to actually submit / score higher)

See [WIN-CHECKLIST.md](WIN-CHECKLIST.md).

- Public GitHub repo with license visible in About
- Public repository should include the rendered architecture diagram and its source
- Demo video ≤ 5 min
- AWS Builder ID on the submission form
- $50 credits request by **11 Sep 2026 12:00 PT**
- Optional but scoring: live URL, AgentCore deploy, up to 3 builder.aws posts (+0.6)
- Public model-backed Strands review is verified locally through Gemini; Bedrock/AgentCore
  deployment and a live URL remain optional score raisers.

## Do not reopen

- Do not add a second domain/store API. `till.store.night` / `reset` plus `ShopNight.to_dict` is the snapshot.
- Do not POST `/api/close` after decide. Close resets the night.
- Do not file a deposit while ask cards are open.
- Do not invent cash.
