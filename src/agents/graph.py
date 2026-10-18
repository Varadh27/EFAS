from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from src.agents.state import AuditState
from src.agents.nodes import (
    sql_extractor_node,
    compliance_evaluator_node,
    hitl_approval_gate_node,
    report_synthesis_node,
    sql_generator_node,
    auditor_evaluation_node,
)


def route_after_evaluation(
    state: AuditState,
) -> Literal["hitl_approval_gate", "report_synthesis"]:
    """Routes to the HITL interrupt gate if thresholds are breached."""
    if state.get("requires_human_approval"):
        return "hitl_approval_gate"
    return "report_synthesis"


def build_audit_graph(checkpointer=None):
    """Compiles multi-agent audit workflow with state checkpointing."""
    builder = StateGraph(AuditState)

    builder.add_node("sql_extractor", sql_extractor_node)
    builder.add_node("compliance_evaluator", compliance_evaluator_node)
    builder.add_node("hitl_approval_gate", hitl_approval_gate_node)
    builder.add_node("report_synthesis", report_synthesis_node)

    builder.add_edge(START, "sql_extractor")
    builder.add_edge("sql_extractor", "compliance_evaluator")
    builder.add_conditional_edges(
        "compliance_evaluator",
        route_after_evaluation,
        {
            "hitl_approval_gate": "hitl_approval_gate",
            "report_synthesis": "report_synthesis",
        },
    )
    builder.add_edge("hitl_approval_gate", "report_synthesis")
    builder.add_edge("report_synthesis", END)

    active_checkpointer = checkpointer or MemorySaver()
    return builder.compile(checkpointer=active_checkpointer)


__all__ = [
    "route_after_evaluation",
    "build_audit_graph",
    "sql_extractor_node",
    "compliance_evaluator_node",
    "sql_generator_node",
    "auditor_evaluation_node",
]
