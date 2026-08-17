from __future__ import annotations

from pathlib import Path

from strands.agent.agent_result import AgentResult
from strands.multiagent.base import MultiAgentBase, MultiAgentResult, NodeResult, Status
from strands.types.content import ContentBlock, Message

from till import tools

SKILLS = Path(__file__).resolve().parents[1] / "skills"


def load_skill(role: str) -> str:
    return (SKILLS / role / "SKILL.md").read_text(encoding="utf-8")


def _result(name: str, text: str, payload: dict) -> MultiAgentResult:
    agent_result = AgentResult(
        stop_reason="end_turn",
        message=Message(role="assistant", content=[ContentBlock(text=text)]),
        metrics=None,
        state=payload,
    )
    return MultiAgentResult(
        status=Status.COMPLETED,
        results={name: NodeResult(result=agent_result, execution_time=1, status=Status.COMPLETED)},
        execution_count=1,
        execution_time=1,
    )


class CashierNode(MultiAgentBase):
    def __init__(self) -> None:
        super().__init__()
        self.name = "cashier"

    async def invoke_async(self, task, invocation_state, **kwargs):
        count = tools.count_drawer()
        tenders = tools.classify_tenders()
        text = f"{load_skill('cashier').splitlines()[1]}\ncounted {count['counted_cash']:.2f} variance {count['variance']:.2f}"
        return _result(self.name, text, {"count": count, "tenders": tenders})


class AuditorNode(MultiAgentBase):
    def __init__(self) -> None:
        super().__init__()
        self.name = "auditor"

    async def invoke_async(self, task, invocation_state, **kwargs):
        audit = tools.audit_exceptions()
        text = f"auto {len(audit['auto'])}  ask {len(audit['ask'])}"
        return _result(self.name, text, audit)


class ClerkNode(MultiAgentBase):
    def __init__(self) -> None:
        super().__init__()
        self.name = "clerk"

    async def invoke_async(self, task, invocation_state, **kwargs):
        packet = tools.file_deposit()
        return _result(self.name, f"filed {packet['id']}", packet)
