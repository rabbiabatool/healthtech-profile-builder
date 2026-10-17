let csrfToken = null;
let refreshInFlight = null;

export class ApiError extends Error {
  constructor(status, data) {
    super(data?.detail || "Something went wrong. Please try again.");
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

export function setCsrfToken(token) {
  csrfToken = token;
}

async function loadCsrfToken() {
  const response = await fetch("/api/auth/csrf", { cache: "no-store", credentials: "same-origin" });
  const data = await response.json();
  csrfToken = data.csrfToken;
  return csrfToken;
}

async function send(path, method, body) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (method !== "GET") {
    headers["X-CSRFToken"] = csrfToken || (await loadCsrfToken());
  }
  return fetch(path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
    credentials: "same-origin",
  });
}

async function readJson(response) {
  if (response.status === 204) return null;
  try {
    return await response.json();
  } catch {
    return null;
  }
}

export async function api(path, { method = "GET", body } = {}) {
  let response = await send(path, method, body);
  let data = await readJson(response);

  const csrfRejected =
    response.status === 403 && typeof data?.detail === "string" && data.detail.startsWith("CSRF Failed");
  if (csrfRejected) {
    csrfToken = null;
    response = await send(path, method, body);
    data = await readJson(response);
  }

  if (!response.ok) {
    throw new ApiError(response.status, data);
  }
  return data;
}

function refreshSession() {
  if (!refreshInFlight) {
    refreshInFlight = api("/api/auth/refresh", { method: "POST" }).finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

export async function userApi(path, options) {
  try {
    return await api(path, options);
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) throw error;
    try {
      await refreshSession();
    } catch {
      throw error;
    }
    return api(path, options);
  }
}

export function fieldErrors(error) {
  const result = {};
  if (error instanceof ApiError && error.status === 400 && error.data && typeof error.data === "object") {
    for (const [field, messages] of Object.entries(error.data)) {
      result[field] = Array.isArray(messages) ? messages.join(" ") : String(messages);
    }
  }
  return result;
}

export function errorMessage(error) {
  if (error instanceof ApiError) {
    return error.status === 400 ? "Please check the highlighted fields and try again." : error.message;
  }
  return "Cannot reach the server. Please check that the backend is running.";
}