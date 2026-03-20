"""Completion notifier middleware for async subagents.

When a subagent finishes (success or error), this middleware sends a message
to the supervisor's thread so it wakes up and can relay the result to the user
without waiting to be asked.

**This is a bring-your-own component.** The async subagent protocol does not
include a built-in notification mechanism -- by default the supervisor only
learns about completion when it (or the user) calls `check_async_subagent`.
This middleware closes that gap by pushing a notification from the subagent
back to the supervisor.

## How it works

1. The supervisor passes its own `thread_id` and `assistant_id` to the subagent
   at launch time (via `configurable` or input metadata -- this wiring is
   deployment-specific).
2. This middleware is added to the subagent's middleware stack.
3. When the subagent's run completes, the after-agent hook fires and sends a
   new run to the supervisor's thread with a summary of the result.
4. When the subagent errors, the wrap-model-call hook catches the exception,
   sends an error notification, and re-raises.

## Integration

The supervisor needs to pass its thread/assistant IDs to the subagent. How you
do this depends on your deployment:

- **Config-based** (LangSmith Agent Builder pattern): pass via
  `config.configurable.parent_thread_id` and `config.configurable.parent_assistant_id`
- **Input-based**: include in the launch message input as metadata
- **Store-based**: write to a shared LangGraph store namespace

This example uses the config-based approach. Adapt `_get_parent_ids()` to match
your deployment's conventions.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware, Runtime
from langgraph_sdk import get_client

logger = logging.getLogger(__name__)


def _get_parent_ids(config: dict[str, Any]) -> tuple[str | None, str | None]:
    """Extract parent thread and assistant IDs from the runnable config.

    Adapt this function to match how your deployment passes parent context
    to subagents. The config-based approach shown here matches the pattern
    used in LangSmith Agent Builder.
    """
    configurable = config.get("configurable", {})
    return (
        configurable.get("parent_thread_id"),
        configurable.get("parent_assistant_id"),
    )


async def _notify_parent(
    parent_thread_id: str,
    parent_assistant_id: str,
    notification: str,
    subagent_name: str,
) -> None:
    """Send a notification run to the parent's thread.

    Uses `get_client()` with no URL, which resolves to ASGI transport when
    running in the same LangGraph deployment. For remote deployments, pass
    the URL explicitly.
    """
    try:
        client = get_client()
        await client.runs.create(
            thread_id=parent_thread_id,
            assistant_id=parent_assistant_id,
            input={
                "messages": [{"role": "user", "content": notification}],
            },
        )
        logger.info(
            "Notified parent thread %s that subagent '%s' finished",
            parent_thread_id,
            subagent_name,
        )
    except Exception:
        logger.warning(
            "Failed to notify parent thread %s",
            parent_thread_id,
            exc_info=True,
        )


class CompletionNotifierMiddleware(AgentMiddleware):
    """Notifies the supervisor's thread when this subagent completes or errors.

    Add this as the last middleware in a subagent's stack so it fires after
    all other middleware has run.

    Args:
        parent_thread_id: The supervisor's thread ID to notify.
        parent_assistant_id: The supervisor's assistant ID (needed to create a run).
        subagent_name: Human-readable name for log messages and notifications.
    """

    def __init__(
        self,
        parent_thread_id: str | None,
        parent_assistant_id: str | None,
        subagent_name: str | None = None,
    ):
        self.parent_thread_id = parent_thread_id
        self.parent_assistant_id = parent_assistant_id
        self.subagent_name = subagent_name or "subagent"
        self._notified = False

    def _should_notify(self) -> bool:
        return (
            not self._notified
            and bool(self.parent_thread_id)
            and bool(self.parent_assistant_id)
        )

    async def _send_notification(self, message: str) -> None:
        if not self._should_notify():
            return
        self._notified = True
        await _notify_parent(
            self.parent_thread_id,  # type: ignore[arg-type]
            self.parent_assistant_id,  # type: ignore[arg-type]
            message,
            self.subagent_name,
        )

    def _extract_last_message(self, state: dict[str, Any]) -> str:
        """Extract a summary from the subagent's final message."""
        messages = state.get("messages", [])
        if not messages:
            return "(no output)"
        last = messages[-1]
        if hasattr(last, "content"):
            content = last.content
            return content[:500] if isinstance(content, str) else str(content)[:500]
        if isinstance(last, dict):
            return str(last.get("content", ""))[:500]
        return str(last)[:500]

    async def aafter_agent(
        self, state: dict[str, Any], runtime: Runtime
    ) -> dict[str, Any] | None:
        """After-agent hook: fires when the subagent run completes successfully."""
        summary = self._extract_last_message(state)
        await self._send_notification(
            f"[Async subagent '{self.subagent_name}' has completed] Result: {summary}"
        )
        return None

    async def awrap_model_call(self, request, handler):
        """Wrap-model-call hook: catches errors and notifies the supervisor."""
        try:
            return await handler(request)
        except Exception as e:
            await self._send_notification(
                f"[Async subagent '{self.subagent_name}' encountered an error] "
                f"Error: {e!s}"
            )
            raise


def build_completion_notifier(
    parent_thread_id: str | None,
    parent_assistant_id: str | None,
    subagent_name: str | None = None,
) -> CompletionNotifierMiddleware:
    """Build a completion notifier middleware.

    Convenience factory that mirrors the pattern used in LangSmith Agent Builder.

    Example:
        ```python
        notifier = build_completion_notifier(
            parent_thread_id=config["configurable"].get("parent_thread_id"),
            parent_assistant_id=config["configurable"].get("parent_assistant_id"),
            subagent_name="researcher",
        )
        ```
    """
    return CompletionNotifierMiddleware(
        parent_thread_id=parent_thread_id,
        parent_assistant_id=parent_assistant_id,
        subagent_name=subagent_name,
    )
