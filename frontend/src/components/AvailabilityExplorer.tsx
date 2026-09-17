import { useEffect, useState } from "react";
import { api } from "../api/client";
import RiskBadge from "./RiskBadge";
import type { AvailabilityRow, RiskAlert } from "../types";

const COMMON_DRUGS = [
  "Isoniazid", "Rifampicin", "Ethambutol", "Pyrazinamide", "Amoxicillin", "Ciprofloxacin",
  "Paracetamol", "Ibuprofen", "Oral rehydration salts", "Ringer lactate", "Metformin",
  "Amlodipine", "Oxytocin", "Snake Venom Antiserum", "Insulin (Soluble)",
  "Deferoxamine", "Deferasirox", "Deferiprone", "Hydroxyurea",
];

export default function AvailabilityExplorer({ alerts }: { alerts: RiskAlert[] }) {
  const [drug, setDrug] = useState(COMMON_DRUGS[0]);
  const [nearFacilityId, setNearFacilityId] = useState("");
  const [rows, setRows] = useState<AvailabilityRow[]>([]);
  const [loading, setLoading] = useState(false);

  const facilityOptions = Array.from(
    new Map(alerts.map((a) => [a.facility_id, a.facility_name || a.facility_id])).entries()
  );

  useEffect(() => {
    setLoading(true);
    api
      .get<AvailabilityRow[]>(`/alerts/availability/${encodeURIComponent(drug)}`, {
        params: nearFacilityId ? { near_facility_id: nearFacilityId } : {},
      })
      .then((res) => setRows(res.data))
      .finally(() => setLoading(false));
  }, [drug, nearFacilityId]);

  return (
    <div className="bg-white border border-[#D5DEDC] rounded-xl shadow-sm p-5">
      <h3 className="font-semibold text-sm text-[#12292B] mb-1">Availability explorer</h3>
      <p className="text-xs text-[#4C6567] mb-3">
        Look up a drug's availability across every facility in scope, or ranked by real travel time from a chosen facility.
      </p>
      <div className="flex gap-2 mb-3">
        <select
          className="flex-1 border border-[#D5DEDC] rounded-lg px-3 py-2 text-sm"
          value={drug}
          onChange={(e) => setDrug(e.target.value)}
        >
          {COMMON_DRUGS.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
        <select
          className="flex-1 border border-[#D5DEDC] rounded-lg px-3 py-2 text-sm"
          value={nearFacilityId}
          onChange={(e) => setNearFacilityId(e.target.value)}
        >
          <option value="">All facilities in scope</option>
          {facilityOptions.map(([id, name]) => (
            <option key={id} value={id}>Near: {name}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <p className="text-sm text-[#4C6567]">Loading...</p>
      ) : (
        <div className="max-h-80 overflow-y-auto divide-y divide-[#EAF0EE]">
          {rows.map((r) => (
            <div key={r.facility_id} className="flex items-center justify-between py-2 text-sm">
              <div>
                <div className="font-medium text-[#12292B]">{r.facility_name}</div>
                <div className="text-xs text-[#4C6567]">
                  {r.district}
                  {r.travel_time_min != null && ` · ${r.travel_time_min.toFixed(0)} min away`}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-[#4C6567]">{r.current_days_of_cover.toFixed(0)}d cover</span>
                <RiskBadge level={r.risk_level} />
              </div>
            </div>
          ))}
          {rows.length === 0 && <p className="text-sm text-[#4C6567] py-4 text-center">No data for this selection.</p>}
        </div>
      )}
    </div>
  );
}
