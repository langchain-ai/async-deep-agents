/**
 * Coder subagent graph.
 *
 * A specialized agent for code generation, review, and debugging tasks.
 * This graph runs as an async subagent -- the supervisor launches it as a
 * background job and checks on it later.
 *
 * When deployed via `langgraph.ts.json`, this graph is addressable by its
 * graph ID ("coder") and the supervisor reaches it via ASGI transport.
 *
 * ## Completion notifications
 *
 * By default, the supervisor only learns about completion when it calls
 * `check_async_subagent`. To enable push notifications, see the commented-out
 * graph factory at the bottom of this file and `completion_notifier.ts`.
 */

import { ChatAnthropic } from "@langchain/anthropic";
import { createAgent } from "langchain";
import { tool } from "@langchain/core/tools";
import { z } from "zod";

const SYSTEM_PROMPT = `\
You are a code generation agent specializing in writing, reviewing, and
debugging code.

Your job is to produce high-quality code based on the requirements you've been
given. Focus on:

1. Correctness -- code should work as specified
2. Clarity -- use clear variable names, add comments for complex logic
3. Best practices -- follow language idioms and conventions
4. Error handling -- handle edge cases and provide useful error messages
5. Testing -- suggest or include test cases when appropriate

Always include the programming language in code fence blocks.
Take your time to produce clean, production-ready code.`;

const runCodeCheck = tool(
  async (input) => {
    // In a real deployment, this could run linters, type checkers, or even
    // execute code in a sandbox
    const lineCount = input.code.trim().split("\n").length;
    return (
      `Code check (${input.language}):\n` +
      `- Lines: ${lineCount}\n` +
      `- Syntax: OK (placeholder)\n` +
      `- Style: OK (placeholder)\n` +
      `\nIn production, connect to actual linters/type checkers here.`
    );
  },
  {
    name: "run_code_check",
    description: "Run a basic check on generated code.",
    schema: z.object({
      code: z.string().describe("The source code to check."),
      language: z
        .string()
        .describe("The programming language (e.g., 'python', 'typescript')."),
    }),
  },
);

const generateTests = tool(
  async (input) => {
    const fw = input.framework ?? "auto";
    return (
      `Test generation (${input.language}, framework=${fw}):\n` +
      `- Unit tests for public functions\n` +
      `- Edge case coverage\n` +
      `- Integration test suggestions\n` +
      `\nThis is a placeholder. The LLM generates the actual test code.`
    );
  },
  {
    name: "generate_tests",
    description: "Generate test cases for the given code.",
    schema: z.object({
      code: z.string().describe("The source code to generate tests for."),
      language: z.string().describe("The programming language."),
      framework: z
        .string()
        .optional()
        .describe(
          "Testing framework to use (e.g., 'pytest', 'vitest'). Defaults to 'auto'.",
        ),
    }),
  },
);

const model = new ChatAnthropic({
  model: "claude-sonnet-4-6-20250514",
});

// --- Static graph (no completion notifications) ---

export const graph = createAgent({
  model,
  tools: [runCodeCheck, generateTests],
  systemPrompt: SYSTEM_PROMPT,
  name: "coder",
});

// --- Dynamic graph factory with completion notifications ---
// Uncomment this block and comment out the static `graph` above to enable
// push notifications back to the supervisor when this subagent finishes.
//
// import { type RunnableConfig } from "@langchain/core/runnables";
// import { buildCompletionNotifier } from "./middleware/completionNotifier.js";
//
// export async function* graph(config: RunnableConfig) {
//   const configurable = (config as any).configurable ?? {};
//   const notifier = buildCompletionNotifier({
//     parentThreadId: configurable.parentThreadId,
//     parentAssistantId: configurable.parentAssistantId,
//     subagentName: "coder",
//   });
//   yield createAgent({
//     model,
//     tools: [runCodeCheck, generateTests],
//     systemPrompt: SYSTEM_PROMPT,
//     middleware: [notifier],
//     name: "coder",
//   });
// }
