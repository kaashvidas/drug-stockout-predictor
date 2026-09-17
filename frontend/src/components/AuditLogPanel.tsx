import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { AuditLogRow } from "../types";

export default function AuditLogPanel() {
  const [rows, setRows] = useState<AuditLogRow[]>([]);

  useEffect(() => {
    api.get<AuditLogRow[]>("/redistribution/audit-log").then((res) => setRows(res.data)).catch(() => setRows([]));
  }, []);

  return (
    <div className="panel p-5">
      <h3 className="font-semibold text-sm text-[#12292B] mb-1">Audit trail</h3>
      <p className="text-xs text-[#4C6567] mb-3">
        Every alert-driven action logged once, visible (scoped) at every level above it.
      </p>
      <div className="space-y-2 max-h-72 overflow-y-auto thin-scroll">
        {rows.map((r) => (
          <div key={r.id} className="text-xs border-b border-[#EAF0EE] pb-2">
            <div className="text-[#12292B] font-medium">{r.action.replace(/_/g, " ")}</div>
            <div className="text-[#4C6567]">{r.detail}</div>
            <div className="text-[#9FB8B6]">{r.actor} ({r.role}) &middot; {new Date(r.created_at).toLocaleString()}</div>
          </div>
        ))}
        {rows.length === 0 && <p className="text-sm text-[#4C6567]">No actions logged yet.</p>}
      </div>
    </div>
  );
}
