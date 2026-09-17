import { useEffect, useMemo, useState } from "react";
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
import SearchBar from "../components/SearchBar";
import RankedBarChart from "../components/RankedBarChart";
import AvailabilityExplorer from "../components/AvailabilityExplorer";
import PendingTransferRequests from "../components/PendingTransferRequests";
import MyStockHistory from "../components/MyStockHistory";
import type { DrugRanking, FacilityRanking, HeatmapRow, RiskAlert } from "../types";

export default function Dashboard() {
  const { auth } = useAuth();
  const [alerts, setAlerts] = useState<RiskAlert[]>([]);
  const [heatmap, setHeatmap] = useState<HeatmapRow[]>([]);
  const [drugRankings, setDrugRankings] = useState<DrugRanking[]>([]);
  const [facilityRankings, setFacilityRankings] = useState<FacilityRanking[]>([]);
  const [selected, setSelected] = useState<RiskAlert | null>(null);
  const [search, setSearch] = useState("");

  useEffect(() => {
    api.get<RiskAlert[]>("/alerts").then((res) => {
      setAlerts(res.data);
      if (res.data.length > 0) setSelected(res.data[0]);
    });
    api.get<HeatmapRow[]>("/alerts/heatmap").then((res) => setHeatmap(res.data));
    api.get<DrugRanking[]>("/alerts/rankings/by-drug").then((res) => setDrugRankings(res.data));
    api.get<FacilityRanking[]>("/alerts/rankings/by-facility").then((res) => setFacilityRankings(res.data));
  }, []);

  const filteredAlerts = useMemo(() => {
    if (!search.trim()) return alerts;
    const q = search.trim().toLowerCase();
    return alerts.filter(
      (a) =>
        a.drug.toLowerCase().includes(q) ||
        a.facility_id.toLowerCase().includes(q) ||
        (a.facility_name ?? "").toLowerCase().includes(q) ||
        a.district.toLowerCase().includes(q) ||
        a.state.toLowerCase().includes(q)
    );
  }, [alerts, search]);

  if (!auth) return null;

  const isFacilityRole = auth.role === "facility";
  const isSystemicRole = auth.role === "state" || auth.role === "national" || auth.role === "program";
  const canApprove = auth.role === "district" || auth.role === "state" || auth.role === "national";

  const criticalCount = alerts.filter((a) => a.risk_level === "critical").length;
  const highCount = alerts.filter((a) => a.risk_level === "high").length;
  const structuralCount = alerts.filter((a) => a.is_structural_decline).length;

  function selectByFacility(facilityId: string) {
    const candidate = alerts.filter((a) => a.facility_id === facilityId).sort((a, b) => b.risk_probability - a.risk_probability)[0];
    if (candidate) setSelected(candidate);
  }

  function selectByDrug(drug: string) {
    const candidate = alerts.filter((a) => a.drug === drug).sort((a, b) => b.risk_probability - a.risk_probability)[0];
    if (candidate) setSelected(candidate);
  }

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

        {isSystemicRole && (drugRankings.length > 0 || facilityRankings.length > 0) && (
          <div className="grid grid-cols-2 gap-6">
            <RankedBarChart
              title="Most at-risk drugs"
              subtitle="Average risk across every facility in scope — where the next stockout is most likely to hit."
              rows={drugRankings.map((d) => ({ label: d.drug, avg_risk: d.avg_risk, n_critical: d.n_critical }))}
              onSelect={selectByDrug}
            />
            <RankedBarChart
              title="Most at-risk facilities"
              subtitle="Worst single-drug risk per facility — the shortlist to act on first."
              rows={facilityRankings.map((f) => ({
                label: f.facility_name || f.facility_id,
                avg_risk: f.max_risk,
                n_critical: f.n_critical,
              }))}
              onSelect={(label) => {
                const match = facilityRankings.find((f) => (f.facility_name || f.facility_id) === label);
                if (match) selectByFacility(match.facility_id);
              }}
            />
          </div>
        )}

        {canApprove && <AvailabilityExplorer alerts={alerts} />}

        <SearchBar value={search} onChange={setSearch} />

        <div className={`grid gap-6 ${isFacilityRole ? "grid-cols-1" : "grid-cols-3"}`}>
          <div className={isFacilityRole ? "" : "col-span-1"}>
            <AlertList alerts={filteredAlerts} onSelect={setSelected} selected={selected} maxRows={isFacilityRole ? 10 : undefined} />
            {isFacilityRole && auth.scope && (
              <div className="mt-6 space-y-6">
                <StockReportForm facilityId={auth.scope} />
                <MyStockHistory facilityId={auth.scope} />
              </div>
            )}
          </div>

          <div className={isFacilityRole ? "" : "col-span-1"}>
            <ExplainabilityPanel alert={selected} />
          </div>

          <div className={`space-y-6 ${isFacilityRole ? "" : "col-span-1"}`}>
            <CascadePanel alert={selected} />
            <RedistributionQueue alert={selected} />
            {canApprove && <PendingTransferRequests />}
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
