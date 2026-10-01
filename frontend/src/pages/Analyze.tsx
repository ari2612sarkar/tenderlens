import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { activeProfileId, api, setActiveProfileId, type Profile, type Sample } from "../api";
import { ErrorNote } from "../components/ui";

const MAX_BYTES = 25 * 1024 * 1024;

export function Analyze() {
  const navigate = useNavigate();
  const fileInput = useRef<HTMLInputElement>(null);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [profileId, setProfileId] = useState(activeProfileId());
  const [file, setFile] = useState<File | null>(null);
  const [sampleId, setSampleId] = useState("");
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.samples().then(async ({ samples, profiles }) => {
      setSamples(samples);
      const mine = activeProfileId();
      const list = [...profiles];
      if (!mine.startsWith("demo-")) {
        const own = await api.profile(mine).catch(() => null);
        if (own) list.unshift(own);
      }
      setProfiles(list);
    }).catch((e) => setError(e.message));
  }, []);

  function pick(f: File | undefined) {
    setError("");
    if (!f) return;
    if (f.type !== "application/pdf" && !f.name.toLowerCase().endsWith(".pdf")) return setError("Choose a PDF file.");
    if (f.size > MAX_BYTES) return setError("This PDF is larger than 25 MB. Upload the main bid document only.");
    setFile(f);
    setSampleId("");
  }

  async function start() {
    setError("");
    try {
      setActiveProfileId(profileId);
      let body: { profile_id: string; tender_key?: string; sample_id?: string } = { profile_id: profileId };
      if (file) {
        setBusy("Uploading the tender…");
        body = { ...body, tender_key: await api.uploadPdf(file) };
      } else if (sampleId) {
        body = { ...body, sample_id: sampleId };
      } else {
        return setError("Choose a tender PDF or one of the sample tenders.");
      }
      setBusy("Starting the analysis…");
      const { id } = await api.startAnalysis(body);
      navigate(`/report/${id}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy("");
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="display text-3xl sm:text-4xl">Analyze a tender</h1>
      <p className="mt-3 text-ink-soft">
        It takes two to four minutes. You'll see each step as it happens, and the report stays available at its own link.
      </p>

      <section className="mt-10">
        <h2 className="text-lg font-semibold">1. The tender</h2>
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            pick(e.dataTransfer.files[0]);
          }}
          className={`mt-3 rounded-xl border-2 border-dashed px-6 py-8 text-center ${
            dragging ? "border-stamp bg-stamp-soft" : "border-rule bg-sheet"
          }`}
        >
          {file ? (
            <p>
              <span className="font-semibold">{file.name}</span>{" "}
              <span className="text-ink-soft">({(file.size / 1e6).toFixed(1)} MB)</span>
            </p>
          ) : (
            <p className="text-ink-soft">Drop the bid document PDF here (up to 25 MB)</p>
          )}
          <button
            type="button"
            onClick={() => fileInput.current?.click()}
            className="mt-3 rounded-lg border border-ink/20 bg-paper px-4 py-2 font-semibold hover:border-stamp"
          >
            {file ? "Choose a different PDF" : "Choose PDF"}
          </button>
          <input ref={fileInput} type="file" accept="application/pdf,.pdf" className="sr-only" onChange={(e) => pick(e.target.files?.[0])} />
        </div>

        <label className="mt-4 block">
          <span className="text-ink-soft">No tender at hand? Use a live GeM bid instead:</span>
          <select
            value={sampleId}
            onChange={(e) => {
              setSampleId(e.target.value);
              if (e.target.value) setFile(null);
            }}
            className="mt-1.5 block w-full rounded-lg border border-rule bg-sheet px-3 py-2.5"
          >
            <option value="">Select a sample tender</option>
            {samples.map((s) => (
              <option key={s.id} value={s.id}>
                {s.bid_number}: {s.title}
              </option>
            ))}
          </select>
        </label>
      </section>

      <section className="mt-10">
        <h2 className="text-lg font-semibold">2. Your company</h2>
        <div className="mt-3 grid gap-2">
          {profiles.map((p) => (
            <label
              key={p.id}
              className={`flex cursor-pointer items-start gap-3 rounded-lg border px-4 py-3 ${
                profileId === p.id ? "border-stamp bg-stamp-soft" : "border-rule bg-sheet"
              }`}
            >
              <input type="radio" name="profile" className="mt-1 accent-[var(--color-stamp)]" checked={profileId === p.id} onChange={() => setProfileId(p.id!)} />
              <span>
                <span className="font-semibold">{p.name}</span>
                <span className="block text-sm text-ink-soft">
                  {p.enterprise_size} enterprise in {p.state || "India"}, {p.past_projects.length} past projects on file
                </span>
              </span>
            </label>
          ))}
        </div>
        <p className="mt-3 text-sm text-ink-soft">
          Want to check your own business? <Link to="/profile" className="font-semibold text-stamp underline">Fill in your company profile</Link>{" "}
          first. It takes about five minutes.
        </p>
      </section>

      <div className="mt-10 flex flex-wrap items-center gap-4">
        <button
          type="button"
          onClick={start}
          disabled={!!busy}
          className="rounded-lg bg-stamp px-6 py-3 font-semibold text-white hover:bg-stamp-deep disabled:opacity-60"
        >
          Analyze tender
        </button>
        {busy && <span className="pulse text-ink-soft">{busy}</span>}
      </div>
      {error && <div className="mt-4"><ErrorNote message={error} /></div>}
    </div>
  );
}
