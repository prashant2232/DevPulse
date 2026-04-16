function severity(score) {
  const s = parseFloat(score || 0);
  if (s < -0.2) return { label: "critical", color: "#ff2222" };
  if (s < -0.1) return { label: "high",     color: "var(--danger)" };
  return           { label: "medium",    color: "#ff8800" };
}

function Badge({ label, color }) {
  return (
    <span
      style={{
        background: `${color}22`,
        color,
        fontSize: 10,
        fontWeight: 500,
        padding: "2px 7px",
        borderRadius: 4,
        border: `1px solid ${color}44`,
        textTransform: "uppercase",
        letterSpacing: "0.05em",
      }}
    >
      {label}
    </span>
  );
}

function formatTime(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "UTC",
      hour12: false,
    }) + " UTC";
  } catch {
    return iso;
  }
}

export default function AlertsList({ alerts }) {
  return (
    <div
      style={{
        background: "var(--surface)",
        borderRadius: 10,
        padding: "18px 16px",
        border: "1px solid var(--border)",
        flex: 1,
        minWidth: 0,
      }}
    >
      <p style={{ color: "var(--muted)", fontSize: 11, marginBottom: 14 }}>
        Anomaly alerts
        {alerts.length > 0 && (
          <span
            style={{
              marginLeft: 8,
              background: "rgba(255,68,68,0.15)",
              color: "var(--danger)",
              fontSize: 10,
              padding: "1px 6px",
              borderRadius: 4,
            }}
          >
            {alerts.length}
          </span>
        )}
      </p>

      {alerts.length === 0 ? (
        <p style={{ color: "#444", fontSize: 13, textAlign: "center", padding: "24px 0" }}>
          No anomalies detected
        </p>
      ) : (
        alerts.map((alert, i) => {
          const sev = severity(alert.score);
          return (
            <div
              key={i}
              style={{
                border: `1px solid ${sev.color}55`,
                borderLeft: `3px solid ${sev.color}`,
                borderRadius: "0 8px 8px 0",
                padding: "10px 12px",
                marginBottom: 8,
                background: `${sev.color}08`,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 4 }}>
                <p style={{ color: sev.color, fontWeight: 500, fontSize: 13 }}>
                  {alert.developer}
                </p>
                <Badge label={sev.label} color={sev.color} />
              </div>
              <p style={{ color: "#666", fontSize: 11, marginBottom: 3 }}>
                {alert.repo}
                {alert.commits_today && ` · ${alert.commits_today} commits today`}
              </p>
              <p style={{ color: "#444", fontSize: 11 }}>
                score {parseFloat(alert.score || 0).toFixed(3)} · {formatTime(alert.detected_at)}
              </p>
            </div>
          );
        })
      )}
    </div>
  );
}