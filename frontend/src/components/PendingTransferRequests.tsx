import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { TransferRequestRow } from "../types";

export default function PendingTransferRequests() {
  const [requests, setRequests] = useState<TransferRequestRow[]>([]);

  function load() {
    api.get<TransferRequestRow[]>("/redistribution/requests", { params: { status: "pending" } }).then((res) => setRequests(res.data));
  }

  useEffect(() => {
    load();
  }, []);

  async function resolve(id: number, action: "approve" | "dismiss", donorFacilityId?: string) {
    await api.post(`/redistribution/requests/${id}/resolve`, { action, donor_facility_id: donorFacilityId });
    load();
  }

  return (
    <div className="panel p-5">
      <h3 className="font-semibold text-sm text-[#12292B] mb-1">Facility supply requests</h3>
      <p className="text-xs text-[#4C6567] mb-3">
        Bottom-up requests from facilities reporting critical stock, waiting on your approval.
      </p>
      <div className="space-y-2 max-h-72 overflow-y-auto thin-scroll">
        {requests.map((r) => (
          <div key={r.id} className="border border-[#EAF0EE] rounded-lg px-3 py-2">
            <div className="flex items-center justify-between">
              <div className="text-sm font-medium text-[#12292B]">
                {r.requesting_facility_name ?? r.requesting_facility_id} — {r.drug}
              </div>
            </div>
            <div className="text-xs text-[#4C6567] mb-2">
              {r.requesting_district}
              {r.suggested_donor_facility_id && ` · suggested donor: ${r.suggested_donor_facility_id}`}
              {r.note && ` · "${r.note}"`}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => resolve(r.id, "approve", r.suggested_donor_facility_id)}
                className="text-xs font-semibold bg-[#0F6E66] text-white rounded-full px-3 py-1"
              >
                Approve
              </button>
              <button
                onClick={() => resolve(r.id, "dismiss")}
                className="text-xs font-semibold border border-[#D5DEDC] text-[#4C6567] rounded-full px-3 py-1"
              >
                Dismiss
              </button>
            </div>
          </div>
        ))}
        {requests.length === 0 && <p className="text-sm text-[#4C6567]">No pending requests.</p>}
      </div>
    </div>
  );
}
