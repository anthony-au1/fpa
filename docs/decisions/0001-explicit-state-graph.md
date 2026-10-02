# ADR 0001: Explicit state graph

**Decision:** Use LangGraph for an explicit bounded state graph; keep enforceable controls in deterministic Python.

**Reason:** Financial workflows need inspectable transitions, durable pauses, and predictable failure handling. An unconstrained ReAct loop cannot own approval or arithmetic controls.
