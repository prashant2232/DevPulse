import { useState, useEffect, useCallback } from "react";
import { fetchMetrics, fetchAlerts, fetchDigest } from "./api";
import StatusBar    from "./components/StatusBar";
import MetricCards  from "./components/MetricCards";
import CommitChart  from "./components/CommitChart";
import AlertsList   from "./components/AlertsList";
import DigestCard   from "./components/DigestCard";

const POLL_INTERVAL = 30_000;

export default function App() {
  const [metrics,     setMetrics]     = useState([]);
  const [alerts,      setAlerts]      = useState([]);
  const [digest,      setDigest]      = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [loading,     setLoading]     = useState(true);

  const refresh = useCallback(async () => {
    const [m, a, d] = await Promise.all([
      fetchMetrics(),
      fetchAlerts(),
      fetchDigest(),
    ]);
    if (m) setMetrics(m.metrics  || []);
    if (a) setAlerts(a.alerts    || []);
    if (d) setDigest(d);
    setLastUpdated(Date.now());
    setLoading(false);
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, POLL_INTERVAL);
    return () => clearInterval(id);
  }, [refresh]);

  return (
    <div
      style={{
        background: "var(--bg)",
        minHeight: "100vh",
        padding: "28px 32px",
        maxWidth: 1280,
        margin: "0 auto",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 28,
          paddingBottom: 16,
          borderBottom: "1px solid var(--border)",
        }}
      >
        <div>
          <h1
            style={{
              fontSize: 20,
              fontWeight: 500,
              color: "var(--text)",
              letterSpacing: "-0.3px",
            }}
          >
            Dev<span style={{ color: "var(--accent)" }}>Pulse</span>
          </h1>
          <p style={{ color: "var(--muted)", fontSize: 12, marginTop: 2 }}>
            Real-time developer activity intelligence
          </p>
        </div>
        <StatusBar lastUpdated={lastUpdated} />
      </div>

      {/* Loading skeleton */}
      {loading ? (
        <div style={{ color: "var(--muted)", fontSize: 13, paddingTop: 40, textAlign: "center" }}>
          Connecting to backend…
        </div>
      ) : (
        <>
          <MetricCards metrics={metrics} alerts={alerts} />
          <CommitChart metrics={metrics} />
          <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
            <AlertsList alerts={alerts} />
            <DigestCard digest={digest} onRefresh={refresh} />
          </div>
        </>
      )}
    </div>
  );
}