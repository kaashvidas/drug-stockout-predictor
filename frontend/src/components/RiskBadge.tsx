const COLORS: Record<string, string> = {
  low: "bg-risk-low",
  medium: "bg-risk-medium",
  high: "bg-risk-high",
  critical: "bg-risk-critical",
};

export default function RiskBadge({ level }: { level: string }) {
  return (
    <span
      className={`inline-block font-mono text-[10px] font-semibold uppercase tracking-wider text-white px-2 py-0.5 rounded-full ${COLORS[level] ?? "bg-gray-400"}`}
    >
      {level}
    </span>
  );
}
