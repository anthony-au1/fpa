from app.agent.graph import WORKFLOW_NODES, build_graph


def test_graph_compiles_with_explicit_nodes() -> None:
    graph = build_graph().get_graph()
    assert set(WORKFLOW_NODES).issubset(graph.nodes)
