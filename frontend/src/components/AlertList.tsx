import RiskBadge from "./RiskBadge";
import TrustBadge from "./TrustBadge";
import type { RiskAlert } from "../types";

interface Props {
  alerts: RiskAlert[];
  onSelect: (alert: RiskAlert) => void;
  selected?: RiskAlert | null;
  maxRows?: number;
}

export default function AlertList({ alerts, onSelect, selected, maxRows }: Props) {
  const rows = maxRows ? alerts.slice(0, maxRows) : alerts;

  return (
    <div className="panel overflow-hidden">
      <div className="px-4 py-3 border-b border-[#D5DEDC] flex items-center justify-between">
        <h3 className="font-semibold text-sm text-[#12292B]">Ranked alerts</h3>
        <span className="text-xs text-[#4C6567]">{alerts.length} facility-drug pairs</span>
      </div>
      <div className="max-h-[520px] overflow-y-auto thin-scroll divide-y divide-[#EAF0EE]">
        {rows.map((a) => (
          <button
            key={`${a.facility_id}-${a.drug}`}
            onClick={() => onSelect(a)}
            className={`w-full text-left px-4 py-3 hover:bg-[#EAF0EE] transition-colors ${
              selected?.facility_id === a.facility_id && selected?.drug === a.drug ? "bg-[#EAF0EE]" : ""
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium text-sm text-[#12292B] truncate">{a.drug}</span>
              <RiskBadge level={a.risk_level} />
            </div>
            <div className="flex items-center justify-between mt-1">
              <span className="text-xs text-[#4C6567]">
                {a.facility_id} &middot; {a.district}, {a.state}
              </span>
              <TrustBadge score={a.trust_score} />
            </div>
            <div className="flex items-center gap-3 mt-1 text-xs text-[#4C6567]">
              <span>{a.current_days_of_cover.toFixed(0)} days of cover</span>
              {a.is_structural_decline && (
                <span className="text-[#C1443A] font-semibold">structural decline</span>
              )}
            </div>
          </button>
        ))}
        {rows.length === 0 && (
          <div className="px-4 py-6 text-sm text-[#4C6567] text-center">No alerts in this scope.</div>
        )}
      </div>
    </div>
  );
}
