import axios from "axios";
import { apiBaseUrl } from "./config";

const aiApi = axios.create({
  baseURL: `${apiBaseUrl}/ai`
});

aiApi.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export type AIAction = "ask" | "summary" | "rewrite";
export type RewriteMode = "polish" | "expand" | "translate";

export interface AIResult {
  action: string;
  model: string;
  content: string;
  elapsedMs: number;
}

export interface AIHistoryItem {
  id: number;
  documentId: number;
  userId: number;
  role: "user" | "assistant";
  action: string;
  content: string;
  model: string;
  elapsedMs: number;
  createdAt?: string;
}

export interface KnowledgeSearchHit {
  documentId: number;
  title: string;
  chunkIndex: number;
  content: string;
  score: number;
  matchedTerms: string[];
}

export interface KnowledgeAgentResult {
  question: string;
  answer: string;
  citations: KnowledgeSearchHit[];
  refusal: boolean;
  model: string;
  elapsedMs: number;
  trace: {
    workflow: string[];
    retrievedChunks: number;
  };
}

export type AgentRunStatus =
  | "planning"
  | "executing"
  | "awaiting_approval"
  | "completed"
  | "failed"
  | "cancelled";

export interface AgentPlanStep {
  id: string;
  kind: "tool" | "model";
  tool: string;
  args: Record<string, unknown>;
  reason: string;
  status: string;
  output?: Record<string, unknown>;
}

export interface AgentTraceEvent {
  stepId: string;
  kind: string;
  tool: string;
  status: string;
  durationMs: number;
  outputPreview?: unknown;
}

export interface AgentRun {
  runId: number;
  goal: string;
  documentId?: number;
  status: AgentRunStatus;
  plan: AgentPlanStep[];
  trace: AgentTraceEvent[];
  memories: Array<Record<string, unknown>>;
  result: string;
  model: string;
  error?: string | null;
  pendingApproval?: AgentPlanStep | null;
  createdAt?: string;
  updatedAt?: string;
}

export interface AgentToolSpec {
  name: string;
  description: string;
  readOnly: boolean;
  requiresApproval: boolean;
  inputSchema: Record<string, string>;
}

export const searchKnowledge = (
  query: string,
  options: { documentId?: number; topK?: number } = {}
) =>
  aiApi.get("/knowledge/search", {
    params: {
      q: query,
      documentId: options.documentId,
      topK: options.topK ?? 8
    }
  });

export const queryKnowledgeAgent = (
  question: string,
  options: { documentId?: number; topK?: number } = {}
) =>
  aiApi.post("/agent/query", {
    question,
    documentId: options.documentId,
    topK: options.topK ?? 6
  });

export const runAgent = (goal: string, documentId?: number) =>
  aiApi.post<{ success: boolean; data: AgentRun }>("/agent/run", {
    goal,
    documentId
  });

export const approveAgentRun = (runId: number, approved: boolean) =>
  aiApi.post<{ success: boolean; data: AgentRun }>(
    `/agent/runs/${runId}/approval`,
    { approved }
  );

export const getAgentRun = (runId: number) =>
  aiApi.get<{ success: boolean; data: AgentRun }>(`/agent/runs/${runId}`);

export const getAgentRuns = (documentId?: number) =>
  aiApi.get<{ success: boolean; data: AgentRun[] }>("/agent/runs", {
    params: { documentId }
  });

export const getAgentTools = () =>
  aiApi.get<{ success: boolean; data: AgentToolSpec[] }>("/agent/tools");

export const getAgentMemories = (documentId?: number) =>
  aiApi.get<{ success: boolean; data: Array<Record<string, unknown>> }>(
    "/agent/memories",
    { params: { documentId } }
  );

export const askAI = (documentId: number, question: string) =>
  aiApi.post(`/documents/${documentId}/ask`, { question });

export const summarizeDocument = (documentId: number) =>
  aiApi.post(`/documents/${documentId}/summary`);

export const rewriteSelection = (
  documentId: number,
  selectedText: string,
  mode: RewriteMode
) => aiApi.post(`/documents/${documentId}/rewrite`, { selectedText, mode });

export const getAIHistory = (documentId: number) =>
  aiApi.get(`/documents/${documentId}/messages`);

export interface StreamRequest {
  action: AIAction;
  question?: string;
  selectedText?: string;
  mode?: RewriteMode;
}

interface StreamEvent {
  event: string;
  data: Record<string, unknown>;
}

export const streamAI = async (
  documentId: number,
  payload: StreamRequest,
  onEvent: (event: StreamEvent) => void
) => {
  const token = sessionStorage.getItem("token");
  const response = await fetch(`${apiBaseUrl}/ai/documents/${documentId}/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok || !response.body) {
    throw new Error(`AI 请求失败 (${response.status})`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const consume = (chunk: string) => {
    buffer += chunk;
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";

    for (const rawEvent of events) {
      const eventName = rawEvent.match(/^event:\s*(.+)$/m)?.[1] || "message";
      const dataLine = rawEvent.match(/^data:\s*(.+)$/m)?.[1];
      if (!dataLine) continue;
      onEvent({ event: eventName, data: JSON.parse(dataLine) });
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    consume(decoder.decode(value, { stream: true }));
  }
  consume(decoder.decode());
};
