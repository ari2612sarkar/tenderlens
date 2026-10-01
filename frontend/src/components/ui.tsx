import { useState } from "react";
import type { Cited, SchemeVerdict, Status, Verdict } from "../api";

const VERDICT_STAMP: Record<Verdict, { text: string; sub?: string; color: string }> = {
  ELIGIBLE: { text: "Eligible", sub: "to bid", color: "var(--color-met)" },
  ELIGIBLE_WITH_CAUTION: { text: "Eligible", sub: "bid with caution", color: "var(--color-stamp)" },
  CHECK_ITEMS: { text: "Check items", sub: "before bidding", color: "var(--color-review)" },
  NOT_ELIGIBLE: { text: "Not eligible", color: "var(--color-fail)" },
  CLOSED: { text: "Closed", sub: "bidding ended", color: "var(--color-missing)" },
};

export function Stamp({ verdict, size = "lg", animate = false }: { verdict: Verdict; size?: "sm" | "lg"; animate?: boolean }) {
  const s = VERDICT_STAMP[verdict];
  return (
    <span
      className={`stamp ${animate ? "stamp-in" : ""} ${size === "lg" ? "text-3xl sm:text-4xl" : "text-sm"}`}
      style={{ ["--stamp-color" as string]: s.color }}
      role="img"
      aria-label={`Verdict: ${s.text}${s.sub ? `, ${s.sub}` : ""}`}
    >
      <span>{s.text}</span>
      {s.sub && <small>{s.sub}</small>}
    </span>
  );
}

const STATUS: Record<Status, { label: string; cls: string; mark: string }> = {
  MET: { label: "Met", cls: "bg-met-soft text-met", mark: "✓" },
  NOT_MET: { label: "Not met", cls: "bg-fail-soft text-fail", mark: "✕" },
  EXEMPT: { label: "Exempt", cls: "bg-exempt-soft text-exempt", mark: "◇" },
  NEEDS_REVIEW: { label: "Check", cls: "bg-review-soft text-review", mark: "?" },
  MISSING_DATA: { label: "Add data", cls: "bg-missing-soft text-missing", mark: "…" },
};

export function StatusChip({ status }: { status: Status }) {
  const s = STATUS[status];
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-0.5 text-sm font-semibold ${s.cls}`}>
      <span aria-hidden>{s.mark}</span>
      {s.label}
    </span>
  );
}

const SCHEME: Record<SchemeVerdict, { label: string; cls: string }> = {
  ELIGIBLE: { label: "You qualify", cls: "bg-met-soft text-met" },
  POSSIBLY_ELIGIBLE: { label: "Possibly", cls: "bg-review-soft text-review" },
  NOT_ELIGIBLE: { label: "Not eligible", cls: "bg-missing-soft text-missing" },
};

export function SchemeChip({ verdict }: { verdict: SchemeVerdict }) {
  const s = SCHEME[verdict];
  return <span className={`whitespace-nowrap rounded-full px-2.5 py-0.5 text-sm font-semibold ${s.cls}`}>{s.label}</span>;
}

/** Page tag that reveals the verbatim quote; ungrounded quotes are visibly marked. */
export function Cite({ item, pdfUrl }: { item: Cited; pdfUrl?: string }) {
  const [open, setOpen] = useState(false);
  const verified = item.grounded !== false;
  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className={`rounded px-1.5 py-0.5 text-sm font-semibold underline-offset-2 hover:underline ${
          verified ? "bg-stamp-soft text-stamp" : "border border-dashed border-review text-review"
        }`}
      >
        p. {item.page}
        {!verified && " (unverified)"}
      </button>
      {open && (
        <figure className="mt-2 border-l-[3px] border-stamp pl-3">
          <blockquote className="quote text-ink">“{item.quote}”</blockquote>
          <figcaption className="mt-1 text-sm text-ink-soft">
            {verified ? "Found on this page of the tender." : "Not found on the cited page. Check the tender yourself."}{" "}
            {pdfUrl && (
              <a className="font-semibold text-stamp underline" href={`${pdfUrl}#page=${item.page}`} target="_blank" rel="noreferrer">
                Open page {item.page}
              </a>
            )}
          </figcaption>
        </figure>
      )}
    </div>
  );
}

export function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setDone(true);
          setTimeout(() => setDone(false), 1800);
        } catch {
          /* clipboard blocked; text is still selectable */
        }
      }}
      className="rounded-md border border-rule bg-sheet px-2.5 py-1 text-sm font-semibold text-ink hover:border-stamp hover:text-stamp"
    >
      {done ? "Copied" : label}
    </button>
  );
}

export function ErrorNote({ message }: { message: string }) {
  return (
    <p role="alert" className="rounded-md border border-fail/30 bg-fail-soft px-4 py-3 text-fail">
      {message}
    </p>
  );
}
