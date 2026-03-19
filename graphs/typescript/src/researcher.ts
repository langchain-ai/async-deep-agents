/**
 * Researcher subagent graph.
 *
 * A specialized agent for information gathering, analysis, and research tasks.
 * This graph runs as an async subagent -- the supervisor launches it as a
 * background job and checks on it later.
 *
 * When deployed via `langgraph.ts.json`, this graph is addressable by its
 * graph ID ("researcher") and the supervisor reaches it via ASGI transport.
 */

import { ChatAnthropic } from "@langchain/anthropic";
import { createAgent } from "langchain";
import { tool } from "@langchain/core/tools";
import { z } from "zod";

const SYSTEM_PROMPT = `\
You are a research agent specializing in information gathering and analysis.

Your job is to thoroughly research the topic or question you've been given and
produce a comprehensive, well-structured response. Focus on:

1. Accuracy -- verify claims and note when information is uncertain
2. Completeness -- cover all relevant aspects of the topic
3. Structure -- organize your findings clearly with headings and bullet points
4. Sources -- mention where information could be verified when relevant

Take your time to be thorough. The supervisor agent will check on your results
when they're needed.`;

const analyzeTopic = tool(
  async (input) => {
    // In a real deployment, this could call a search API, RAG pipeline, etc.
    return (
      `Analysis of '${input.query}':\n` +
      `- Key aspects identified\n` +
      `- Related concepts mapped\n` +
      `- Potential sources noted\n` +
      `\nThis is a placeholder. In production, connect to your preferred ` +
      `search/RAG tools here.`
    );
  },
  {
    name: "analyze_topic",
    description:
      "Analyze a topic by breaking it down into key aspects and considerations.",
    schema: z.object({
      query: z.string().describe("The topic or question to analyze."),
    }),
  },
);

const summarizeFindings = tool(
  async (input) => {
    const fmt = input.format ?? "bullet_points";
    return (
      `Summary (${fmt}):\n` +
      `- Condensed key findings from provided content\n` +
      `- Organized by relevance and importance\n` +
      `\nThis is a placeholder. The LLM handles the actual summarization.`
    );
  },
  {
    name: "summarize_findings",
    description: "Summarize research findings into a structured format.",
    schema: z.object({
      content: z.string().describe("The raw research content to summarize."),
      format: z
        .string()
        .optional()
        .describe(
          "Output format -- 'bullet_points', 'narrative', or 'table'. Defaults to 'bullet_points'.",
        ),
    }),
  },
);

const model = new ChatAnthropic({
  model: "claude-sonnet-4-6-20250514",
});

export const graph = createAgent({
  model,
  tools: [analyzeTopic, summarizeFindings],
  systemPrompt: SYSTEM_PROMPT,
  name: "researcher",
});
