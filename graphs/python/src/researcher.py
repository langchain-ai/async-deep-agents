"""Researcher subagent graph.

A specialized agent for information gathering, analysis, and research tasks.
This graph runs as an async subagent -- the supervisor launches it as a
background job and checks on it later.

When deployed via `langgraph.json`, this graph is addressable by its graph ID
("researcher") and the supervisor reaches it via ASGI transport.

## Completion notifications

By default, the supervisor only learns about completion when it calls
`check_async_subagent`. To enable push notifications, uncomment the
completion notifier wiring below. See `completion_notifier.py` for details.
"""

from __future__ import annotations

from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool

# Uncomment to enable completion notifications:
# from langchain_core.runnables import RunnableConfig
# from middleware.completion_notifier import build_completion_notifier

SYSTEM_PROMPT = """\
You are a research agent specializing in information gathering and analysis.

Your job is to thoroughly research the topic or question you've been given and
produce a comprehensive, well-structured response. Focus on:

1. Accuracy -- verify claims and note when information is uncertain
2. Completeness -- cover all relevant aspects of the topic
3. Structure -- organize your findings clearly with headings and bullet points
4. Sources -- mention where information could be verified when relevant

Take your time to be thorough. The supervisor agent will check on your results
when they're needed.
"""


@tool
def analyze_topic(query: str) -> str:
    """Analyze a topic by breaking it down into key aspects and considerations.

    Args:
        query: The topic or question to analyze.
    """
    # In a real deployment, this could call a search API, RAG pipeline, etc.
    return (
        f"Analysis of '{query}':\n"
        f"- Key aspects identified\n"
        f"- Related concepts mapped\n"
        f"- Potential sources noted\n"
        f"\nThis is a placeholder. In production, connect to your preferred "
        f"search/RAG tools here."
    )


@tool
def summarize_findings(content: str, format: str = "bullet_points") -> str:
    """Summarize research findings into a structured format.

    Args:
        content: The raw research content to summarize.
        format: Output format -- 'bullet_points', 'narrative', or 'table'.
    """
    return (
        f"Summary ({format}):\n"
        f"- Condensed key findings from provided content\n"
        f"- Organized by relevance and importance\n"
        f"\nThis is a placeholder. The LLM handles the actual summarization."
    )


model = ChatAnthropic(model="claude-sonnet-4-6-20250514")


# --- Static graph (no completion notifications) ---

graph = create_agent(
    model=model,
    tools=[analyze_topic, summarize_findings],
    system_prompt=SYSTEM_PROMPT,
    name="researcher",
)


# --- Dynamic graph factory with completion notifications ---
# Uncomment this block and comment out the static `graph` above to enable
# push notifications back to the supervisor when this subagent finishes.
#
# import contextlib
# from langchain_core.runnables import RunnableConfig
# from middleware.completion_notifier import build_completion_notifier
#
# @contextlib.asynccontextmanager
# async def graph(config: RunnableConfig):
#     """Graph factory that wires up the completion notifier from config."""
#     configurable = config.get("configurable", {})
#     notifier = build_completion_notifier(
#         parent_thread_id=configurable.get("parent_thread_id"),
#         parent_assistant_id=configurable.get("parent_assistant_id"),
#         subagent_name="researcher",
#     )
#     yield create_agent(
#         model=model,
#         tools=[analyze_topic, summarize_findings],
#         system_prompt=SYSTEM_PROMPT,
#         middleware=[notifier],
#         name="researcher",
#     )
