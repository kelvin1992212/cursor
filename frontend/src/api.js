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
  getAIStatus: () => request("/admin/ai/status"),
  updateAIStatus: (enabled) => request("/admin/ai/status", { method: "PUT", body: { enabled } }),
  pauseAI: () => request("/admin/ai/pause", { method: "POST" }),
  updateAISchedule: (scheduleStart, scheduleEnd, timezone) =>
    request("/admin/ai/schedule", {
      method: "PUT",
      body: {
        schedule_start: scheduleStart,
        schedule_end: scheduleEnd,
        timezone,
      },
    }),
  listAgents: () => request("/admin/agents"),
  createAgent: (payload) => request("/admin/agents", { method: "POST", body: payload }),
  listLeads: (query) => request("/crm/leads", { query }),
  getCustomer: (phone) => request(`/crm/customers/${encodeURIComponent(phone)}`),
  addCustomerTags: (phone, tags) =>
    request(`/crm/customers/${encodeURIComponent(phone)}/tags`, {
      method: "POST",
      body: { tags },
    }),
  removeCustomerTag: (phone, tagName) =>
    request(`/crm/customers/${encodeURIComponent(phone)}/tags/${encodeURIComponent(tagName)}`, {
      method: "DELETE",
    }),
  listBookings: () => request("/crm/bookings"),
  createBooking: (payload) => request("/crm/bookings", { method: "POST", body: payload }),
  listReports: (phone) => request(`/admin/reports/${encodeURIComponent(phone)}`),
  createFeedback: (payload) => request("/crm/feedback", { method: "POST", body: payload }),
  simulateIncoming: (payload) => request("/webhooks/simulate", { method: "POST", body: payload }),
};
