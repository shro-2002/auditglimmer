import { ModeTag } from "@/components/ui/Badges";
import type { Mode } from "@/lib/types";

type Props = { callModes: Mode[]; serverMode: Mode | undefined };

/** Says which mode produced this session's evidence, which can differ from the server's current mode. */
export function EvidenceModeNote({ callModes, serverMode }: Props) {
  const modes = [...new Set(callModes)].sort();
  if (modes.length === 0) {
    return (
      <p data-testid="evidence-mode" data-modes="" className="text-sm text-ink-muted">
        No provider calls recorded for this session yet.
      </p>
    );
  }
  const differs = serverMode !== undefined && (modes.length > 1 || modes[0] !== serverMode);
  return (
    <p data-testid="evidence-mode" data-modes={modes.join(",")} className="flex flex-wrap items-center gap-2 text-sm">
      <span>Evidence produced in</span>
      {modes.map((m) => (
        <ModeTag key={m} mode={m} />
      ))}
      <span>mode</span>
      {differs && serverMode && <span className="text-ink-muted">— server currently {serverMode.toUpperCase()}</span>}
    </p>
  );
}
