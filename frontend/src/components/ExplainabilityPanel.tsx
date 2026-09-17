import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import { api } from "../api/client";
import RiskBadge from "./RiskBadge";
import TrustBadge from "./TrustBadge";
import ReconstructedBadge from "./ReconstructedBadge";
import type { ExplainResponse, RiskAlert } from "../types";

export default function ExplainabilityPanel({ alert }: { alert: RiskAlert | null }) {
  const [data, setData] = useState<ExplainResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!alert) return;
    setLoading(true);
    api
      .get<ExplainResponse>(`/alerts/${alert.facility_id}/${encodeURIComponent(alert.drug)}/explain`)
      .then((res) => setData(res.data))
      .finally(() => setLoading(false));
  }, [alert]);

  if (!alert) {
    return (
      <div className="panel p-8 text-center text-sm text-[#4C6567]">
        Select an alert to see its decomposition, confidence, and driving signals.
      </div>
    );
  }

  if (loading || !data) {
    return <div className="panel p-8 text-center text-sm text-[#4C6567]">Loading...</div>;
  }

  const chartData = data.dates.map((d, i) => ({
    date: d,
    days_of_cover: Math.min(data.days_of_cover[i], 120),
    trend: data.trend[i],
    seasonal: data.seasonal[i],
    residual: data.residual[i],
  })).filter((_, i) => i % 3 === 0); // thin for chart perf

  return (
    <div className="panel p-5 space-y-5">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-semibold text-[#12292B]">{data.drug}</h3>
          <p className="text-xs text-[#4C6567]">{alert.facility_id} &middot; {alert.district}, {alert.state}</p>
        </div>
        <div className="flex items-center gap-2">
          <RiskBadge level={alert.risk_level} />
          <TrustBadge score={alert.trust_score} />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 text-center">
        <Stat label="Days of cover" value={alert.current_days_of_cover.toFixed(0)} />
        <Stat label="Trend slope / day" value={data.trend_slope_per_day.toFixed(4)} />
        <Stat
          label="Decline type"
          value={data.is_structural_decline ? "Structural" : "Temporary"}
          highlight={data.is_structural_decline}
        />
      </div>

      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-[#4C6567] mb-1">Days of cover, over time</p>
        <div className="h-40">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#EAF0EE" />
              <XAxis dataKey="date" tick={false} />
              <YAxis width={30} tick={{ fontSize: 10 }} />
              <Tooltip labelFormatter={(v) => v} formatter={(v) => Number(v).toFixed(1)} />
              <ReferenceLine y={14} stroke="#C1443A" strokeDasharray="4 4" label={{ value: "14d", fontSize: 10 }} />
              <Line type="monotone" dataKey="days_of_cover" stroke="#0F6E66" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-[#4C6567] mb-1">
          STL decomposition — trend (structural signal)
        </p>
        <div className="h-32">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#EAF0EE" />
              <XAxis dataKey="date" tick={false} />
              <YAxis width={30} tick={{ fontSize: 10 }} />
              <Tooltip formatter={(v) => Number(v).toFixed(1)} />
              <Line type="monotone" dataKey="trend" stroke="#A9691C" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-[#4C6567] mb-1">Seasonal</p>
          <div className="h-20">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <Line type="monotone" dataKey="seasonal" stroke="#4C6567" dot={false} strokeWidth={1.5} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-[#4C6567] mb-1">Residual (noise)</p>
          <div className="h-20">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <Line type="monotone" dataKey="residual" stroke="#9FB8B6" dot={false} strokeWidth={1.5} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <ReconstructedBadge text={data.reconstructed_notice} />
    </div>
  );
}

function Stat({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="bg-[#EAF0EE] rounded-lg py-2.5">
      <div className={`stat-value text-sm ${highlight ? "text-[#C1443A]" : "text-[#12292B]"}`}>{value}</div>
      <div className="text-[10px] font-semibold uppercase tracking-wider text-[#4C6567] mt-0.5">{label}</div>
    </div>
  );
}
