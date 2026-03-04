const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/+$/, "");

function buildUrl(path, query) {
  const url = new URL(`${API_BASE_URL}${path}`);
  if (query) {
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, value);
      }
    });
  }
  return url.toString();
}

async function request(path, options = {}) {
  const { method = "GET", body, query } = options;
  const response = await fetch(buildUrl(path, query), {
    method,
    headers: {
      "Content-Type": "application/json",
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const payload = await response.json();
      detail = payload.detail || JSON.stringify(payload);
    } catch {
      detail = await response.text();
    }
    throw new Error(detail || `HTTP ${response.status}`);
  }

  if (response.status === 204) {
    return null;
  }
  return response.json();
}

export const apiBaseUrl = API_BASE_URL;

export const api = {
  listChatrooms: (query) => request("/omni/chatrooms", { query }),
  createChatroom: (payload) => request("/omni/chatrooms", { method: "POST", body: payload }),
  getChatroomAI: (chatroomId) => request(`/omni/chatrooms/${chatroomId}/ai`),
  updateChatroomAIStatus: (chatroomId, enabled) =>
    request(`/omni/chatrooms/${chatroomId}/ai/status`, {
      method: "PUT",
      body: { enabled },
    }),
  pauseChatroomAI: (chatroomId) => request(`/omni/chatrooms/${chatroomId}/ai/pause`, { method: "POST" }),
  updateChatroomSchedule: (chatroomId, scheduleStart, scheduleEnd, timezone) =>
    request(`/omni/chatrooms/${chatroomId}/ai/schedule`, {
      method: "PUT",
      body: {
        ai_schedule_start: scheduleStart,
        ai_schedule_end: scheduleEnd,
        timezone,
      },
    }),
  listThreads: (chatroomId, query) => request(`/omni/chatrooms/${chatroomId}/threads`, { query }),
  listMessages: (threadId, query) => request(`/omni/threads/${threadId}/messages`, { query }),
  sendMessage: (threadId, payload) => request(`/omni/threads/${threadId}/messages`, { method: "POST", body: payload }),
  simulateIncoming: (payload) => request("/omni/simulate", { method: "POST", body: payload }),
};
