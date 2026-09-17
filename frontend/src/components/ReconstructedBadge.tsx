/**
 * Per the build guide's own honesty policy (Section 04) and the project's
 * DATA_SOURCES.md: any chart built from the generated Tier-3 stock layer
 * must say so on the chart itself, not just in a docs file.
 */
export default function ReconstructedBadge({ text }: { text?: string }) {
  return (
    <div className="flex items-start gap-2 text-xs text-[#4C6567] bg-[#EAF0EE] border-l-2 border-[#A9691C] rounded-r-md px-3 py-2 mt-2">
      <span className="text-[#A9691C] font-bold">i</span>
      <span>
        {text ??
          "Reconstructed — interpolated between verified checkpoints (CAG audit percentages; real Sarguja/Pilibhit case-study dates). Not a live feed. See docs/DATA_SOURCES.md."}
      </span>
    </div>
  );
}
