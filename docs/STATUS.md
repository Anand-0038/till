# Status

Local demo is built and tested. Submission kit for Devpost is not.

## Done

- Product: Till, Professional track, Oak & Bit night close
- Spec, policy table, four role skills
- Strands `GraphBuilder` + `BeforeNodeCallEvent` interrupt/resume
- FastAPI: `/health`, `/api/night`, `/api/close`, `/api/decide`, `/api/reset`, static board at `/`
- Locked close can be exported through `/api/export` or the board's **Export audit** control as a
  local JSON artifact; export is rejected before the packet is locked
- Board: Run night close, Decision Inbox, register tape, deposit packet. Not a chat home.
- Judge assets: rendered architecture diagram, waiting-state screenshot, locked-state screenshot,
  and originality/attribution note
- Apache-2.0 license
- Tests: policy caps and receipt requirement, atomic decision validation, deposit guard, graph
  interrupt/resume, HTTP close→decide, invalid HTTP decision handling, initial empty state,
  tool-aware tape, and skill files

## Last test run

```
12 passed
```

Graph close pauses on `VAR-TILL` + `REF-4412`, packet is null. Decide accept + approve locks `DEP-2026-08-11` with cash-to-drop `1228.00`.

## Not done (needed to actually submit / score higher)

See [WIN-CHECKLIST.md](WIN-CHECKLIST.md).

- Public GitHub repo with license visible in About
- Public repository should include the rendered architecture diagram and its source
- Demo video ≤ 5 min
- AWS Builder ID on the submission form
- $50 credits request by **11 Sep 2026 12:00 PT**
- Optional but scoring: live URL, AgentCore deploy, up to 3 builder.aws posts (+0.6)
- OpenAI/Bedrock narration of nodes (optional; close must stay mock-safe)

## Do not reopen

- Do not add a second domain/store API. `till.store.night` / `reset` plus `ShopNight.to_dict` is the snapshot.
- Do not POST `/api/close` after decide. Close resets the night.
- Do not file a deposit while ask cards are open.
- Do not invent cash.
