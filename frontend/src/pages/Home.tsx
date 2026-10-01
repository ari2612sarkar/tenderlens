import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Analysis, type Profile, type Sample } from "../api";
import { Stamp } from "../components/ui";

const STEPS = [
  { title: "Read every page", body: "Text is pulled from the PDF page by page. Scanned pages go through Amazon Textract." },
  { title: "Two agents extract, in parallel", body: "One lists every eligibility rule and exemption. The other looks for risky clauses. Each item comes with an exact quote and page number." },
  { title: "Check each quote against its page", body: "Code looks for every quote on the page it cites. If a quote isn't there, the item is marked unverified and can't decide your verdict." },
  { title: "Apply the rules to your company", body: "Plain code, not the AI, compares turnover, experience, certificates and MSE exemptions against your profile." },
  { title: "Write up the decision", body: "You get a verdict, a reason for every requirement, pre-bid queries for risky clauses and a list of documents to prepare." },
];

export function Home() {
  const [samples, setSamples] = useState<Sample[]>([]);
  const [profiles, setProfiles] = useState<Record<string, Profile>>({});
  const [analyses, setAnalyses] = useState<Record<string, Analysis>>({});

  useEffect(() => {
    api.samples().then(({ samples, profiles }) => {
      setSamples(samples);
      setProfiles(Object.fromEntries(profiles.map((p) => [p.id, p])));
      samples.forEach((s) =>
        api.analysis(s.analysis_id).then((a) => setAnalyses((prev) => ({ ...prev, [s.id]: a }))).catch(() => {}),
      );
    }).catch(() => {});
  }, []);

  return (
    <>
      <section className="mx-auto grid max-w-6xl gap-10 px-4 pb-14 pt-12 sm:px-6 lg:grid-cols-[1.15fr_1fr] lg:pt-20">
        <div>
          <h1 className="display text-4xl sm:text-5xl lg:text-[3.6rem]">Know if you can bid before you read 40 pages of tender.</h1>
          <p className="mt-5 max-w-[60ch] text-lg text-ink-soft">
            Upload a GeM or CPPP tender. TenderLens checks every eligibility rule against your company profile and shows the exact
            line, on the exact page, behind each answer.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/analyze" className="rounded-lg bg-stamp px-5 py-3 font-semibold text-white hover:bg-stamp-deep">
              Analyze a tender
            </Link>
            {samples[0] && (
              <Link to={`/report/${samples[0].analysis_id}`} className="rounded-lg border border-ink/20 bg-sheet px-5 py-3 font-semibold hover:border-stamp">
                Open a sample report
              </Link>
            )}
          </div>
        </div>

        <figure aria-label="Specimen report" className="relative self-start rounded-xl border border-rule bg-sheet p-5 shadow-[0_1px_0_#d9ded6,0_12px_30px_-18px_rgba(24,33,46,0.35)]">
          <p className="text-sm text-ink-soft">GEM/2026/B/7801296, Indian Air Force</p>
          <p className="mt-1 font-semibold">Customised software for scanning and digitisation of documents</p>
          <dl className="mt-4 divide-y divide-rule border-y border-rule text-[0.95rem]">
            {[
              ["Average turnover, last 3 years", "Exempt for MSEs", "text-exempt"],
              ["3 years of similar experience", "Exempt for MSEs", "text-exempt"],
              ["OEM authorisation certificate", "Check", "text-review"],
            ].map(([req, status, cls]) => (
              <div key={req} className="flex items-baseline justify-between gap-4 py-2.5">
                <dt>{req}</dt>
                <dd className={`font-semibold ${cls}`}>{status}</dd>
              </div>
            ))}
          </dl>
          <blockquote className="quote mt-4 border-l-[3px] border-stamp pl-3 text-ink-soft">
            “MSE Relaxation for Years Of Experience and Turnover: Yes”
            <span className="mt-1 block font-sans text-sm font-semibold text-stamp">p. 1</span>
          </blockquote>
          <div className="pointer-events-none absolute -right-2 -top-6 sm:-right-6">
            <Stamp verdict="CHECK_ITEMS" animate />
          </div>
        </figure>
      </section>

      <section className="border-y border-rule bg-sheet">
        <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
          <h2 className="display text-2xl sm:text-3xl">Real tenders, already analysed</h2>
          <p className="mt-2 max-w-[65ch] text-ink-soft">
            These are live bids from the Government e-Marketplace, each checked against a demo company. Open one to see every rule,
            its source and the verdict.
          </p>
          <ul className="mt-6 divide-y divide-rule border-y border-rule">
            {samples.map((s) => {
              const a = analyses[s.id];
              return (
                <li key={s.id}>
                  <Link to={`/report/${s.analysis_id}`} className="group grid gap-3 py-5 sm:grid-cols-[1fr_auto] sm:items-center">
                    <div>
                      <p className="text-sm text-ink-soft">
                        {s.bid_number}, {s.organisation}
                      </p>
                      <p className="mt-0.5 text-lg font-semibold group-hover:text-stamp">{s.title}</p>
                      <p className="mt-1 text-sm text-ink-soft">
                        {s.sector}. Closes {new Date(s.closes).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}. Checked
                        for {profiles[s.profile_id]?.name ?? "a demo company"}.
                      </p>
                    </div>
                    <div className="min-h-12 sm:pr-4">
                      {a?.verdict ? <Stamp verdict={a.verdict} size="sm" /> : <span className="text-sm text-ink-soft">Report pending</span>}
                    </div>
                  </Link>
                </li>
              );
            })}
            {samples.length === 0 && <li className="py-5 text-ink-soft">Loading sample tenders…</li>}
          </ul>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
        <h2 className="display text-2xl sm:text-3xl">The AI reads the tender. Rules decide the verdict.</h2>
        <p className="mt-3 max-w-[65ch] text-ink-soft">
          A language model is good at finding requirements in a long PDF and bad at guaranteeing it didn't invent one. So TenderLens
          splits the job: Claude on Amazon Bedrock extracts, code verifies and decides.
        </p>
        <ol className="mt-8 grid gap-x-10 gap-y-7 md:grid-cols-2">
          {STEPS.map((s, i) => (
            <li key={s.title} className="grid grid-cols-[2.25rem_1fr] gap-3">
              <span className="display flex h-9 w-9 items-center justify-center rounded-full border-2 border-stamp text-stamp" aria-hidden>
                {i + 1}
              </span>
              <div>
                <h3 className="font-semibold">{s.title}</h3>
                <p className="mt-1 text-ink-soft">{s.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>
    </>
  );
}
