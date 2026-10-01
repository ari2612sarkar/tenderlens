import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, dateTime, inr, type Analysis, type Report as ReportT, type Risk, type SchemeMatch } from "../api";
import { Cite, CopyButton, ErrorNote, SchemeChip, Stamp, StatusChip } from "../components/ui";

const PIPELINE = [
  { key: "extract", label: "Reading the tender page by page" },
  { key: "eligibility", label: "Eligibility agent listing requirements and exemptions" },
  { key: "risks", label: "Risk agent reviewing contract clauses" },
  { key: "verify", label: "Checking every quote against its page" },
  { key: "evaluate", label: "Applying the rules to your company profile" },
  { key: "summarize", label: "Writing the summary" },
];

export function Report() {
  const { id = "" } = useParams();
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let timer: number | undefined;
    let cancelled = false;
    const load = () =>
      api.analysis(id).then((a) => {
        if (cancelled) return;
        setAnalysis(a);
        if (a.status === "RUNNING") timer = window.setTimeout(load, 3000);
      }).catch((e) => !cancelled && setError(e.message));
    load();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [id]);

  if (error) return <Page><ErrorNote message={error} /></Page>;
  if (!analysis) return <Page><p className="pulse text-ink-soft">Opening the report…</p></Page>;
  if (analysis.status === "FAILED")
    return (
      <Page>
        <h1 className="display text-3xl">The analysis didn't finish</h1>
        <div className="mt-4"><ErrorNote message={analysis.error ?? "Something went wrong."} /></div>
        <Link to="/analyze" className="mt-6 inline-block font-semibold text-stamp underline">Try another tender</Link>
      </Page>
    );
  if (analysis.status === "RUNNING" || !analysis.report) return <Progress analysis={analysis} />;
  return <ReportView report={analysis.report} pdfUrl={analysis.pdf_url} />;
}

function Page({ children }: { children: React.ReactNode }) {
  return <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6">{children}</div>;
}

function Progress({ analysis }: { analysis: Analysis }) {
  const done = new Set(analysis.steps_done ?? []);
  return (
    <Page>
      <h1 className="display text-3xl sm:text-4xl">Analysing the tender</h1>
      <p className="mt-3 max-w-[60ch] text-ink-soft">
        This usually takes two to four minutes. You can leave this page; the report will be waiting at this link.
      </p>
      <ol className="mt-8 max-w-xl space-y-3">
        {PIPELINE.map((s, i) => {
          const later = PIPELINE.slice(i + 1).some((n) => done.has(n.key));
          const state = later || (done.has(s.key) && analysis.step !== s.key) ? "done" : done.has(s.key) ? "active" : "waiting";
          return (
            <li key={s.key} className="flex items-center gap-3">
              <span
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 text-sm font-bold ${
                  state === "done" ? "border-met bg-met text-white" : state === "active" ? "pulse border-stamp text-stamp" : "border-rule text-ink-soft"
                }`}
                aria-hidden
              >
                {state === "done" ? "✓" : i + 1}
              </span>
              <span className={state === "waiting" ? "text-ink-soft" : "font-medium"}>{s.label}</span>
            </li>
          );
        })}
      </ol>
      <p className="mt-8 text-sm text-ink-soft">Running on AWS Step Functions, with Claude on Amazon Bedrock for the two extraction agents.</p>
    </Page>
  );
}

function ReportView({ report, pdfUrl }: { report: ReportT; pdfUrl?: string }) {
  const f = report.key_facts;
  const mandatory = report.results.filter((r) => r.criterion.mandatory);
  const optional = report.results.filter((r) => !r.criterion.mandatory);
  const risks = [...report.risks].sort((a, b) => sev(a) - sev(b));

  return (
    <Page>
      <p className="text-sm text-ink-soft">
        {[f.tender_no, f.organisation].filter(Boolean).join(", ")}
      </p>
      <div className="mt-2 grid gap-6 lg:grid-cols-[1fr_auto] lg:items-start">
        <div>
          <h1 className="display text-3xl sm:text-4xl">{f.title ?? "Tender report"}</h1>
          <p className="mt-2 text-ink-soft">Checked for {report.profile.name}</p>
        </div>
        <div className="lg:pr-6 lg:pt-2"><Stamp verdict={report.verdict} animate /></div>
      </div>

      <section className="mt-8 grid gap-8 lg:grid-cols-[1.4fr_1fr]">
        <div>
          <h2 className="text-xl font-semibold">{report.summary.headline}</h2>
          <p className="mt-2 max-w-[68ch]">{report.summary.summary}</p>
          <h3 className="mt-5 font-semibold">What to do next</h3>
          <ol className="mt-2 list-decimal space-y-1.5 pl-5">
            {report.summary.next_steps.map((s) => <li key={s}>{s}</li>)}
          </ol>
        </div>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-4 self-start rounded-xl border border-rule bg-sheet p-5 text-[0.95rem]">
          <Fact label="Bid closes" value={dateTime(f.bid_end)} />
          <Fact label="Bid security (EMD)" value={f.emd_inr ? `${inr(f.emd_inr)}${report.emd_exempt ? ", exempt for you" : ""}` : report.emd_exempt ? "Exempt for you" : "Not stated"} />
          <Fact label="Estimated value" value={inr(f.est_value_inr)} />
          <Fact label="Performance security" value={f.pbg_pct != null ? `${f.pbg_pct}%` : "Not stated"} />
          <Fact label="Contract period" value={f.contract_period ?? "Not stated"} />
          <Fact label="Quotes verified" value={`${report.grounding.grounded} of ${report.grounding.checked}`} />
        </dl>
      </section>

      <section className="mt-12">
        <h2 className="display text-2xl">Eligibility, requirement by requirement</h2>
        <p className="mt-1 text-ink-soft">Open a page tag to read the tender's exact words.</p>
        <CriteriaTable rows={mandatory} pdfUrl={pdfUrl} />
        {optional.length > 0 && (
          <>
            <h3 className="mt-8 font-semibold">Optional or preferential</h3>
            <CriteriaTable rows={optional} pdfUrl={pdfUrl} />
          </>
        )}
      </section>

      {risks.length > 0 && (
        <section className="mt-12">
          <h2 className="display text-2xl">Clauses to think about before bidding</h2>
          <ul className="mt-4 divide-y divide-rule border-y border-rule">
            {risks.map((r) => <RiskRow key={`${r.title}-${r.page}`} risk={r} pdfUrl={pdfUrl} />)}
          </ul>
        </section>
      )}

      <div className="mt-12 grid gap-10 lg:grid-cols-2">
        {report.documents_required.length > 0 && (
          <section>
            <h2 className="display text-2xl">Documents to prepare</h2>
            <ul className="mt-4 space-y-2.5">
              {report.documents_required.map((d) => (
                <li key={d.name} className="flex gap-3">
                  <input type="checkbox" className="mt-1.5 h-4 w-4 accent-[var(--color-met)]" aria-label={`Prepared: ${d.name}`} />
                  <div className="flex-1">
                    <p className="font-medium">{d.name}</p>
                    {d.reason && <p className="text-sm text-ink-soft">{d.reason}</p>}
                  </div>
                  <Cite item={d} pdfUrl={pdfUrl} />
                </li>
              ))}
            </ul>
          </section>
        )}
        <Schemes profileId={report.profile.id} />
      </div>

      <p className="mt-12 border-t border-rule pt-4 text-sm text-ink-soft">
        Analysed {dateTime(report.analyzed_at)}. {report.stats.pages} pages read
        {report.stats.ocr_pages ? `, ${report.stats.ocr_pages} with OCR` : ""}
        {report.stats.seconds ? ` in ${Math.round(report.stats.seconds / 6) / 10} minutes` : ""}
        {report.stats.model ? ` using ${report.stats.model.replace("anthropic.", "")} on Amazon Bedrock` : ""}.
      </p>
    </Page>
  );
}

function sev(r: Risk) {
  return { high: 0, medium: 1, low: 2 }[r.severity];
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-sm text-ink-soft">{label}</dt>
      <dd className="font-semibold">{value}</dd>
    </div>
  );
}

function CriteriaTable({ rows, pdfUrl }: { rows: ReportT["results"]; pdfUrl?: string }) {
  return (
    <div className="mt-4 overflow-hidden rounded-xl border border-rule bg-sheet">
      <table className="w-full border-collapse text-left">
        <thead className="hidden bg-paper text-sm text-ink-soft md:table-header-group">
          <tr>
            <th className="px-4 py-2.5 font-medium">Requirement</th>
            <th className="px-4 py-2.5 font-medium">Status</th>
            <th className="px-4 py-2.5 font-medium">Why</th>
            <th className="px-4 py-2.5 font-medium">Source</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-rule">
          {rows.map((r) => (
            <tr key={r.criterion.id} className="grid gap-2 px-4 py-4 md:table-row md:p-0">
              <td className="font-medium md:w-[32%] md:px-4 md:py-4 md:align-top">{r.criterion.description}</td>
              <td className="md:px-4 md:py-4 md:align-top"><StatusChip status={r.status} /></td>
              <td className="text-ink-soft md:px-4 md:py-4 md:align-top">
                {r.reason}
                {r.matched_projects.length > 0 && (
                  <span className="mt-1 block text-sm">Counted: {r.matched_projects.join("; ")}</span>
                )}
              </td>
              <td className="md:w-[30%] md:px-4 md:py-4 md:align-top"><Cite item={r.criterion} pdfUrl={pdfUrl} /></td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr><td className="px-4 py-4 text-ink-soft">No requirements of this kind were found in the tender.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

const SEVERITY = {
  high: { label: "High risk", cls: "text-fail" },
  medium: { label: "Medium risk", cls: "text-review" },
  low: { label: "Low risk", cls: "text-ink-soft" },
};

function RiskRow({ risk, pdfUrl }: { risk: Risk; pdfUrl?: string }) {
  const s = SEVERITY[risk.severity];
  return (
    <li className="grid gap-3 py-5 md:grid-cols-[1fr_1fr]">
      <div>
        <p className={`text-sm font-semibold ${s.cls}`}>{s.label}</p>
        <h3 className="mt-0.5 text-lg font-semibold">{risk.title}</h3>
        <p className="mt-1 text-ink-soft">{risk.explanation}</p>
        <div className="mt-2"><Cite item={risk} pdfUrl={pdfUrl} /></div>
      </div>
      {risk.suggested_prebid_query && (
        <div className="self-start rounded-lg border border-rule bg-paper p-4">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm font-semibold">Pre-bid query you could send</p>
            <CopyButton text={risk.suggested_prebid_query} label="Copy query" />
          </div>
          <p className="mt-2">{risk.suggested_prebid_query}</p>
        </div>
      )}
    </li>
  );
}

function Schemes({ profileId }: { profileId: string }) {
  const [matches, setMatches] = useState<SchemeMatch[] | null>(null);
  useEffect(() => {
    if (profileId) api.schemes(profileId).then((r) => setMatches(r.matches)).catch(() => setMatches([]));
  }, [profileId]);
  const relevant = (matches ?? []).filter((m) => m.verdict !== "NOT_ELIGIBLE").slice(0, 5);
  if (matches && relevant.length === 0) return null;
  return (
    <section>
      <h2 className="display text-2xl">Government schemes you may qualify for</h2>
      {!matches && <p className="pulse mt-4 text-ink-soft">Matching schemes…</p>}
      <ul className="mt-4 space-y-3">
        {relevant.map((m) => (
          <li key={m.id} className="rounded-lg border border-rule bg-sheet p-4">
            <div className="flex items-start justify-between gap-3">
              <p className="font-semibold">{m.name}</p>
              <SchemeChip verdict={m.verdict} />
            </div>
            <p className="mt-1 text-sm text-ink-soft">{m.benefit}</p>
          </li>
        ))}
      </ul>
      {relevant.length > 0 && <Link to="/schemes" className="mt-3 inline-block font-semibold text-stamp underline">See all schemes and why</Link>}
    </section>
  );
}
