// Talks to the Week 3 prediction API (Member only).
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

const CSRF_PATH = "/api/auth/csrf";

async function readJson(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

export async function fetchModelInfo() {
  const response = await fetch(`${API_BASE}/api/v1/ml/model`, {
    credentials: "include",
    cache: "no-store",
  });
  return { status: response.status, data: await readJson(response) };
}

export async function requestPrediction(modeOrPayload, maybePayload) {
  const payload = maybePayload !== undefined ? maybePayload : modeOrPayload;

  const csrfResponse = await fetch(`${API_BASE}${CSRF_PATH}`, {
    credentials: "include",
    cache: "no-store",
  });
  const csrf = await readJson(csrfResponse);

  const response = await fetch(`${API_BASE}/api/v1/ml/no-show/predict`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrf?.csrfToken ?? "",
    },
    body: JSON.stringify(payload),
  });
  return { status: response.status, data: await readJson(response) };
}
