// Thin wrapper around fetch: adds the auth token and turns errors into readable messages.

const BASE_URL: string = import.meta.env.VITE_API_URL || "/api";
const TOKEN_KEY = "fixflow_token";
const TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_SECONDS || 25) * 1000;
const SERVER_DOWN =
  "Cannot reach the FixFlow server. Make sure the backend is running (uvicorn on port 8000) and try again.";

export const tokenStore = {
  get: () => sessionStorage.getItem(TOKEN_KEY) ?? localStorage.getItem(TOKEN_KEY),
  set: (token: string, remember = true) => {
    tokenStore.clear();
    (remember ? localStorage : sessionStorage).setItem(TOKEN_KEY, token);
  },
  clear: () => {
    localStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(TOKEN_KEY);
  },
};

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

type Scalar = string | number | boolean | undefined | null;
type Params = Record<string, Scalar | Scalar[]>;

const labelFor = (field: string) => field.replace(/_id$/, "").replace(/_/g, " ");

/** The API returns either a sentence or a list of field problems. */
function readableError(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: { field?: string; message?: string; loc?: string[]; msg?: string }) => {
        const field = d.field ?? (d.loc ?? []).slice(1).join(" ");
        const message = (d.message ?? d.msg ?? "is not valid").replace(/^Value error, /, "");
        return field ? `${labelFor(field)}: ${message}` : message;
      })
      .join(" · ");
  }
  return "Something went wrong. Please try again.";
}

async function request<T>(method: string, path: string, body?: unknown, params?: Params): Promise<T> {
  const query = new URLSearchParams();
  Object.entries(params ?? {}).forEach(([key, value]) => {
    const values = Array.isArray(value) ? value : [value];
    values.forEach((v) => {
      if (v !== undefined && v !== null && v !== "" && v !== false) query.append(key, String(v));
    });
  });
  const url = `${BASE_URL}${path}${query.toString() ? `?${query}` : ""}`;

  const headers: Record<string, string> = {};
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  let response: Response;
  try {
    response = await fetch(url, {
      method, headers, signal: controller.signal, body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (err) {
    const timedOut = (err as Error).name === "AbortError";
    throw new ApiError(timedOut ? `The server did not answer in ${TIMEOUT_MS / 1000} seconds. ${SERVER_DOWN}` : SERVER_DOWN, 0);
  } finally {
    clearTimeout(timer);
  }

  if (response.status === 401 && token) {
    // Session ended (expired, signed out elsewhere, or access changed).
    tokenStore.clear();
    window.dispatchEvent(new Event("fixflow:unauthorized"));
  }
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    // The dev proxy answers 5xx with an empty body when the backend is not running.
    if (data === null && response.status >= 500) throw new ApiError(SERVER_DOWN, response.status);
    throw new ApiError(readableError(data?.detail), response.status);
  }
  return (await response.json()) as T;
}

export const http = {
  get: <T>(path: string, params?: Params) => request<T>("GET", path, undefined, params),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body ?? {}),
  put: <T>(path: string, body: unknown) => request<T>("PUT", path, body),
  patch: <T>(path: string, body: unknown) => request<T>("PATCH", path, body),
};
