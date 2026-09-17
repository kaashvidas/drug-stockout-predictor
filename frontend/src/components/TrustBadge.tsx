export default function TrustBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = score >= 0.8 ? "#2E8B57" : score >= 0.5 ? "#B4741B" : "#C1443A";
  return (
    <span
      className="inline-flex items-center gap-1 text-[11px] font-mono px-1.5 py-0.5 rounded border"
      style={{ borderColor: color, color }}
      title="Reporting-trust score: down-weights confidence for facilities with spotty reporting history"
    >
      trust {pct}%
    </span>
  );
}
