import type {
  AskEntry,
  ChatMessage,
  CompanyDetailResponse,
  CompanyList,
  Problem,
  Statement,
  StatsResponse,
} from "./types";

const BASE = (process.env.LEETAPI_URL ?? "http://localhost:4000").replace(/\/$/, "");

class ApiError extends Error {
  status: number;
  requestId?: string;
  constructor(message: string, status: number, requestId?: string) {
    super(message);
    this.status = status;
    this.requestId = requestId;
  }
}

async function call<T>(
  path: string,
  init: RequestInit = {},
  signal?: AbortSignal
): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
    signal,
    cache: "no-store",
  });
  const text = await r.text();
  let body: unknown = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  if (!r.ok) {
    const detail =
      body && typeof body === "object" && "error" in body
        ? String((body as { error: string }).error)
        : (body && typeof body === "object" && "detail" in body
            ? String((body as { detail: string }).detail)
            : `HTTP ${r.status}`);
    const requestId =
      body && typeof body === "object" && "requestId" in body
        ? String((body as { requestId: string }).requestId)
        : undefined;
    throw new ApiError(detail, r.status, requestId);
  }
  return body as T;
}

export type ListProblemsParams = {
  limit?: number;
  topics?: string;
  topics_all?: string;
  difficulty?: string;
  company?: string;
  companies_all?: string;
  min_company_count?: number;
  min_frequency?: number;
  sort?: string;
  order?: "asc" | "desc";
};

export type ProblemList = { total: number; items: Problem[] };

function qs(params: Record<string, unknown>): string {
  const entries = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== null && v !== ""
  );
  if (entries.length === 0) return "";
  const parts = entries.map(
    ([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`
  );
  return `?${parts.join("&")}`;
}

export const api = {
  listProblems: (params: ListProblemsParams = {}) =>
    call<ProblemList>(`/problems${qs(params)}`),

  getProblem: (slug: string) => call<Problem>(`/problems/${encodeURIComponent(slug)}`),

  getStatement: (slug: string) =>
    call<Statement>(`/problems/${encodeURIComponent(slug)}/statement`),

  explain: (
    slug: string,
    body: {
      kind: "teacher" | "socratic";
      provider: string;
      model: string;
      persona: string;
      force?: boolean;
    },
    signal?: AbortSignal
  ) =>
    call<{ payload: Record<string, unknown>; cached: boolean; request_id: string }>(
      `/tutor/${encodeURIComponent(slug)}/explain`,
      { method: "POST", body: JSON.stringify(body) },
      signal
    ),

  complete: (
    body: {
      messages: ChatMessage[];
      provider?: string;
      model?: string;
      max_tokens?: number;
      temperature?: number;
    },
    signal?: AbortSignal
  ) =>
    call<{ text: string; provider: string; model: string; request_id: string }>(
      `/tutor/complete`,
      { method: "POST", body: JSON.stringify(body) },
      signal
    ),

  listModels: (provider: string) =>
    call<{ models: { id: string; name: string; context_length?: number }[]; error?: string }>(
      `/models${qs({ provider })}`
    ),

  cache: () => call<{ count: number; rows: unknown[] }>("/cache"),

  listCompanies: (opts: { with_topics?: boolean; limit?: number } = {}) =>
    call<CompanyList>(`/companies${qs(opts)}`),

  getCompany: (name: string) =>
    call<CompanyDetailResponse>(`/companies/${encodeURIComponent(name)}`),

  getCompanyRelated: (name: string, limit = 8) =>
    call<AskEntry[]>(`/companies/${encodeURIComponent(name)}/related${qs({ limit })}`),

  getStats: (top_problems_limit = 30) =>
    call<StatsResponse>(`/stats${qs({ top_problems_limit })}`),
};

export { ApiError };
export const LEETAPI_URL = BASE;
