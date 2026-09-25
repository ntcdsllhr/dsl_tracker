// Thin wrapper around fetch() for the DSL Technical Records API.
// Token is kept in localStorage; every request attaches `Authorization: Token <t>`.

const TOKEN_KEY = "dsl_tracker_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function request(path, { method = "GET", body, params } = {}) {
  let url = `/api${path}`;
  if (params) {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "")
    ).toString();
    if (qs) url += `?${qs}`;
  }

  const headers = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers["Authorization"] = `Token ${token}`;

  const res = await fetch(url, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401) {
    clearToken();
    throw new Error("Session expired. Please log in again.");
  }

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (data.detail) {
        detail = data.detail;
      } else if (data && typeof data === "object") {
        // DRF validation errors come back as { field: ["message", ...], ... }
        // (or "non_field_errors" for things like the unique-together port
        // check) — turn that into one readable line instead of raw JSON.
        const parts = Object.entries(data).map(([field, messages]) => {
          const text = Array.isArray(messages) ? messages.join(" ") : messages;
          return field === "non_field_errors" ? text : `${field}: ${text}`;
        });
        if (parts.length) detail = parts.join(" · ");
      }
    } catch {
      /* ignore parse errors */
    }
    throw new Error(detail);
  }

  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  getDashboardStats: () => request("/dashboard/stats/"),

  // Activity / reporting
  listActivity: (params) => request("/activity/", { params }),
  getActivityStats: () => request("/activity/stats/"),
  getActivityReport: (period) => request("/activity/report/", { params: { period } }),
  getCustomerHistory: (id, params) => request(`/customers/${id}/history/`, { params }),

  login: (username, password) =>
    request("/auth/token/", { method: "POST", body: { username, password } }),

  // Customers (technician's main list/search screen)
  listCustomers: (params) => request("/customers/", { params }),
  getCustomer: (id) => request(`/customers/${id}/`),
  createCustomer: (body) => request("/customers/", { method: "POST", body }),
  updateCustomer: (id, body) => request(`/customers/${id}/`, { method: "PATCH", body }),
  deleteCustomer: (id) => request(`/customers/${id}/`, { method: "DELETE" }),

  // DSL service
  createDslService: (body) => request("/dsl-services/", { method: "POST", body }),
  updateDslService: (id, body) => request(`/dsl-services/${id}/`, { method: "PATCH", body }),

  // Copper pair
  createCopperPair: (body) => request("/copper-pairs/", { method: "POST", body }),
  updateCopperPair: (id, body) => request(`/copper-pairs/${id}/`, { method: "PATCH", body }),

  // Complaints / fault history
  listComplaints: (params) => request("/complaints/", { params }),
  createComplaint: (body) => request("/complaints/", { method: "POST", body }),
  updateComplaint: (id, body) => request(`/complaints/${id}/`, { method: "PATCH", body }),
  deleteComplaint: (id) => request(`/complaints/${id}/`, { method: "DELETE" }),

  // Lookups (for filter dropdowns / forms)
  listRegions: () => request("/regions/"),
  listCities: (params) => request("/cities/", { params }),
  listMsags: (params) => request("/msags/", { params }),
};
