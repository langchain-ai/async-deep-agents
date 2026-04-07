/**
 * Limit how many async subagent jobs may be non-terminal at once (backpressure).
 *
 * Wraps launch tools from Deep Agents async middleware. State keys: `async_tasks`
 * (current deepagents), or legacy `async_subagent_jobs` / `asyncSubagentJobs`.
 */

import { ToolMessage } from "@langchain/core/messages";
import { createMiddleware } from "langchain";

const LAUNCH_TOOL_NAMES = new Set([
  "start_async_task",
  "launch_async_subagent",
]);

const TERMINAL = new Set([
  "success",
  "error",
  "cancelled",
  "timeout",
  "interrupted",
]);

function tasksRecord(
  state: Record<string, unknown>,
): Record<string, { status?: string }> {
  const raw =
    (state.async_tasks as Record<string, { status?: string }> | undefined) ??
    (state.async_subagent_jobs as Record<string, { status?: string }> | undefined) ??
    (state.asyncSubagentJobs as Record<string, { status?: string }> | undefined);
  return raw && typeof raw === "object" ? raw : {};
}

/** Count tracked async jobs whose status is not terminal. */
export function countActiveAsyncTasks(state: Record<string, unknown>): number {
  let n = 0;
  for (const task of Object.values(tasksRecord(state))) {
    const s = task?.status;
    if (typeof s === "string" && !TERMINAL.has(s)) n += 1;
  }
  return n;
}

function defaultMaxConcurrent(): number {
  const raw = process.env.MAX_CONCURRENT_ASYNC_TASKS ?? "8";
  const value = parseInt(raw, 10);
  if (!Number.isFinite(value) || value < 1) {
    throw new Error(
      `MAX_CONCURRENT_ASYNC_TASKS must be a positive integer, got ${JSON.stringify(raw)}`,
    );
  }
  return value;
}

export type MaxConcurrentAsyncTasksOptions = {
  /** Max non-terminal async jobs; defaults from env `MAX_CONCURRENT_ASYNC_TASKS` or 8. */
  maxConcurrent?: number;
};

export function maxConcurrentAsyncTasksMiddleware(
  options?: MaxConcurrentAsyncTasksOptions,
) {
  const max =
    options?.maxConcurrent !== undefined
      ? options.maxConcurrent
      : defaultMaxConcurrent();
  if (max < 1) {
    throw new Error("maxConcurrent must be >= 1");
  }

  return createMiddleware({
    name: "MaxConcurrentAsyncTasksMiddleware",
    wrapToolCall: async (request, handler) => {
      if (!LAUNCH_TOOL_NAMES.has(request.toolCall.name)) {
        return handler(request);
      }
      const active = countActiveAsyncTasks(
        request.state as Record<string, unknown>,
      );
      if (active >= max) {
        const msg =
          `Concurrent async subagent limit reached (${active}/${max}). ` +
          "Do not start another background job until a task finishes or is cancelled. " +
          "Use check_async_task / list_async_tasks (or legacy check/list tools) for status, " +
          "or cancel_async_task to free a slot. Explain this to the user.";
        return new ToolMessage({
          content: msg,
          tool_call_id: request.toolCall.id ?? "",
        });
      }
      return handler(request);
    },
  });
}
