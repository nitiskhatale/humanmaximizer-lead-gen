"""
LangGraph StateGraph — assembles the 3-agent pipeline.

Flow:
    START → research_node → qualification_node
                                   ↓
                    (score ≥ 35) → sales_node → END
                    (score < 35) → END  (status = "disqualified")

The compiled graph is exposed as `pipeline` — a callable that accepts a
LeadState dict and returns an updated LeadState dict.
"""
import logging

from langgraph.graph import END, START, StateGraph

from agents.qualification_agent import qualification_node
from agents.research_agent import research_node
from agents.sales_agent import sales_node
from models.state import LeadState

logger = logging.getLogger(__name__)


def _route_after_qualification(state: LeadState) -> str:
    """Conditional edge: proceed to SalesAgent only if qualified."""
    if state.get("is_qualified", False):
        logger.info(
            "[Graph] routing to sales_node (score=%d)", state.get("qualification_score", 0)
        )
        return "sales_node"
    logger.info(
        "[Graph] lead disqualified (score=%d) — skipping sales_node",
        state.get("qualification_score", 0),
    )
    return END


def build_graph() -> StateGraph:
    """Construct and compile the LangGraph StateGraph."""
    graph = StateGraph(LeadState)

    graph.add_node("research_node", research_node)
    graph.add_node("qualification_node", qualification_node)
    graph.add_node("sales_node", sales_node)

    graph.add_edge(START, "research_node")
    graph.add_edge("research_node", "qualification_node")
    graph.add_conditional_edges(
        "qualification_node",
        _route_after_qualification,
        {
            "sales_node": "sales_node",
            END: END,
        },
    )
    graph.add_edge("sales_node", END)

    return graph.compile()


# Module-level singleton — imported by API routes
pipeline = build_graph()
