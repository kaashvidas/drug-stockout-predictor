import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { CascadeResponse, RiskAlert } from "../types";

export default function CascadePanel({ alert }: { alert: RiskAlert | null }) {
  const [data, setData] = useState<CascadeResponse | null>(null);

  useEffect(() => {
    if (!alert) {
      setData(null);
      return;
    }
    api.get<CascadeResponse>(`/cascade/${alert.facility_id}`).then((res) => setData(res.data));
  }, [alert]);

  if (!alert || !data) return null;

  return (
    <div className="bg-white border border-[#D5DEDC] rounded-xl shadow-sm p-5">
      <h3 className="font-semibold text-sm text-[#12292B] mb-1">Spillover cascade</h3>
      <p className="text-xs text-[#4C6567] mb-3">
        Stress propagates to nearby facilities sharing this catchment, weighted by real road travel time.
      </p>
      <div className="grid grid-cols-2 gap-3 mb-3">
        <div className="bg-[#EAF0EE] rounded-lg py-2 text-center">
          <div className="text-sm font-bold text-[#12292B]">{(data.own_stress * 100).toFixed(0)}%</div>
          <div className="text-[10px] uppercase tracking-wide text-[#4C6567]">Own stress</div>
        </div>
        <div className="bg-[#EAF0EE] rounded-lg py-2 text-center">
          <div className="text-sm font-bold text-[#C1443A]">{(data.propagated_stress * 100).toFixed(0)}%</div>
          <div className="text-[10px] uppercase tracking-wide text-[#4C6567]">After propagation</div>
        </div>
      </div>
      <p className="text-xs font-semibold uppercase tracking-wide text-[#4C6567] mb-1">Nearest catchment neighbors</p>
      <div className="space-y-1">
        {data.neighbor_propagation_paths.map((p) => (
          <div key={p.to} className="flex items-center justify-between text-xs">
            <span className="text-[#12292B]">{p.facility_name ?? p.to}</span>
            <span className="text-[#4C6567]">{p.travel_time_min.toFixed(0)} min &middot; weight {p.weight.toFixed(2)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
