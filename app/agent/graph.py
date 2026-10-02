from collections.abc import Callable

from langgraph.graph import END, START, StateGraph

from app.agent.state import AgentState

Node = Callable[[AgentState], dict]

WORKFLOW_NODES = (
    "VALIDATE_REQUEST",
    "RETRIEVE_POLICY",
    "GATHER_EVIDENCE",
    "RECONCILE",
    "POLICY_ANALYSIS",
    "BUILD_RECOMMENDATION",
    "WAITING_FOR_APPROVAL",
    "SUBMIT_FINANCE_DECISION",
    "COMPLETE",
    "FAILED",
)


class FoundationNodeNotImplemented(RuntimeError):
    pass


def _placeholder(name: str) -> Node:
    def node(_state: AgentState) -> dict:
        raise FoundationNodeNotImplemented(
            f"{name} is a foundation-only node and has no business implementation"
        )

    return node


def build_graph() -> object:
    """Compile the intended topology without exposing unfinished execution through the API."""
    builder = StateGraph(AgentState)
    for name in WORKFLOW_NODES:
        builder.add_node(name, _placeholder(name))
    builder.add_edge(START, "VALIDATE_REQUEST")
    builder.add_edge("VALIDATE_REQUEST", "RETRIEVE_POLICY")
    builder.add_edge("RETRIEVE_POLICY", "GATHER_EVIDENCE")
    builder.add_edge("GATHER_EVIDENCE", "RECONCILE")
    builder.add_edge("RECONCILE", "POLICY_ANALYSIS")
    builder.add_edge("POLICY_ANALYSIS", "BUILD_RECOMMENDATION")
    # Later routing selects COMPLETE or WAITING_FOR_APPROVAL. Both edges document that shape.
    builder.add_edge("BUILD_RECOMMENDATION", "WAITING_FOR_APPROVAL")
    builder.add_edge("WAITING_FOR_APPROVAL", "SUBMIT_FINANCE_DECISION")
    builder.add_edge("SUBMIT_FINANCE_DECISION", "COMPLETE")
    builder.add_edge("COMPLETE", END)
    builder.add_edge("FAILED", END)
    return builder.compile()
