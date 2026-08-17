# Handoff — restart Till from cold

Read this first after a restart. Then `README.md`, then `docs/STATUS.md`.

## What this repo is

**Till** — Agents for Humans hackathon entry. **Professional Agents** track.

A hardware-shop owner staffs a night crew from skill files. The crew closes the register. The owner only stamps cards policy cannot close.

Product name: Till
Shop: Oak & Bit Hardware
Owner: Dana Reyes
Seeded night: Tuesday **2026-08-11**

## Start the demo

```bash
cd ~/projects/hackathons/humans-hack
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn till.main:app --reload --port 8000
```

Open http://127.0.0.1:8000

1. **Run night close**
2. Stamp **VAR-TILL** → accept, **REF-4412** → approve
3. Packet **DEP-2026-08-11** files, cash drop **1228.00**, night **LOCKED**

```bash
pytest tests/test_close.py tests/test_http.py tests/test_skills.py -q
```

No AWS or OpenAI key required.

## File map

| Path | Why it exists |
| --- | --- |
| [HANDOFF.md](HANDOFF.md) | This file. Cold restart. |
| [README.md](README.md) | Judge-facing run instructions |
| [SPEC.md](SPEC.md) | Product spec. Do not drift. |
| [LICENSE](LICENSE) | Apache-2.0 (required) |
| [HACKATHON.md](HACKATHON.md) | Devpost overview, prizes, criteria |
| [RESOURCES.md](RESOURCES.md) | Setup, learning, track inspiration |
| [Agents for Humans Devpost](https://agentsforhumans.devpost.com/) | Official event page and rules |
| [docs/STATUS.md](docs/STATUS.md) | What works, what is left to win |
| [docs/DEMO.md](docs/DEMO.md) | 5-minute video / live-judge script |
| [docs/API.md](docs/API.md) | HTTP contract |
| [docs/architecture.md](docs/architecture.md) | Graph + HITL diagram |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Why this idea, what we refused |
| [docs/WIN-CHECKLIST.md](docs/WIN-CHECKLIST.md) | Credits, AgentCore, video, blogs, Devpost |
| [skills/*/SKILL.md](skills/) | Role job descriptions loaded by nodes |
| `till/` | Close engine, graph, policy, tools, FastAPI |
| `web/` | Night board (tape, inbox, packet) |
| `tests/` | Shipped-path tests |

## Close path (do not bypass)

`POST /api/close` → `till.engine.start_close` → `till.graph.build_graph`
cashier → auditor → **owner-gate interrupt** → (after decide) clerk → `file_deposit`

`POST /api/decide` → `till.engine.resume_close` with Strands `interruptResponse`.

`start_close` **resets** the night. Never call close again after decide.

Policy lives only in `till/policy.py`.

## Seeded Tuesday facts

- 47 sales
- Expected cash 1240.50, counted 1228.00, variance **−12.50** → **VAR-TILL** ask
- Refund **REF-4412** $89 with receipt → ask
- Void **VOID-19** $24 with manager code → auto
- No-sale **NS-7** at 21:14 → auto note
- Packet id `DEP-2026-08-11`

## Last verified

11 tests passed (`test_close`, `test_http`, `test_skills`). The graph interrupt is named
`owner-gate`; the tape records each role's tool. HTTP close then decide locks
`DEP-2026-08-11` / `1228.00`. Invalid or incomplete decisions return `422` without partial
owner mutation.
