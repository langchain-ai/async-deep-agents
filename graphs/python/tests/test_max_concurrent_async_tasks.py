"""Tests for async subagent concurrency guard."""

from middleware.max_concurrent_async_tasks import count_active_async_tasks


def test_count_active_async_tasks_empty() -> None:
    assert count_active_async_tasks({}) == 0


def test_count_active_async_tasks_ignores_terminal() -> None:
    state = {
        "async_tasks": {
            "a": {"status": "success"},
            "b": {"status": "running"},
            "c": {"status": "cancelled"},
        }
    }
    assert count_active_async_tasks(state) == 1


def test_count_legacy_async_subagent_jobs_key() -> None:
    state = {
        "async_subagent_jobs": {
            "x": {"status": "running"},
            "y": {"status": "error"},
        }
    }
    assert count_active_async_tasks(state) == 1
