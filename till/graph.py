from __future__ import annotations

from strands.multiagent import GraphBuilder

from till.hitl import OwnerGate
from till.nodes import AuditorNode, CashierNode, ClerkNode


def build_graph():
    builder = GraphBuilder()
    builder.add_node(CashierNode(), "cashier")
    builder.add_node(AuditorNode(), "auditor")
    builder.add_node(ClerkNode(), "clerk")
    builder.add_edge("cashier", "auditor")
    builder.add_edge("auditor", "clerk")
    builder.set_entry_point("cashier")
    builder.set_hook_providers([OwnerGate()])
    builder.set_max_node_executions(8)
    builder.set_execution_timeout(60)
    return builder.build()
