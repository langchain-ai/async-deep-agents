"""Supervisor agent that orchestrates async subagents.

This is the main agent that users interact with. It uses the
`AsyncSubAgentMiddleware` from deepagents to launch, monitor, and manage
background jobs running on the researcher and coder subagent graphs.

When deployed to LangGraph Platform with all graphs in the same
`langgraph.json`, the `url` field is omitted from the `AsyncSubAgent` specs.
This uses ASGI transport -- the subagents run in the same process as the
supervisor, no external networking required.
"""

from __future__ import annotations

from deepagents import AsyncSubAgent, create_deep_agent
from langchain_anthropic import ChatAnthropic

SYSTEM_PROMPT = """\
## How to work:
1. When the user asks for something, decide if it needs research, coding, or both
2. Launch the appropriate subagent(s) -- you can run multiple in parallel
3. Report the job ID(s) to the user and let them know work is in progress
4. When asked, check on job status and relay results
5. For complex tasks, you can chain subagents: research first, then code based on findings

## Important:
- Always launch subagents for non-trivial tasks rather than trying to do everything yourself
- You can launch multiple subagents simultaneously for independent tasks
- After launching, return control to the user -- don't auto-check status
"""

# Subagent specs -- url is omitted for ASGI transport (same deployment)
ASYNC_SUBAGENTS: list[AsyncSubAgent] = [
    {
        "name": "researcher",
        "description": (
            "Research agent for information gathering, web search, analysis, "
            "and fact-finding. Use for any task that requires looking things up "
            "or synthesizing information from multiple sources."
        ),
        "graph_id": "researcher",
    },
    {
        "name": "coder",
        "description": (
            "Code generation agent for writing, reviewing, debugging, and "
            "refactoring code. Use for any task that involves producing or "
            "analyzing source code in any programming language."
        ),
        "graph_id": "coder",
    },
]

model = ChatAnthropic(model="claude-sonnet-4-6-20250514")

graph = create_deep_agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    async_subagents=ASYNC_SUBAGENTS,
)
