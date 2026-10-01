import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { activeProfileId, api, type Profile, type SchemeMatch } from "../api";
import { ErrorNote, SchemeChip, StatusChip } from "../components/ui";

export function Schemes() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [matches, setMatches] = useState<SchemeMatch[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const id = activeProfileId();
    api.profile(id).then(setProfile).catch(() => {});
    api.schemes(id).then((r) => setMatches(r.matches)).catch((e) => setError(e.message));
  }, []);

  return (
    <div className="mx-auto max-w-4xl px-4 py-12 sm:px-6">
      <h1 className="display text-3xl sm:text-4xl">Government schemes for your business</h1>
      <p className="mt-3 max-w-[65ch] text-ink-soft">
        Central schemes for micro, small and medium enterprises, checked against{" "}
        <span className="font-semibold text-ink">{profile?.name ?? "your profile"}</span>. The same rule engine that reads tenders
        decides each match. <Link to="/profile" className="font-semibold text-stamp underline">Edit profile</Link>
      </p>
      {error && <div className="mt-6"><ErrorNote message={error} /></div>}
      {!matches && !error && <p className="pulse mt-8 text-ink-soft">Matching schemes…</p>}
      <ul className="mt-8 space-y-4">
        {matches?.map((m) => (
          <li key={m.id} className="rounded-xl border border-rule bg-sheet p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">{m.name}</h2>
                {m.ministry && <p className="text-sm text-ink-soft">{m.ministry}</p>}
              </div>
              <SchemeChip verdict={m.verdict} />
            </div>
            <p className="mt-2">{m.benefit}</p>
            <details className="mt-3">
              <summary className="cursor-pointer font-semibold text-stamp">Why</summary>
              <ul className="mt-2 space-y-2">
                {m.results.map((r) => (
                  <li key={r.criterion.id} className="grid gap-1 sm:grid-cols-[auto_1fr] sm:gap-3">
                    <StatusChip status={r.status} />
                    <span>
                      {r.criterion.description}
                      <span className="block text-sm text-ink-soft">{r.reason}</span>
                    </span>
                  </li>
                ))}
              </ul>
            </details>
            {m.source_url && (
              <a href={m.source_url} target="_blank" rel="noreferrer" className="mt-3 inline-block text-sm font-semibold text-stamp underline">
                Official scheme page
              </a>
            )}
          </li>
        ))}
        {matches?.length === 0 && <li className="text-ink-soft">No schemes are loaded yet.</li>}
      </ul>
    </div>
  );
}
