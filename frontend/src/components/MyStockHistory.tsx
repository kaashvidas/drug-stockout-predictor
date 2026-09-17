import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { api } from "../api/client";

interface ReportRow {
  id: number;
  drug: string;
  reported_stock: number;
  status: string;
  reported_by: string;
  created_at: string;
}

const STATUS_COLOR: Record<string, string> = {
  normal: "#0F6E66",
  surplus: "#2E8B57",
  critical: "#C1443A",
};

export default function MyStockHistory({ facilityId }: { facilityId: string }) {
  const [reports, setReports] = useState<ReportRow[]>([]);

  function load() {
    api.get<ReportRow[]>(`/reports/${facilityId}`).then((res) => setReports(res.data));
  }

  useEffect(() => {
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [facilityId]);

  const drugs = Array.from(new Set(reports.map((r) => r.drug)));

  const chartData = [...reports]
    .reverse()
    .map((r) => ({ ...r, ts: new Date(r.created_at).toLocaleDateString() }));

  return (
    <div className="bg-white border border-[#D5DEDC] rounded-xl shadow-sm p-5">
      <h3 className="font-semibold text-sm text-[#12292B] mb-1">Your reported stock history</h3>
      <p className="text-xs text-[#4C6567] mb-3">
        Every report you've submitted from this facility, most recent first.
      </p>

      {reports.length === 0 ? (
        <p className="text-sm text-[#4C6567] py-4 text-center">
          No reports submitted yet — use the form to start your history.
        </p>
      ) : (
        <>
          <div className="h-40 mb-3">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#EAF0EE" />
                <XAxis dataKey="ts" tick={{ fontSize: 10 }} />
                <YAxis width={30} tick={{ fontSize: 10 }} />
                <Tooltip formatter={(v) => `${v} units`} />
                {drugs.map((d, i) => (
                  <Line
                    key={d}
                    type="monotone"
                    dataKey={(r: ReportRow) => (r.drug === d ? r.reported_stock : null)}
                    name={d}
                    stroke={["#0F6E66", "#A9691C", "#C1443A", "#4C6567"][i % 4]}
                    connectNulls
                    dot={{ r: 3 }}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="max-h-48 overflow-y-auto divide-y divide-[#EAF0EE]">
            {reports.map((r) => (
              <div key={r.id} className="flex items-center justify-between py-1.5 text-xs">
                <span className="text-[#12292B]">{r.drug}</span>
                <span className="text-[#4C6567]">{r.reported_stock} units</span>
                <span className="font-semibold" style={{ color: STATUS_COLOR[r.status] ?? "#4C6567" }}>
                  {r.status}
                </span>
                <span className="text-[#9FB8B6]">{new Date(r.created_at).toLocaleDateString()}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
