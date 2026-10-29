const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function request(endpoint, options = {}) {
  const url = endpoint.startsWith("http") ? endpoint : `${API_BASE}${endpoint}`;
  const config = {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  };

  try {
    const response = await fetch(url, config);
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      const errorMsg = data.detail || data.message || `Request failed with status ${response.status}`;
      throw new Error(errorMsg);
    }
    return data;
  } catch (err) {
    console.error(`API Error on [${options.method || "GET"} ${endpoint}]:`, err);
    throw err;
  }
}

export const api = {
  getHealth: () => request("/health"),
  getDashboardStats: () => request("/api/dashboard/stats"),
  
  // Agents
  getAgents: () => request("/api/agents"),
  createAgent: (agentData) => request("/api/agents", { method: "POST", body: JSON.stringify(agentData) }),
  updateAgentStatus: (agentId, status) => request(`/api/agents/${agentId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  }),

  // Borrowers
  getBorrowers: () => request("/api/borrowers"),
  createBorrower: (borrowerData) => request("/api/borrowers", { method: "POST", body: JSON.stringify(borrowerData) }),

  // Calls
  getCalls: (statusFilter = "", limit = 50) => {
    const query = statusFilter ? `?status_filter=${statusFilter}&limit=${limit}` : `?limit=${limit}`;
    return request(`/api/calls${query}`);
  },
  getCallDetail: (callId) => request(`/api/calls/${callId}`),
  initiateCall: (borrowerId, agentId) => request("/api/calls/initiate", {
    method: "POST",
    body: JSON.stringify({ borrower_id: borrowerId, agent_id: agentId }),
  }),
  simulateCall: (callId, targetStatus, failureReason = null) => request(`/api/calls/${callId}/simulate`, {
    method: "POST",
    body: JSON.stringify({ target_status: targetStatus, failure_reason: failureReason }),
  }),

  // Dialer & Pacing
  startProgressiveDialing: (batchSize = 1) => request("/api/dialer/progressive", {
    method: "POST",
    body: JSON.stringify({ batch_size: batchSize }),
  }),
  simulatePredictivePacing: (answerRate = 0.35, duration = 120, providerOverride = null) => request("/api/dialer/predictive/simulate", {
    method: "POST",
    body: JSON.stringify({
      historical_answer_rate: answerRate,
      average_call_duration: duration,
      provider_override: providerOverride,
    }),
  }),

  // Safety Decisions
  getSafetyDecisions: (limit = 50) => request(`/api/safety/decisions?limit=${limit}`),

  // Telecom Providers
  getProviderHealth: () => request("/api/providers/health"),
  updateProviderConfig: (config) => request("/api/providers/config", {
    method: "POST",
    body: JSON.stringify(config),
  }),
  toggleProviderOutage: (providerName, enableOutage) => request(`/api/providers/outage?provider_name=${providerName}&enable_outage=${enableOutage}`, {
    method: "POST",
  }),
  sendProviderWebhookEvent: (eventData) => request("/api/providers/events/webhook", {
    method: "POST",
    body: JSON.stringify(eventData),
  }),

  // Demo & Recovery
  seedDemoData: () => request("/api/demo/seed", { method: "POST" }),
  runRecovery: () => request("/api/recovery/run", { method: "POST" }),

  // Authentication
  login: (email, password) => request("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  }),
  signup: (userData) => request("/api/auth/signup", {
    method: "POST",
    body: JSON.stringify(userData),
  }),
  getMe: () => request("/api/auth/me"),
  logout: () => request("/api/auth/logout", { method: "POST" }),
};
