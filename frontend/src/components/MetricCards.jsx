function Card({ label, value, color = "var(--text)", highlight = false }) {
  return (
    <div
      style={{
        background: "var(--surface)",
        borderRadius: 10,
        padding: "14px 18px",
        border: highlight ? "1px solid rgba(255,68,68,0.3)" : "1px solid var(--border)",
        flex: 1,
        minWidth: 120,
      }}
    >
      <p style={{ color: "var(--muted)", fontSize: 11, marginBottom: 8 }}>{label}</p>
      <p style={{ color, fontSize: 24, fontWeight: 500, lineHeight: 1 }}>{value}</p>
    </div>
  );
}

export default function MetricCards({ metrics, alerts }) {
  const totalCommits = metrics.reduce((s, m) => s + m.commits, 0);
  const developers   = new Set(metrics.map((m) => m.developer)).size;
  const repos        = new Set(metrics.map((m) => m.repo)).size;
  const anomalies    = alerts.length;

  return (
    <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 20 }}>
      <Card label="Total commits (7d)"  value={totalCommits} color="var(--text)" />
      <Card label="Active developers"   value={developers}   color="var(--accent)" />
      <Card label="Anomalies today"     value={anomalies}    color={anomalies > 0 ? "var(--danger)" : "var(--success)"} highlight={anomalies > 0} />
      <Card label="Repos tracked"       value={repos}        color="var(--purple)" />
    </div>
  );
}