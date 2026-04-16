import { useState } from "react";
import { triggerDigest } from "../api";

function Section({ title, body }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <p style={{ color: "var(--purple)", fontSize: 11, marginBottom: 5 }}>{title}</p>
      <p style={{ color: "#bbb", fontSize: 13, lineHeight: 1.6 }}>{body}</p>
    </div>
  );
}

function Spinner() {
  return (
    <div style={{ textAlign: "center", padding: "28px 0", color: "#444", fontSize: 13 }}>
      <div
        style={{
          width: 20,
          height: 20,
          border: "2px solid #333",
          borderTop: "2px solid var(--purple)",
          borderRadius: "50%",
          margin: "0 auto 10px",
          animation: "spin 0.8s linear infinite",
        }}
      />
      Generating digest…
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

export default function DigestCard({ digest, onRefresh }) {
  const [triggering, setTriggering] = useState(false);
  const [triggered, setTriggered]   = useState(false);

  async function handleTrigger() {
    setTriggering(true);
    const ok = await triggerDigest();
    setTriggering(false);
    if (ok) {
      setTriggered(true);
      setTimeout(() => {
        setTriggered(false);
        onRefresh?.();
      }, 4000);
    }
  }

  const hasDigest = digest && digest.summary && !digest.summary.startsWith("No digest");

  return (
    <div
      style={{
        background: "var(--surface)",
        borderRadius: 10,
        padding: "18px 16px",
        border: "1px solid var(--border)",
        borderTop: "2px solid var(--purple)",
        flex: 1,
        minWidth: 0,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
        <p style={{ color: "var(--purple)", fontSize: 11, fontWeight: 500 }}>
          Weekly AI digest
        </p>
        <button
          onClick={handleTrigger}
          disabled={triggering || triggered}
          style={{
            background: triggered ? "rgba(204,136,255,0.15)" : "transparent",
            color: triggered ? "var(--purple)" : "#555",
            border: "1px solid #333",
            borderRadius: 6,
            padding: "4px 10px",
            fontSize: 11,
            cursor: triggering ? "wait" : "pointer",
            transition: "all 0.2s",
          }}
        >
          {triggering ? "generating…" : triggered ? "check back soon" : "generate now"}
        </button>
      </div>

      {triggering ? (
        <Spinner />
      ) : !hasDigest ? (
        <div style={{ color: "#444", fontSize: 13, textAlign: "center", padding: "24px 0", lineHeight: 1.7 }}>
          No digest yet.
          <br />
          Click "generate now" to create one,
          <br />
          or wait for Monday 9am.
        </div>
      ) : (
        <>
          <Section title="Summary"        body={digest.summary} />
          <Section title="Anomalies"      body={digest.anomaly_note} />
          <Section title="Recommendation" body={digest.recommendation} />
        </>
      )}
    </div>
  );
}