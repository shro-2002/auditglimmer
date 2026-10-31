import type { AssetStatus, Decision, Mode } from "@/lib/types";

const CHIP = "inline-flex items-center gap-1.5 rounded px-2 py-0.5 text-xs font-semibold tracking-wide border whitespace-nowrap";

export const ASSET_STATUSES: AssetStatus[] = ["VERIFIED", "HUMAN_CONFIRMED", "PROBABLE", "MISMATCHED", "UNVERIFIED", "NOT_OBSERVABLE"];

/** Hex tones shared with charts so a status reads the same everywhere. */
export const STATUS_HEX: Record<AssetStatus, string> = {
  VERIFIED: "#5eead4",
  HUMAN_CONFIRMED: "#f0abfc",
  PROBABLE: "#fcd34d",
  MISMATCHED: "#fca5a5",
  UNVERIFIED: "#cbd5e1",
  NOT_OBSERVABLE: "#c4b5fd",
};

const STATUS_CLASS: Record<AssetStatus, string> = {
  VERIFIED: "text-st-verified border-st-verified/40 bg-st-verified/10",
  // Outline ring: a human assertion must never read as a machine identifier match.
  HUMAN_CONFIRMED: "text-st-human border-st-human/60 bg-st-human/10 outline outline-1 outline-offset-1 outline-st-human/50",
  PROBABLE: "text-st-probable border-st-probable/40 bg-st-probable/10",
  MISMATCHED: "text-st-mismatched border-st-mismatched/40 bg-st-mismatched/10",
  UNVERIFIED: "text-st-unverified border-st-unverified/30 bg-st-unverified/5 border-dashed",
  NOT_OBSERVABLE: "text-st-notobs border-st-notobs/40 bg-st-notobs/10",
};

const STATUS_GLYPH: Record<AssetStatus, string> = {
  VERIFIED: "✓",
  HUMAN_CONFIRMED: "✎",
  PROBABLE: "≈",
  MISMATCHED: "≠",
  UNVERIFIED: "?",
  NOT_OBSERVABLE: "∅",
};

export const STATUS_LABEL: Record<AssetStatus, string> = {
  VERIFIED: "Verified",
  HUMAN_CONFIRMED: "Human-confirmed",
  PROBABLE: "Probable",
  MISMATCHED: "Mismatched",
  UNVERIFIED: "Unverified",
  NOT_OBSERVABLE: "Not observable",
};

/** Machine statuses show their code; HUMAN_CONFIRMED shows a plain-language label so it cannot be skimmed as VERIFIED. */
export function StatusChip({ status }: { status: AssetStatus }) {
  return (
    <span className={`${CHIP} ${STATUS_CLASS[status]}`} title={STATUS_LABEL[status]}>
      <span aria-hidden="true">{STATUS_GLYPH[status]}</span>
      {status === "HUMAN_CONFIRMED" ? STATUS_LABEL[status] : status}
    </span>
  );
}

const DECISION_CLASS: Record<Decision, string> = {
  VERIFIED: "text-st-verified border-st-verified/40 bg-st-verified/10",
  PROBABLE: "text-st-probable border-st-probable/40 bg-st-probable/10",
  WEAK: "text-st-weak border-st-weak/40 bg-st-weak/10",
  MISMATCHED: "text-st-mismatched border-st-mismatched/40 bg-st-mismatched/10",
  NOT_IN_REGISTER: "text-st-notreg border-st-notreg/40 bg-st-notreg/10",
  EVIDENCE_UNUSABLE: "text-st-unusable border-st-unusable/40 bg-st-unusable/10",
};

export function DecisionChip({ decision }: { decision: Decision }) {
  return <span className={`${CHIP} ${DECISION_CLASS[decision]}`}>{decision}</span>;
}

/** Contract invariant 5: any mode:"demo" object renders a visible DEMO badge. */
export function ModeTag({ mode }: { mode: Mode }) {
  const cls = mode === "demo" ? "text-demo border-demo/50 bg-demo/10" : "text-accent border-accent/50 bg-accent/10";
  return <span className={`${CHIP} ${cls}`}>{mode === "demo" ? "DEMO" : "LIVE"}</span>;
}

/** Flags that need a reviewer's attention, with a plain-language explanation. */
export const FLAG_EXPLANATION: Record<string, string> = {
  CONFLICTING_REVIEWS:
    "Different reviewers recorded different outcomes for this decision. The report stays DRAFT until the disagreement is resolved.",
  COMPETING_FOR_ASSET:
    "Two or more distinct detected objects point to the same single ledger asset. At most one of them can be that asset.",
};

export function FlagTag({ flag }: { flag: string }) {
  const explanation = FLAG_EXPLANATION[flag];
  const tone = explanation ? "border-st-weak/60 bg-st-weak/10 text-st-weak" : "border-line-strong bg-surface-3 text-ink-muted";
  return (
    <span className={`${CHIP} ${tone} font-mono font-normal`} title={explanation}>
      {explanation && <span aria-hidden="true">⚠</span>}
      {flag}
    </span>
  );
}

/** Flag chips plus a written explanation for each attention flag (screen readers get the text, not just a tooltip). */
export function FlagList({ flags }: { flags: string[] }) {
  if (flags.length === 0) return null;
  const explained = flags.filter((f) => FLAG_EXPLANATION[f]);
  return (
    <div className="space-y-1.5">
      <div className="flex flex-wrap gap-1.5" aria-label="Flags">
        {flags.map((f) => (
          <FlagTag key={f} flag={f} />
        ))}
      </div>
      {explained.map((f) => (
        <p key={f} role="note" data-testid={`flag-note-${f}`} className="rounded border-l-2 border-st-weak bg-st-weak/5 px-2 py-1 text-xs text-ink">
          <span className="font-semibold text-st-weak">{f === "CONFLICTING_REVIEWS" ? "Conflicting reviews: " : "Competing for one asset: "}</span>
          {FLAG_EXPLANATION[f]}
        </p>
      ))}
    </div>
  );
}

export const HUMAN_CONFIRMED_NOTE =
  "Human-confirmed = asserted by a named reviewer with a written note — reported separately from machine identifier matches (VERIFIED).";

export const UNVERIFIED_NOTE = "UNVERIFIED = not adequately observed — not evidence the asset is missing.";
