import asyncio

from till.engine import reset_night, resume_close, start_close
from till.nodes import AuditorNode, CashierNode, ClerkNode
from till.policy import classify_exception
from till.store import night, reset
from till.tools import apply_decisions, audit_exceptions, count_drawer, file_deposit


def test_policy_caps():
    assert classify_exception("variance", -12.50) == "ask"
    assert classify_exception("variance", -4.00) == "auto"
    assert classify_exception("refund", 89.00) == "ask"
    assert classify_exception("refund", 20.00, receipt=True) == "auto"
    assert classify_exception("refund", 20.00, receipt=False) == "ask"
    assert classify_exception("void", 24.00, manager_code=True) == "auto"
    assert classify_exception("void", 24.00, manager_code=False) == "ask"


def test_cannot_file_with_open_asks():
    reset()
    count_drawer()
    audit = audit_exceptions()
    assert {card["id"] for card in audit["ask"]} == {"VAR-TILL", "REF-4412"}
    try:
        file_deposit()
        raise AssertionError("deposit must not file")
    except RuntimeError as exc:
        assert "ask" in str(exc)
    assert night().packet is None
    assert night().status != "locked"


def test_cannot_file_before_audit_marks_pending_asks():
    reset()
    count_drawer()

    try:
        file_deposit()
        raise AssertionError("deposit must wait for the auditor")
    except RuntimeError as exc:
        assert "auditor" in str(exc)

    assert night().packet is None
    assert night().status != "locked"


def test_deposit_after_owner_stamps():
    reset()
    count_drawer()
    audit_exceptions()
    apply_decisions(
        [
            {"id": "VAR-TILL", "action": "accept"},
            {"id": "REF-4412", "action": "approve"},
        ]
    )
    packet = file_deposit()
    assert packet["id"] == "DEP-2026-08-11"
    assert packet["cash_to_drop"] == 1228.00
    assert packet["lines"][2:] == [
        "variance   -12.50  accept",
        "refunds    REF-4412 approve",
        "voids      VOID-19 auto (manager code)",
        "notes      NS-7 no-sale after 21:00",
    ]
    assert night().status == "locked"


def test_invalid_owner_decisions_are_atomic():
    reset()
    count_drawer()
    audit_exceptions()
    before_tape = len(night().tape)

    try:
        apply_decisions(
            [
                {"id": "VAR-TILL", "action": "accept"},
                {"id": "REF-4412", "action": "recount"},
            ]
        )
        raise AssertionError("unsupported action must be rejected")
    except ValueError as exc:
        assert "accepts approve, deny" in str(exc)

    assert {item.id for item in night().open_asks()} == {"VAR-TILL", "REF-4412"}
    assert len(night().tape) == before_tape


def test_strands_graph_interrupt_and_resume():
    reset_night()
    first = start_close()
    assert first["run"]["status"] == "interrupted"
    assert {item["name"] for item in first["run"]["interrupts"]} == {"owner-gate"}
    assert first["run"]["interrupts"][0]["reason"]["role"] == "name: owner-gate"
    assert {card["id"] for card in first["open_asks"]} == {"VAR-TILL", "REF-4412"}
    assert first["packet"] is None
    assert first["status"] == "waiting"
    second = resume_close(
        [
            {"id": "VAR-TILL", "action": "accept"},
            {"id": "REF-4412", "action": "approve"},
        ]
    )
    assert second["status"] == "locked"
    assert second["packet"]["id"] == "DEP-2026-08-11"
    assert second["packet"]["cash_to_drop"] == 1228.00
    assert second["open_asks"] == []
    assert {line["tool"] for line in second["tape"]} >= {
        "count_drawer",
        "classify_tenders",
        "audit_exceptions",
        "apply_decisions",
        "file_deposit",
    }
    tender_line = next(
        line for line in second["tape"] if line["tool"] == "classify_tenders"
    )
    assert "cash 1240.50" in tender_line["text"]
    assert "card 3180.20" in tender_line["text"]
    assert "store-credit 95.00" in tender_line["text"]


def test_graph_nodes_carry_their_loaded_skill_contracts():
    reset()

    cashier = asyncio.run(CashierNode().invoke_async("close", {}))
    auditor = asyncio.run(AuditorNode().invoke_async("close", {}))
    apply_decisions(
        [
            {"id": "VAR-TILL", "action": "accept"},
            {"id": "REF-4412", "action": "approve"},
        ]
    )
    clerk = asyncio.run(ClerkNode().invoke_async("close", {}))

    for role, result in (("cashier", cashier), ("auditor", auditor), ("clerk", clerk)):
        state = result.results[role].result.state
        assert state["skill"].startswith("---\nname: " + role)
