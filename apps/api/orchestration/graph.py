"""
SOLVER API - LangGraph Definition

State machine graph definition per Doc 3 Section 8.2.
"""

from typing import Literal

from langgraph.graph import StateGraph, END

from domain.state import (
    WorkflowState,
    StepPhase,
    StepStatus,
    PassType,
    StepName,
    HumanAction,
    ensure_workflow_state,
)
from infrastructure.db.checkpoint_saver import SolverCheckpointSaver
from orchestration.nodes import (
    receive_node,
    analyze_node,
    elicit_node,
    structure_node,
    validate_node,
    review_node,
    process_decision_node,
    advance_node,
)


def route_after_decision(state: WorkflowState) -> Literal["advance", "structure", "validate", "end"]:
    """Route based on human decision.

    Per Doc 3 §8.2:
    - approve → advance to next step
    - reject → return to structuring with feedback
    - modify → revalidate with modifications
    """
    state = ensure_workflow_state(state)
    if state.human_decision == HumanAction.APPROVE:
        return "advance"
    elif state.human_decision == HumanAction.REJECT:
        return "structure"
    elif state.human_decision == HumanAction.MODIFY:
        return "validate"
    return "end"


def is_workflow_complete(state: WorkflowState) -> bool:
    """Check if workflow is complete.

    MVP: Complete after Step 3 Pass 2 approved.
    """
    state = ensure_workflow_state(state)
    return (
        state.current_pass == PassType.EXECUTION and
        state.current_step == StepName.OBJECTIVES and
        state.step_state is not None and
        state.step_state.status == StepStatus.APPROVED
    )


def create_graph(checkpointer: SolverCheckpointSaver) -> StateGraph:
    """Create the SOLVER workflow graph.

    Per Doc 3 §8.2 and Decision #5 (use SolverCheckpointSaver).

    Args:
        checkpointer: Checkpoint saver for state persistence

    Returns:
        Compiled StateGraph ready for execution
    """
    graph = StateGraph(WorkflowState)

    # Add nodes
    graph.add_node("receive", receive_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("elicit", elicit_node)
    graph.add_node("structure", structure_node)
    graph.add_node("validate", validate_node)
    graph.add_node("review", review_node)
    graph.add_node("process_decision", process_decision_node)
    graph.add_node("advance", advance_node)

    # Entry point
    graph.set_entry_point("receive")

    # Edges
    graph.add_edge("receive", "analyze")

    # After analyze: elicit if clarification needed, else structure
    def route_after_analyze(s: WorkflowState) -> str:
        s = ensure_workflow_state(s)
        return "elicit" if (s.step_state is not None and s.step_state.phase == StepPhase.ELICITING) else "structure"

    graph.add_conditional_edges(
        "analyze",
        route_after_analyze,
        {"elicit": "elicit", "structure": "structure"}
    )

    graph.add_edge("elicit", "structure")
    graph.add_edge("structure", "validate")

    # After validate: review if passed, else back to structure
    def route_after_validate(s: WorkflowState) -> str:
        s = ensure_workflow_state(s)
        return "review" if (s.step_state is not None and s.step_state.validation_result is not None and s.step_state.validation_result.passed) else "structure"

    graph.add_conditional_edges(
        "validate",
        route_after_validate,
        {"review": "review", "structure": "structure"}
    )

    graph.add_edge("review", "process_decision")

    # After process_decision: route based on human decision
    graph.add_conditional_edges(
        "process_decision",
        route_after_decision,
        {"advance": "advance", "structure": "structure", "validate": "validate", "end": END}
    )

    # After advance: end if complete, else receive next step
    def route_after_advance(s: WorkflowState) -> str:
        return "end" if is_workflow_complete(s) else "receive"

    graph.add_conditional_edges(
        "advance",
        route_after_advance,
        {"end": END, "receive": "receive"}
    )

    return graph.compile(checkpointer=checkpointer)
