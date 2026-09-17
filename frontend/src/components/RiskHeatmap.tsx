import { MapContainer, TileLayer, CircleMarker, Tooltip as LeafletTooltip } from "react-leaflet";
import type { HeatmapRow } from "../types";

function riskColor(avgRisk: number): string {
  if (avgRisk >= 0.75) return "#8E2A2A";
  if (avgRisk >= 0.5) return "#C1443A";
  if (avgRisk >= 0.25) return "#B4741B";
  return "#2E8B57";
}

export default function RiskHeatmap({ rows }: { rows: HeatmapRow[] }) {
  const center: [number, number] =
    rows.length > 0 ? [rows.reduce((s, r) => s + r.lat, 0) / rows.length, rows.reduce((s, r) => s + r.lon, 0) / rows.length] : [15.3, 76.0];

  return (
    <div className="panel overflow-hidden h-[420px]">
      <MapContainer center={center} zoom={7} style={{ height: "100%", width: "100%" }} scrollWheelZoom={false}>
        <TileLayer
          attribution='&copy; OpenStreetMap contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {rows.map((r) => (
          <CircleMarker
            key={`${r.district}-${r.state}`}
            center={[r.lat, r.lon]}
            radius={10 + r.max_risk * 18}
            pathOptions={{ color: riskColor(r.avg_risk), fillColor: riskColor(r.avg_risk), fillOpacity: 0.6 }}
          >
            <LeafletTooltip>
              <div className="text-xs">
                <strong>{r.district}, {r.state}</strong>
                <br />
                Avg risk: {(r.avg_risk * 100).toFixed(0)}%
                <br />
                {r.n_critical} critical &middot; {r.n_high} high
              </div>
            </LeafletTooltip>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
