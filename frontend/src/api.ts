import type { ResultResponse, StatusResponse, WorkflowListItem } from "./types";


const KEY_STORAGE = "shorts_api_key";

export function getApiKey(): string {
  return localStorage.getItem(KEY_STORAGE)?.trim() || "";
}

export function setApiKey(key: string): void {
  localStorage.setItem(KEY_STORAGE, key.trim());
}

export function apiBase(): string {
  const fromEnv = import.meta.env.VITE_API_BASE as string | undefined;
  if (fromEnv && fromEnv.trim()) {
    return fromEnv.replace(/\/$/, "");
  }
  return "";
}

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const key = getApiKey();
  if (!key) {
    throw new ApiError(401, "Set an API key on the Settings page first.");
  }
  const headers = new Headers(init.headers);
  headers.set("X-API-Key", key);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(`${apiBase()}${path}`, { ...init, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") {
        detail = body.detail;
      } else if (body.detail != null) {
        detail = JSON.stringify(body.detail);
      }
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

export async function createShort(payload: {
  topic: string;
  audience: string;
  hitl_required: boolean;
  max_iterations: number;
}): Promise<{ workflow_id: string; status: string }> {
  return request("/shorts", {
    method: "POST",
    headers: { "Idempotency-Key": crypto.randomUUID() },
    body: JSON.stringify(payload),
  });
}

export async function listShorts(
  limit = 20,
  offset = 0,
): Promise<{ items: WorkflowListItem[]; limit: number; offset: number }> {
  return request(`/shorts?limit=${limit}&offset=${offset}`);
}

export async function getStatus(workflowId: string): Promise<StatusResponse> {
  return request(`/shorts/${workflowId}`);
}

export async function getResult(workflowId: string): Promise<ResultResponse> {
  return request(`/shorts/${workflowId}/result`);
}

export async function approve(
  workflowId: string,
  reviewer = "web",
): Promise<{ workflow_id: string; job_id: string; status: string }> {
  return request(`/shorts/${workflowId}/approve`, {
    method: "POST",
    body: JSON.stringify({ reviewer, feedback: null }),
  });
}

export async function revise(
  workflowId: string,
  feedback: string,
  decision: "request_changes" | "reject" = "request_changes",
): Promise<{ workflow_id: string; job_id: string; status: string }> {
  return request(`/shorts/${workflowId}/revise`, {
    method: "POST",
    body: JSON.stringify({ feedback, decision, reviewer: "web" }),
  });
}

export { ApiError };
