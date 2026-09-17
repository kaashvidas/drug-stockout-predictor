import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import Header from "../components/Header";
import AlertList from "../components/AlertList";
import ExplainabilityPanel from "../components/ExplainabilityPanel";
import CascadePanel from "../components/CascadePanel";
import RedistributionQueue from "../components/RedistributionQueue";
import RiskHeatmap from "../components/RiskHeatmap";
import StockReportForm from "../components/StockReportForm";
import AuditLogPanel from "../components/AuditLogPanel";
import type { HeatmapRow, RiskAlert } from "../types";

export default function Dashboard() {
  const { auth } = useAuth();
  const [alerts, setAlerts] = useState<RiskAlert[]>([]);
  const [heatmap, setHeatmap] = useState<HeatmapRow[]>([]);
  const [selected, setSelected] = useState<RiskAlert | null>(null);

  useEffect(() => {
    api.get<RiskAlert[]>("/alerts").then((res) => {
      setAlerts(res.data);
      if (res.data.length > 0) setSelected(res.data[0]);
    });
    api.get<HeatmapRow[]>("/alerts/heatmap").then((res) => setHeatmap(res.data));
  }, []);

  if (!auth) return null;

  const isFacilityRole = auth.role === "facility";
  const isSystemicRole = auth.role === "state" || auth.role === "national" || auth.role === "program";
  const canApprove = auth.role === "district" || auth.role === "state" || auth.role === "national";

  const criticalCount = alerts.filter((a) => a.risk_level === "critical").length;
  const highCount = alerts.filter((a) => a.risk_level === "high").length;
  const structuralCount = alerts.filter((a) => a.is_structural_decline).length;

  return (
    <div className="min-h-screen bg-[#F3F6F5]">
      <Header />
      <main className="max-w-7xl mx-auto px-6 py-6 space-y-6">
        <div className="grid grid-cols-4 gap-4">
          <SummaryStat label="Facility-drug pairs" value={alerts.length} />
          <SummaryStat label="Critical" value={criticalCount} tone="critical" />
          <SummaryStat label="High" value={highCount} tone="high" />
          <SummaryStat label="Structural decline" value={structuralCount} tone="high" />
        </div>

        {!isFacilityRole && heatmap.length > 0 && <RiskHeatmap rows={heatmap} />}

        <div className={`grid gap-6 ${isFacilityRole ? "grid-cols-1" : "grid-cols-3"}`}>
          <div className={isFacilityRole ? "" : "col-span-1"}>
            <AlertList alerts={alerts} onSelect={setSelected} selected={selected} maxRows={isFacilityRole ? 10 : undefined} />
            {isFacilityRole && auth.scope && (
              <div className="mt-6">
                <StockReportForm facilityId={auth.scope} />
              </div>
            )}
          </div>

          <div className={isFacilityRole ? "" : "col-span-1"}>
            <ExplainabilityPanel alert={selected} />
          </div>

          <div className={`space-y-6 ${isFacilityRole ? "" : "col-span-1"}`}>
            <CascadePanel alert={selected} />
            <RedistributionQueue alert={selected} />
            {(isSystemicRole || canApprove) && <AuditLogPanel />}
          </div>
        </div>
      </main>
    </div>
  );
}

function SummaryStat({ label, value, tone }: { label: string; value: number; tone?: "critical" | "high" }) {
  const color = tone === "critical" ? "text-[#8E2A2A]" : tone === "high" ? "text-[#C1443A]" : "text-[#12292B]";
  return (
    <div className="bg-white border border-[#D5DEDC] rounded-xl shadow-sm px-5 py-4">
      <div className={`text-2xl font-semibold ${color}`}>{value}</div>
      <div className="text-xs uppercase tracking-wide text-[#4C6567] mt-1">{label}</div>
    </div>
  );
}
