const PERCENT = 100;

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export function formatNumber(n: number | null | undefined, digits = 0): string {
  if (n === null || n === undefined) return "—";
  return n.toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

/** 0..1 → "73%". Callers must label what the number is (rule score vs model-reported). */
export function formatFraction(n: number | null | undefined): string {
  if (n === null || n === undefined) return "not reported";
  return `${Math.round(n * PERCENT)}%`;
}

export function formatUsd(n: number): string {
  return n.toLocaleString(undefined, { style: "currency", currency: "USD", minimumFractionDigits: 4 });
}

export function formatMoney(value: number | null, currency: string | null): string {
  if (value === null) return "—";
  if (!currency) return formatNumber(value, 2);
  try {
    return value.toLocaleString(undefined, { style: "currency", currency });
  } catch {
    return `${formatNumber(value, 2)} ${currency}`;
  }
}

export function shortId(id: string): string {
  return id.length > 10 ? id.slice(0, 8) : id;
}
