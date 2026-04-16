import {
  LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";

const PALETTE = [
  "#00aaff", "#cc88ff", "#51cf66",
  "#ffd43b", "#ff6b6b", "#20c997",
  "#f06595", "#74c0fc",
];

function buildSeries(metrics) {
  const byDay = {};
  for (const { day, developer, commits } of metrics) {
    if (!byDay[day]) byDay[day] = { day };
    byDay[day][developer] = (byDay[day][developer] || 0) + commits;
  }
  return Object.values(byDay).sort((a, b) => a.day.localeCompare(b.day));
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div
      style={{
        background: "#222",
        border: "1px solid #333",
        borderRadius: 8,
        padding: "10px 14px",
        fontSize: 12,
      }}
    >
      <p style={{ color: "#888", marginBottom: 6 }}>{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} style={{ color: p.stroke, marginBottom: 2 }}>
          {p.dataKey}: <strong>{p.value}</strong>
        </p>
      ))}
    </div>
  );
};

export default function CommitChart({ metrics }) {
  const data       = buildSeries(metrics);
  const developers = [...new Set(metrics.map((m) => m.developer))];

  if (metrics.length === 0) {
    return (
      <div
        style={{
          background: "var(--surface)",
          borderRadius: 10,
          padding: 20,
          marginBottom: 20,
          textAlign: "center",
          color: "var(--muted)",
          fontSize: 13,
          height: 200,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        No commit data yet — send a webhook event to see activity
      </div>
    );
  }

  return (
    <div
      style={{
        background: "var(--surface)",
        borderRadius: 10,
        padding: "18px 16px",
        marginBottom: 20,
        border: "1px solid var(--border)",
      }}
    >
      <p style={{ color: "var(--muted)", fontSize: 11, marginBottom: 14 }}>
        Commit activity — last 7 days
      </p>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#222" vertical={false} />
          <XAxis
            dataKey="day"
            tick={{ fill: "#555", fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: "#2a2a2a" }}
            tickFormatter={(v) => v.slice(5)}
          />
          <YAxis
            tick={{ fill: "#555", fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            allowDecimals={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ fontSize: 12, color: "#666", paddingTop: 12 }}
            iconType="plainline"
          />
          {developers.map((dev, i) => (
            <Line
              key={dev}
              type="monotone"
              dataKey={dev}
              stroke={PALETTE[i % PALETTE.length]}
              strokeWidth={2}
              dot={{ r: 3, fill: PALETTE[i % PALETTE.length], strokeWidth: 0 }}
              activeDot={{ r: 5, strokeWidth: 0 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}