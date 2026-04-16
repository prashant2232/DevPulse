const BASE = process.env.REACT_APP_API_URL || "http://localhost:8000";

async function apiFetch(path) {
  try {
    const res = await fetch(`${BASE}${path}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error(`[api] ${path} failed:`, err.message);
    return null;
  }
}

export const fetchHealth  = () => apiFetch("/api/health");
export const fetchMetrics = () => apiFetch("/api/metrics");
export const fetchAlerts  = () => apiFetch("/api/alerts");
export const fetchDigest  = () => apiFetch("/api/digest");

export async function triggerDigest() {
  try {
    const res = await fetch(`${BASE}/api/digest/trigger`, { method: "POST" });
    return res.ok;
  } catch {
    return false;
  }
}