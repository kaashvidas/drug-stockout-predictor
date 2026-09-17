import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";

function riskColor(avgRisk: number): string {
  if (avgRisk >= 0.75) return "#8E2A2A";
  if (avgRisk >= 0.5) return "#C1443A";
  if (avgRisk >= 0.25) return "#B4741B";
  return "#2E8B57";
}

interface Row {
  label: string;
  sublabel?: string;
  avg_risk: number;
  n_critical: number;
}

export default function RankedBarChart({
  title,
  subtitle,
  rows,
  maxRows = 12,
  onSelect,
}: {
  title: string;
  subtitle?: string;
  rows: Row[];
  maxRows?: number;
  onSelect?: (label: string) => void;
}) {
  const data = rows.slice(0, maxRows).map((r) => ({
    ...r,
    riskPct: Math.round(r.avg_risk * 100),
  }));

  return (
    <div className="bg-white border border-[#D5DEDC] rounded-xl shadow-sm p-5">
      <h3 className="font-semibold text-sm text-[#12292B]">{title}</h3>
      {subtitle && <p className="text-xs text-[#4C6567] mb-2">{subtitle}</p>}
      <div style={{ height: Math.max(220, data.length * 28) }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#EAF0EE" horizontal={false} />
            <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 10 }} unit="%" />
            <YAxis
              type="category"
              dataKey="label"
              width={140}
              tick={{ fontSize: 11 }}
              interval={0}
            />
            <Tooltip
              formatter={(v, name) => (name === "riskPct" ? [`${v}%`, "avg risk"] : v)}
              labelFormatter={(v) => v}
            />
            <Bar
              dataKey="riskPct"
              radius={[0, 4, 4, 0]}
              onClick={(d) => onSelect?.((d as unknown as Row).label)}
              cursor={onSelect ? "pointer" : "default"}
            >
              {data.map((row, i) => (
                <Cell key={i} fill={riskColor(row.avg_risk)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
