import { useState } from "react";
import { api } from "../api/client";

const COMMON_DRUGS = [
  "Isoniazid", "Rifampicin", "Ethambutol", "Pyrazinamide", "Amoxicillin", "Ciprofloxacin",
  "Paracetamol", "Ibuprofen", "Oral rehydration salts", "Ringer lactate", "Metformin",
  "Amlodipine", "Oxytocin", "Snake Venom Antiserum", "Insulin (Soluble)",
  "Deferoxamine", "Deferasirox", "Deferiprone", "Hydroxyurea",
];

export default function StockReportForm({ facilityId }: { facilityId: string }) {
  const [drug, setDrug] = useState(COMMON_DRUGS[0]);
  const [stock, setStock] = useState("");
  const [status, setStatus] = useState<"idle" | "queued" | "sent" | "error">("idle");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const value = parseFloat(stock);
    if (Number.isNaN(value)) return;

    if (!navigator.onLine) {
      const queue = JSON.parse(localStorage.getItem("sc_offline_reports") ?? "[]");
      queue.push({ facility_id: facilityId, drug, reported_stock: value, queued_at: new Date().toISOString() });
      localStorage.setItem("sc_offline_reports", JSON.stringify(queue));
      setStatus("queued");
      setStock("");
      return;
    }

    try {
      await api.post("/reports", { facility_id: facilityId, drug, reported_stock: value });
      setStatus("sent");
      setStock("");
    } catch {
      setStatus("error");
    }
  }

  return (
    <div className="bg-white border border-[#D5DEDC] rounded-xl shadow-sm p-5">
      <h3 className="font-semibold text-sm text-[#12292B] mb-1">Report stock</h3>
      <p className="text-xs text-[#4C6567] mb-3">
        Low-connectivity friendly — if you're offline, this queues and syncs automatically once you're back online.
      </p>
      <form onSubmit={submit} className="space-y-2">
        <select
          className="w-full border border-[#D5DEDC] rounded-lg px-3 py-2 text-sm"
          value={drug}
          onChange={(e) => setDrug(e.target.value)}
        >
          {COMMON_DRUGS.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
        <input
          className="w-full border border-[#D5DEDC] rounded-lg px-3 py-2 text-sm"
          placeholder="Units in stock"
          type="number"
          value={stock}
          onChange={(e) => setStock(e.target.value)}
        />
        <button className="w-full bg-[#0F6E66] text-white rounded-lg py-2 text-sm font-semibold">
          Submit report
        </button>
      </form>
      {status === "sent" && <p className="text-xs text-[#2E8B57] mt-2">Submitted and synced.</p>}
      {status === "queued" && <p className="text-xs text-[#B4741B] mt-2">Offline — queued, will sync automatically.</p>}
      {status === "error" && <p className="text-xs text-[#C1443A] mt-2">Could not submit — try again.</p>}
    </div>
  );
}
