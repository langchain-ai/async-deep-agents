/**
 * Deep agent that orchestrates async subagents.
 *
 * This is the main agent that users interact with. It uses the
 * `createAsyncSubagentMiddleware` from deepagents to launch, monitor, and
 * manage background jobs running on the researcher and coder subagent graphs.
 *
 * When deployed to LangGraph Platform with all graphs in the same
 * `langgraph.ts.json`, the `url` field is omitted from the AsyncSubagent specs.
 * This uses ASGI transport -- the subagents run in the same process as the
 * supervisor, no external networking required.
 */

import { ChatAnthropic } from "@langchain/anthropic";
import { createDeepAgent } from "deepagents";

import { maxConcurrentAsyncTasksMiddleware } from "./middleware/maxConcurrentAsyncTasks.js";

const SYSTEM_PROMPT = `\
## How to work:
1. When the user asks for something, decide if it needs research, coding, or both
2. Launch the appropriate subagent(s) -- you can run multiple in parallel
3. Report the job ID(s) to the user and let them know work is in progress
4. When asked, check on job status and relay results
5. For complex tasks, you can chain subagents: research first, then code based on findings

## Important:
- Always launch subagents for non-trivial tasks rather than trying to do everything yourself
- You can launch multiple subagents in parallel when needed, up to the deployment's concurrent job limit
- After launching, return control to the user -- don't auto-check status
- If a launch is refused due to too many running jobs, tell the user and offer to check status or cancel tasks`;

/** Remote async subagents (graphId + ASGI). Typed as SubAgent[] until deepagents exposes async specs. */
const asyncStyleSubagents = [
  {
    name: "researcher",
    description:
      "Research agent for information gathering, web search, analysis, " +
      "and fact-finding. Use for any task that requires looking things up " +
      "or synthesizing information from multiple sources.",
    graphId: "researcher",
  },
  {
    name: "coder",
    description:
      "Code generation agent for writing, reviewing, debugging, and " +
      "refactoring code. Use for any task that involves producing or " +
      "analyzing source code in any programming language.",
    graphId: "coder",
  },
] as const;

const model = new ChatAnthropic({
  model: "claude-sonnet-4-6-20250514",
});

const maxConcurrentRaw = process.env.MAX_CONCURRENT_ASYNC_TASKS;
const maxConcurrent =
  maxConcurrentRaw !== undefined && maxConcurrentRaw !== ""
    ? parseInt(maxConcurrentRaw, 10)
    : undefined;

export const graph = createDeepAgent({
  model,
  systemPrompt: SYSTEM_PROMPT,
  middleware: [
    maxConcurrentAsyncTasksMiddleware(
      maxConcurrent !== undefined && Number.isFinite(maxConcurrent)
        ? { maxConcurrent }
        : {},
    ),
  ],
  // @ts-expect-error graphId marks LangGraph Platform async subagents; types lag deepagents.
  subagents: [...asyncStyleSubagents],
});
