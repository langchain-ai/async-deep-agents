/**
 * Completion notifier middleware for async subagents.
 *
 * When a subagent finishes (success or error), this middleware sends a message
 * to the supervisor's thread so it wakes up and can relay the result to the user
 * without waiting to be asked.
 *
 * **This is a bring-your-own component.** The async subagent protocol does not
 * include a built-in notification mechanism -- by default the supervisor only
 * learns about completion when it (or the user) calls `check_async_subagent`.
 * This middleware closes that gap by pushing a notification from the subagent
 * back to the supervisor.
 *
 * ## How it works
 *
 * 1. The supervisor passes its own `threadId` and `assistantId` to the subagent
 *    at launch time (via config or input metadata).
 * 2. This middleware is added to the subagent's middleware stack.
 * 3. When the subagent's run completes, `afterAgent` fires and sends a new run
 *    to the supervisor's thread with a summary of the result.
 * 4. When the subagent errors, `wrapModelCall` catches the exception, sends
 *    an error notification, and re-throws.
 *
 * ## Integration
 *
 * The supervisor needs to pass its thread/assistant IDs to the subagent. How you
 * do this depends on your deployment. This example reads from LangGraph config.
 * Adapt `getParentIds()` to match your deployment's conventions.
 */

import { Client } from "@langchain/langgraph-sdk";
import { createMiddleware } from "langchain";

/**
 * Send a notification run to the parent supervisor's thread.
 *
 * Uses a Client with no URL, which resolves to ASGI transport when running
 * in the same LangGraph deployment.
 */
async function notifyParent(
  parentThreadId: string,
  parentAssistantId: string,
  notification: string,
  subagentName: string,
): Promise<void> {
  try {
    const client = new Client();
    await client.runs.create(parentThreadId, parentAssistantId, {
      input: {
        messages: [{ role: "user", content: notification }],
      },
    });
    console.log(
      `Notified parent thread ${parentThreadId} that subagent '${subagentName}' finished`,
    );
  } catch (e) {
    console.warn(
      `Failed to notify parent thread ${parentThreadId}: ${e}`,
    );
  }
}

/**
 * Extract a summary from the subagent's last message (up to 500 chars).
 */
function extractLastMessage(
  state: Record<string, unknown>,
): string {
  const messages = (state.messages ?? []) as unknown[];
  if (messages.length === 0) return "(no output)";

  const last = messages[messages.length - 1];
  if (typeof last === "object" && last !== null && "content" in last) {
    const content = (last as Record<string, unknown>).content;
    return typeof content === "string"
      ? content.slice(0, 500)
      : String(content).slice(0, 500);
  }
  return String(last).slice(0, 500);
}

/**
 * Build a completion notifier middleware for a subagent.
 *
 * @param parentThreadId - The supervisor's thread ID to notify.
 * @param parentAssistantId - The supervisor's assistant ID (needed to create a run).
 * @param subagentName - Human-readable name for log messages and notifications.
 *
 * @example
 * ```ts
 * const notifier = buildCompletionNotifier({
 *   parentThreadId: config.configurable?.parentThreadId,
 *   parentAssistantId: config.configurable?.parentAssistantId,
 *   subagentName: "researcher",
 * });
 *
 * const graph = createAgent({
 *   model,
 *   tools,
 *   middleware: [notifier],
 * });
 * ```
 */
export function buildCompletionNotifier(options: {
  parentThreadId?: string;
  parentAssistantId?: string;
  subagentName?: string;
}) {
  const {
    parentThreadId,
    parentAssistantId,
    subagentName = "subagent",
  } = options;

  let notified = false;

  function shouldNotify(): boolean {
    return !notified && !!parentThreadId && !!parentAssistantId;
  }

  async function sendNotification(message: string): Promise<void> {
    if (!shouldNotify()) return;
    notified = true;
    await notifyParent(
      parentThreadId!,
      parentAssistantId!,
      message,
      subagentName,
    );
  }

  return createMiddleware({
    name: "completionNotifier",

    afterAgent: async (state: Record<string, unknown>) => {
      const summary = extractLastMessage(state);
      await sendNotification(
        `[Async subagent '${subagentName}' has completed] Result: ${summary}`,
      );
      return undefined;
    },

    wrapModelCall: async (request, handler) => {
      try {
        return await handler(request);
      } catch (e) {
        await sendNotification(
          `[Async subagent '${subagentName}' encountered an error] Error: ${e}`,
        );
        throw e;
      }
    },
  });
}
