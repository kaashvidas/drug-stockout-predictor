import { useState } from "react";
import { api } from "../api/client";

const COMMON_DRUGS = [
  "Isoniazid", "Rifampicin", "Ethambutol", "Pyrazinamide", "Amoxicillin", "Ciprofloxacin",
  "Paracetamol", "Ibuprofen", "Oral rehydration salts", "Ringer lactate", "Metformin",
  "Amlodipine", "Oxytocin", "Snake Venom Antiserum", "Insulin (Soluble)",
  "Deferoxamine", "Deferasirox", "Deferiprone", "Hydroxyurea",
];

type Status = "normal" | "surplus" | "critical";

export default function StockReportForm({ facilityId }: { facilityId: string }) {
  const [drug, setDrug] = useState(COMMON_DRUGS[0]);
  const [stock, setStock] = useState("");
  const [status, setStatus] = useState<Status>("normal");
  const [note, setNote] = useState("");
  const [statusMsg, setStatusMsg] = useState<"idle" | "queued" | "sent" | "error" | "requested">("idle");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const value = parseFloat(stock);
    if (Number.isNaN(value)) return;

    if (!navigator.onLine) {
      const queue = JSON.parse(localStorage.getItem("sc_offline_reports") ?? "[]");
      queue.push({ facility_id: facilityId, drug, reported_stock: value, status, queued_at: new Date().toISOString() });
      localStorage.setItem("sc_offline_reports", JSON.stringify(queue));
      setStatusMsg("queued");
      setStock("");
      return;
    }

    try {
      await api.post("/reports", { facility_id: facilityId, drug, reported_stock: value, status });
      setStatusMsg("sent");
      setStock("");
    } catch {
      setStatusMsg("error");
    }
  }

  async function requestSupply() {
    try {
      await api.post("/redistribution/requests", {
        requesting_facility_id: facilityId,
        drug,
        note: note || undefined,
      });
      setStatusMsg("requested");
    } catch {
      setStatusMsg("error");
    }
  }

  return (
    <div className="panel p-5">
      <h3 className="font-semibold text-sm text-[#12292B] mb-1">Report stock</h3>
      <p className="text-xs text-[#4C6567] mb-3">
        Low-connectivity friendly — if you're offline, this queues and syncs automatically once you're back online.
      </p>
      <form onSubmit={submit} className="space-y-2">
        <select
          className="w-full border border-[#D5DEDC] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#0F6E66] focus:ring-2 focus:ring-[#0F6E66]/15 transition-shadow"
          value={drug}
          onChange={(e) => setDrug(e.target.value)}
        >
          {COMMON_DRUGS.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
        <input
          className="w-full border border-[#D5DEDC] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#0F6E66] focus:ring-2 focus:ring-[#0F6E66]/15 transition-shadow"
          placeholder="Units in stock"
          type="number"
          value={stock}
          onChange={(e) => setStock(e.target.value)}
        />
        <div className="flex gap-2">
          {(["normal", "surplus", "critical"] as Status[]).map((s) => (
            <button
              type="button"
              key={s}
              onClick={() => setStatus(s)}
              className={`flex-1 text-xs font-semibold rounded-lg py-2 border ${
                status === s
                  ? s === "critical"
                    ? "bg-[#C1443A] text-white border-[#C1443A]"
                    : s === "surplus"
                    ? "bg-[#2E8B57] text-white border-[#2E8B57]"
                    : "bg-[#0F6E66] text-white border-[#0F6E66]"
                  : "border-[#D5DEDC] text-[#4C6567]"
              }`}
            >
              {s === "normal" ? "Normal" : s === "surplus" ? "Surplus" : "Running critical"}
            </button>
          ))}
        </div>
        <button className="w-full bg-[#0F6E66] text-white rounded-lg py-2 text-sm font-semibold">
          Submit report
        </button>
      </form>

      {status === "critical" && (
        <div className="mt-3 pt-3 border-t border-[#EAF0EE]">
          <p className="text-xs text-[#4C6567] mb-2">
            Stock marked critical — ask nearby surplus facilities to supply you.
          </p>
          <input
            className="w-full border border-[#D5DEDC] rounded-lg px-3 py-2 text-sm mb-2"
            placeholder="Optional note (e.g. how many units needed)"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <button
            onClick={requestSupply}
            className="w-full bg-[#C1443A] text-white rounded-lg py-2 text-sm font-semibold"
          >
            Request supply from nearby facilities
          </button>
        </div>
      )}

      {statusMsg === "sent" && <p className="text-xs text-[#2E8B57] mt-2">Submitted and synced.</p>}
      {statusMsg === "queued" && <p className="text-xs text-[#B4741B] mt-2">Offline — queued, will sync automatically.</p>}
      {statusMsg === "requested" && <p className="text-xs text-[#2E8B57] mt-2">Supply request sent to your district/state procurement queue.</p>}
      {statusMsg === "error" && <p className="text-xs text-[#C1443A] mt-2">Could not submit — try again.</p>}
    </div>
  );
}
