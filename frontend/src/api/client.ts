import type {
  Assessment, Board, HistoryItem, PatientPublic, Profile, Progress, Results, SendMessageResult, Session,
} from "./types";

const BASE = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
const TOKEN_KEY = "ts_token";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export const tokenStore = {
  get: (): string | null => {
    try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
  },
  set: (t: string) => {
    try { localStorage.setItem(TOKEN_KEY, t); } catch { /* storage unavailable */ }
  },
  clear: () => {
    try { localStorage.removeItem(TOKEN_KEY); } catch { /* storage unavailable */ }
  },
};

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  } catch {
    throw new ApiError(0, "Can't reach the clinic server. Is the backend running?");
  }
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (typeof data.detail === "string") msg = data.detail;
      else if (Array.isArray(data.detail)) msg = data.detail.map((d: { msg: string }) => d.msg).join(", ");
    } catch { /* non-JSON error */ }
    throw new ApiError(res.status, msg);
  }
  return res.json() as Promise<T>;
}

export const api = {
  guestLogin: (display_name: string) =>
    request<{ token: string; profile: Profile }>("POST", "/api/auth/guest", { display_name }),
  me: () => request<Profile>("GET", "/api/auth/me"),
  rename: (display_name: string) => request<Profile>("PATCH", "/api/auth/me", { display_name }),

  generatePatient: (force = false) =>
    request<PatientPublic>("POST", `/api/patients/generate${force ? "?force=true" : ""}`),
  getPatient: (id: string) => request<PatientPublic>("GET", `/api/patients/${id}`),

  startSession: (patient_id: string) => request<Session>("POST", "/api/sessions/start", { patient_id }),
  getSession: (id: string) => request<Session>("GET", `/api/sessions/${id}`),
  sendMessage: (id: string, content: string) =>
    request<SendMessageResult>("POST", `/api/sessions/${id}/message`, { content }),
  getBoard: (id: string) => request<Board>("GET", `/api/sessions/${id}/board`),
  saveNotes: (id: string, notes: string) => request<Board>("POST", `/api/sessions/${id}/notes`, { notes }),
  endSession: (id: string) => request<Session>("POST", `/api/sessions/${id}/end`),
  submitAssessment: (id: string, a: Assessment) => request<Session>("POST", `/api/sessions/${id}/assessment`, a),
  evaluate: (id: string) => request<Results>("POST", `/api/sessions/${id}/evaluate`),
  results: (id: string) => request<Results>("GET", `/api/sessions/${id}/results`),

  progress: () => request<Progress>("GET", "/api/game/progress"),
  history: () => request<HistoryItem[]>("GET", "/api/sessions/history"),
};
