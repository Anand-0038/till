from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

DecisionAction = Literal["accept", "approve", "deny", "reverse"]
ExceptionKind = Literal["variance", "refund", "void", "no-sale"]
Lane = Literal["auto", "ask"]
NightStatus = Literal["open", "counting", "waiting", "locked"]


def money(value: float) -> float:
    return round(float(value), 2)


@dataclass
class Tender:
    method: str
    amount: float
    txn_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExceptionItem:
    id: str
    kind: ExceptionKind
    amount: float
    reason: str
    lane: Lane
    status: Literal["pending", "open", "auto", "decided"] = "pending"
    manager_code: bool = False
    time_hhmm: str | None = None
    receipt: bool = False
    decision: str | None = None
    decision_note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TapeLine:
    agent: str
    text: str
    tool: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Packet:
    id: str
    cash_to_drop: float
    lines: list[str]
    decisions: list[dict[str, str]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ShopNight:
    shop: str
    owner: str
    date: str
    register: str
    sales_count: int
    expected_cash: float
    counted_cash: float | None
    variance: float | None
    tenders: list[Tender]
    exceptions: list[ExceptionItem]
    tape: list[TapeLine] = field(default_factory=list)
    packet: Packet | None = None
    status: NightStatus = "open"

    def open_asks(self) -> list[ExceptionItem]:
        return [
            item
            for item in self.exceptions
            if item.lane == "ask" and item.status == "open"
        ]

    def to_dict(self) -> dict[str, Any]:
        from till.policy import POLICY_TABLE

        asks = [e.to_dict() for e in self.open_asks()]
        return {
            "shop": self.shop,
            "owner": self.owner,
            "date": self.date,
            "register": self.register,
            "sales_count": self.sales_count,
            "sales": self.sales_count,
            "expected_cash": self.expected_cash,
            "counted_cash": self.counted_cash,
            "variance": self.variance,
            "drawer": {
                "expected": self.expected_cash,
                "counted": self.counted_cash,
                "variance": self.variance,
            },
            "tenders": [t.to_dict() for t in self.tenders],
            "exceptions": [e.to_dict() for e in self.exceptions],
            "tape": [t.to_dict() for t in self.tape],
            "packet": self.packet.to_dict() if self.packet else None,
            "policy": [dict(row) for row in POLICY_TABLE],
            "status": self.status,
            "open_asks": asks,
            "cards": asks,
        }
