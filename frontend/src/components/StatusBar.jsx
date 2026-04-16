import { useState, useEffect } from "react";
import { fetchHealth } from "../api";

const dot = (color) => ({
  width: 7,
  height: 7,
  borderRadius: "50%",
  background: color,
  display: "inline-block",
  marginRight: 6,
  flexShrink: 0,
});

export default function StatusBar({ lastUpdated }) {
  const [connected, setConnected] = useState(null);

  useEffect(() => {
    const check = async () => {
      const data = await fetchHealth();
      setConnected(data?.status === "ok");
    };
    check();
    const id = setInterval(check, 15000);
    return () => clearInterval(id);
  }, []);

  const timeAgo = lastUpdated
    ? `${Math.round((Date.now() - lastUpdated) / 1000)}s ago`
    : "—";

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
      <div style={{ display: "flex", alignItems: "center", fontSize: 12 }}>
        {connected === null && (
          <>
            <span style={dot("#555")} />
            <span style={{ color: "#555" }}>connecting…</span>
          </>
        )}
        {connected === true && (
          <>
            <span style={dot("var(--success)")} />
            <span style={{ color: "var(--success)" }}>connected</span>
          </>
        )}
        {connected === false && (
          <>
            <span style={dot("var(--danger)")} />
            <span style={{ color: "var(--danger)" }}>disconnected</span>
          </>
        )}
      </div>
      {lastUpdated && (
        <span style={{ fontSize: 12, color: "#444" }}>updated {timeAgo}</span>
      )}
    </div>
  );
}