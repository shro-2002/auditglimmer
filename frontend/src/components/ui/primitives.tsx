import type { ButtonHTMLAttributes, ReactNode } from "react";

import { ApiError } from "@/lib/api";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

const BUTTON_BASE =
  "inline-flex min-h-10 items-center justify-center gap-2 rounded-md px-3.5 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50";

const BUTTON_VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-accent text-accent-ink hover:bg-accent-strong active:bg-accent",
  secondary: "border border-line-strong bg-surface-3 text-ink hover:border-accent/60 hover:bg-surface-2",
  ghost: "text-ink-muted hover:bg-surface-3 hover:text-ink",
  danger: "border border-danger/50 bg-danger/10 text-st-mismatched hover:bg-danger/20",
};

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant };

export function Button({ variant = "secondary", className = "", type = "button", ...rest }: ButtonProps) {
  return <button type={type} className={`${BUTTON_BASE} ${BUTTON_VARIANTS[variant]} ${className}`} {...rest} />;
}

/** Same look as Button, for anchors (downloads, links). */
export function buttonClass(variant: ButtonVariant = "secondary"): string {
  return `${BUTTON_BASE} ${BUTTON_VARIANTS[variant]}`;
}

type CardProps = {
  title?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
  testId?: string;
};

export function Card({ title, actions, children, className = "", bodyClassName = "p-4", testId }: CardProps) {
  return (
    <section
      data-testid={testId}
      className={`rounded-lg border border-line bg-surface shadow-[0_1px_0_0_rgb(255_255_255/0.03)_inset,0_8px_24px_-12px_rgb(0_0_0/0.6)] ${className}`}
    >
      {(title || actions) && (
        <header className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-3">
          {title && <h2 className="text-sm font-semibold tracking-wide text-ink">{title}</h2>}
          {actions}
        </header>
      )}
      <div className={bodyClassName}>{children}</div>
    </section>
  );
}

export function Skeleton({ className = "h-4 w-full" }: { className?: string }) {
  return <div aria-hidden="true" className={`animate-pulse rounded bg-surface-3 ${className}`} />;
}

export function SkeletonRows({ rows = 4, label = "Loading" }: { rows?: number; label?: string }) {
  return (
    <div role="status" aria-label={label} className="space-y-2">
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} className="h-8 w-full" />
      ))}
      <span className="sr-only">{label}…</span>
    </div>
  );
}

export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error) return err.message;
  return "Unexpected error.";
}

type ErrorStateProps = { error: unknown; onRetry?: () => void; title?: string };

export function ErrorState({ error, onRetry, title = "Could not load data" }: ErrorStateProps) {
  const apiErr = error instanceof ApiError ? error : null;
  return (
    <div role="alert" className="rounded-md border border-danger/40 bg-danger/10 p-4 text-sm">
      <p className="font-semibold text-st-mismatched">{title}</p>
      <p className="mt-1 text-ink">{errorMessage(error)}</p>
      {apiErr && (
        <p className="mt-1 font-mono text-xs text-ink-muted">
          {apiErr.code}
          {apiErr.status ? ` · HTTP ${apiErr.status}` : ""}
          {apiErr.correlationId ? ` · correlation ${apiErr.correlationId}` : ""}
        </p>
      )}
      {onRetry && (
        <Button className="mt-3" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-md border border-dashed border-line-strong bg-surface-2/50 px-4 py-8 text-center">
      <p className="text-sm font-medium text-ink">{title}</p>
      {children && <div className="mx-auto mt-1 max-w-prose text-sm text-ink-muted">{children}</div>}
    </div>
  );
}

export function Field({ label, value, mono = false }: { label: string; value: ReactNode; mono?: boolean }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs uppercase tracking-wider text-ink-faint">{label}</dt>
      <dd className={`mt-0.5 break-words text-sm text-ink ${mono ? "font-mono" : ""}`}>{value ?? "—"}</dd>
    </div>
  );
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="rounded-lg border border-line bg-surface-2 p-4">
      <p className="text-xs uppercase tracking-wider text-ink-faint">{label}</p>
      <p className="tabular mt-1 text-2xl font-semibold text-ink">{value}</p>
      {hint && <p className="mt-1 text-xs text-ink-muted">{hint}</p>}
    </div>
  );
}

export const TABLE = "w-full min-w-[640px] border-collapse text-left text-sm";
export const TH = "border-b border-line bg-surface-2 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-ink-faint";
export const TD = "border-b border-line/70 px-3 py-2 align-top";

export function TableWrap({ children, label }: { children: ReactNode; label: string }) {
  return (
    <div className="overflow-x-auto rounded-md border border-line" role="region" aria-label={label} tabIndex={0}>
      {children}
    </div>
  );
}
