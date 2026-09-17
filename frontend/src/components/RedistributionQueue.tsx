import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import type { RedistributionCandidate, RiskAlert } from "../types";

export default function RedistributionQueue({ alert }: { alert: RiskAlert | null }) {
  const { auth } = useAuth();
  const [candidates, setCandidates] = useState<RedistributionCandidate[]>([]);
  const [loading, setLoading] = useState(false);
  const [actedIds, setActedIds] = useState<Set<string>>(new Set());
  const canApprove = auth && ["district", "state", "national"].includes(auth.role);
  const isFacility = auth?.role === "facility";

  useEffect(() => {
    if (!alert) {
      setCandidates([]);
      return;
    }
    setLoading(true);
    api
      .get<RedistributionCandidate[]>("/redistribution/recommendations", {
        params: { facility_id: alert.facility_id, drug: alert.drug },
      })
      .then((res) => setCandidates(res.data))
      .catch(() => setCandidates([]))
      .finally(() => setLoading(false));
  }, [alert]);

  async function approve(c: RedistributionCandidate) {
    await api.post("/redistribution/approve", {
      donor_facility_id: c.donor_facility_id,
      recipient_facility_id: c.recipient_facility_id,
      drug: c.drug,
      score: c.score,
      travel_time_min: c.travel_time_min,
    });
    setActedIds((prev) => new Set(prev).add(c.donor_facility_id));
  }

  async function requestFrom(c: RedistributionCandidate) {
    await api.post("/redistribution/requests", {
      requesting_facility_id: c.recipient_facility_id,
      drug: c.drug,
      suggested_donor_facility_id: c.donor_facility_id,
    });
    setActedIds((prev) => new Set(prev).add(c.donor_facility_id));
  }

  if (!alert) return null;

  return (
    <div className="bg-white border border-[#D5DEDC] rounded-xl shadow-sm p-5">
      <h3 className="font-semibold text-sm text-[#12292B] mb-1">Redistribution recommendations</h3>
      <p className="text-xs text-[#4C6567] mb-3">
        Ranked by urgency, real travel time (derated for real heavy rain), and donor shortfall risk. Recommend-only — a person approves every transfer.
      </p>
      {loading && <p className="text-sm text-[#4C6567]">Loading candidates...</p>}
      {!loading && candidates.length === 0 && (
        <p className="text-sm text-[#4C6567]">No feasible donor facilities with surplus stock of {alert.drug} found.</p>
      )}
      <div className="space-y-2">
        {candidates.map((c) => (
          <div
            key={c.donor_facility_id}
            className="flex items-center justify-between border border-[#EAF0EE] rounded-lg px-3 py-2"
          >
            <div>
              <div className="text-sm font-medium text-[#12292B] flex items-center gap-2">
                {c.donor_facility_name ?? c.donor_facility_id}
                {c.weather_flag && (
                  <span
                    className="text-[10px] font-bold uppercase text-[#B4741B] border border-[#B4741B] rounded-full px-1.5"
                    title={`Route derated for real heavy rain: ${c.travel_time_min.toFixed(0)}min -> ${c.effective_travel_time_min.toFixed(0)}min effective`}
                  >
                    weather risk
                  </span>
                )}
              </div>
              <div className="text-xs text-[#4C6567]">
                {c.donor_district} &middot; {c.travel_time_min.toFixed(0)} min away &middot; surplus{" "}
                {c.donor_surplus_days_of_cover.toFixed(0)}d cover &middot; score {c.score.toFixed(2)}
              </div>
            </div>
            {actedIds.has(c.donor_facility_id) ? (
              <span className="text-xs font-semibold text-[#2E8B57]">
                {canApprove ? "Approved" : "Requested"}
              </span>
            ) : canApprove ? (
              <button
                onClick={() => approve(c)}
                className="text-xs font-semibold bg-[#0F6E66] text-white rounded-full px-3 py-1"
              >
                Approve transfer
              </button>
            ) : isFacility ? (
              <button
                onClick={() => requestFrom(c)}
                className="text-xs font-semibold bg-[#C1443A] text-white rounded-full px-3 py-1"
              >
                Request supply
              </button>
            ) : (
              <span className="text-xs text-[#4C6567]">View only</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
