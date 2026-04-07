"""Limit how many async subagent jobs may be non-terminal at once (backpressure).

Intercepts launch tools from Deep Agents async middleware so the supervisor cannot
spawn unbounded LangGraph threads. Counts jobs in ``async_tasks`` (current
deepagents) or legacy ``async_subagent_jobs`` / ``asyncSubagentJobs`` keys.
"""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware, ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.types import Command

LAUNCH_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "start_async_task",
        "launch_async_subagent",
    }
)
TERMINAL_STATUSES: frozenset[str] = frozenset(
    {"success", "error", "cancelled", "timeout", "interrupted"}
)


def _tasks_map(state: Mapping[str, Any]) -> dict[str, Any]:
    raw = (
        state.get("async_tasks")
        or state.get("async_subagent_jobs")
        or state.get("asyncSubagentJobs")
    )
    if not isinstance(raw, dict):
        return {}
    return raw


def count_active_async_tasks(state: Mapping[str, Any]) -> int:
    """Return the number of tracked async jobs whose status is not terminal."""
    n = 0
    for task in _tasks_map(state).values():
        if not isinstance(task, dict):
            continue
        status = task.get("status")
        if isinstance(status, str) and status not in TERMINAL_STATUSES:
            n += 1
    return n


def _default_max_concurrent() -> int:
    raw = os.environ.get("MAX_CONCURRENT_ASYNC_TASKS", "8")
    try:
        value = int(raw)
    except ValueError as e:
        msg = f"MAX_CONCURRENT_ASYNC_TASKS must be a positive integer, got {raw!r}"
        raise ValueError(msg) from e
    if value < 1:
        msg = "MAX_CONCURRENT_ASYNC_TASKS must be >= 1"
        raise ValueError(msg)
    return value


class MaxConcurrentAsyncTasksMiddleware(AgentMiddleware):
    """Refuse new launches when too many async jobs are already in flight."""

    tools = ()

    def __init__(self, *, max_concurrent: int | None = None) -> None:
        self.max_concurrent = (
            max_concurrent if max_concurrent is not None else _default_max_concurrent()
        )
        if self.max_concurrent < 1:
            msg = "max_concurrent must be >= 1"
            raise ValueError(msg)

    def _blocked_message(self, active: int) -> str:
        return (
            f"Concurrent async subagent limit reached ({active}/{self.max_concurrent}). "
            "Do not start another background job until a task finishes or is cancelled. "
            "Use check_async_task / list_async_tasks (or legacy check/list tools) to see "
            "status, or cancel_async_task to free a slot. Explain this to the user."
        )

    def _tool_call_id(self, request: ToolCallRequest) -> str:
        tc = request.tool_call
        if isinstance(tc, dict):
            return str(tc.get("id") or "")
        return str(getattr(tc, "id", "") or "")

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        tc = request.tool_call
        name = tc["name"] if isinstance(tc, dict) else getattr(tc, "name", "")
        if name not in LAUNCH_TOOL_NAMES:
            return handler(request)
        state = request.state
        if not isinstance(state, Mapping):
            return handler(request)
        active = count_active_async_tasks(state)
        if active >= self.max_concurrent:
            return ToolMessage(
                content=self._blocked_message(active),
                tool_call_id=self._tool_call_id(request),
            )
        return handler(request)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        tc = request.tool_call
        name = tc["name"] if isinstance(tc, dict) else getattr(tc, "name", "")
        if name not in LAUNCH_TOOL_NAMES:
            return await handler(request)
        state = request.state
        if not isinstance(state, Mapping):
            return await handler(request)
        active = count_active_async_tasks(state)
        if active >= self.max_concurrent:
            return ToolMessage(
                content=self._blocked_message(active),
                tool_call_id=self._tool_call_id(request),
            )
        return await handler(request)
