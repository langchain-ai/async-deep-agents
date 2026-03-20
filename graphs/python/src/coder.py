"""Coder subagent graph.

A specialized agent for code generation, review, and debugging tasks.
This graph runs as an async subagent -- the supervisor launches it as a
background job and checks on it later.

When deployed via `langgraph.json`, this graph is addressable by its graph ID
("coder") and the supervisor reaches it via ASGI transport.

## Completion notifications

By default, the supervisor only learns about completion when it calls
`check_async_subagent`. To enable push notifications, uncomment the
completion notifier wiring below. See `completion_notifier.py` for details.
"""

from __future__ import annotations

from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool

SYSTEM_PROMPT = """\
You are a code generation agent specializing in writing, reviewing, and
debugging code.

Your job is to produce high-quality code based on the requirements you've been
given. Focus on:

1. Correctness -- code should work as specified
2. Clarity -- use clear variable names, add comments for complex logic
3. Best practices -- follow language idioms and conventions
4. Error handling -- handle edge cases and provide useful error messages
5. Testing -- suggest or include test cases when appropriate

Always include the programming language in code fence blocks (e.g., ```python).
Take your time to produce clean, production-ready code.
"""


@tool
def run_code_check(code: str, language: str) -> str:
    """Run a basic check on generated code.

    Args:
        code: The source code to check.
        language: The programming language (e.g., 'python', 'typescript').
    """
    # In a real deployment, this could run linters, type checkers, or even
    # execute code in a sandbox
    line_count = len(code.strip().splitlines())
    return (
        f"Code check ({language}):\n"
        f"- Lines: {line_count}\n"
        f"- Syntax: OK (placeholder)\n"
        f"- Style: OK (placeholder)\n"
        f"\nIn production, connect to actual linters/type checkers here."
    )


@tool
def generate_tests(code: str, language: str, framework: str = "auto") -> str:
    """Generate test cases for the given code.

    Args:
        code: The source code to generate tests for.
        language: The programming language.
        framework: Testing framework to use (e.g., 'pytest', 'vitest'). Defaults to 'auto'.
    """
    return (
        f"Test generation ({language}, framework={framework}):\n"
        f"- Unit tests for public functions\n"
        f"- Edge case coverage\n"
        f"- Integration test suggestions\n"
        f"\nThis is a placeholder. The LLM generates the actual test code."
    )


model = ChatAnthropic(model="claude-sonnet-4-6-20250514")


# --- Static graph (no completion notifications) ---

graph = create_agent(
    model=model,
    tools=[run_code_check, generate_tests],
    system_prompt=SYSTEM_PROMPT,
    name="coder",
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
#         subagent_name="coder",
#     )
#     yield create_agent(
#         model=model,
#         tools=[run_code_check, generate_tests],
#         system_prompt=SYSTEM_PROMPT,
#         middleware=[notifier],
#         name="coder",
#     )
