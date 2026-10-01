import { useEffect, useMemo, useState } from "react";
import { activeProfileId, api, inr, setActiveProfileId, type PastProject, type Profile as ProfileT } from "../api";
import { ErrorNote } from "../components/ui";

const STATES = [
  "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Delhi", "Goa", "Gujarat", "Haryana",
  "Himachal Pradesh", "Jammu and Kashmir", "Jharkhand", "Karnataka", "Kerala", "Ladakh", "Madhya Pradesh", "Maharashtra",
  "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Puducherry", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
  "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal", "Andaman and Nicobar Islands", "Chandigarh",
  "Dadra and Nagar Haveli and Daman and Diu", "Lakshadweep",
];
const REGISTRATIONS = ["GST", "PAN", "Udyam", "EPF", "ESIC", "Labour Licence"];

function lastFys(n: number): string[] {
  const now = new Date();
  const start = now.getMonth() >= 3 ? now.getFullYear() : now.getFullYear() - 1;
  return Array.from({ length: n }, (_, i) => `${start - 1 - i}-${String((start - i) % 100).padStart(2, "0")}`);
}

const EMPTY: ProfileT = {
  name: "", enterprise_size: "micro", dpiit_startup: false, state: "", incorporation_year: null, net_worth_inr: null,
  employee_count: null, turnover_by_fy: {}, certifications: [], registrations: ["GST", "PAN", "Udyam"], past_projects: [],
  oem_authorizations: [], sector_tags: [], women_owned: false, sc_st_owned: false,
};

const input = "mt-1 block w-full rounded-lg border border-rule bg-sheet px-3 py-2";

export function Profile() {
  const [profile, setProfile] = useState<ProfileT>(EMPTY);
  const [demos, setDemos] = useState<ProfileT[]>([]);
  const [tags, setTags] = useState<Record<string, string>>({});
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const fys = useMemo(() => lastFys(3), []);

  useEffect(() => {
    api.taxonomy().then((t) => setTags(t.work_tags)).catch(() => {});
    api.samples().then((s) => setDemos(s.profiles)).catch(() => {});
    const id = activeProfileId();
    if (!id.startsWith("demo-")) api.profile(id).then(setProfile).catch(() => {});
  }, []);

  const set = <K extends keyof ProfileT>(k: K, v: ProfileT[K]) => setProfile((p) => ({ ...p, [k]: v }));
  const num = (v: string) => (v.trim() === "" ? null : Number(v));
  const isDemo = !!profile.id?.startsWith("demo-");

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setStatus("");
    try {
      const saved = await api.saveProfile(profile);
      setProfile(saved);
      setActiveProfileId(saved.id!);
      setStatus("Profile saved. New analyses will use it.");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  function updateProject(i: number, patch: Partial<PastProject>) {
    set("past_projects", profile.past_projects.map((p, j) => (j === i ? { ...p, ...patch } : p)));
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="display text-3xl sm:text-4xl">Company profile</h1>
      <p className="mt-3 text-ink-soft">
        TenderLens compares each tender against these facts. Use the figures from your audited accounts and certificates.
        Nothing here is shared, and you can come back and edit it.
      </p>
      {demos.length > 0 && (
        <p className="mt-4 text-sm">
          <span className="text-ink-soft">Start from a demo company: </span>
          {demos.map((d) => (
            <button key={d.id} type="button" onClick={() => setProfile(d)} className="mr-3 font-semibold text-stamp underline">
              {d.name}
            </button>
          ))}
        </p>
      )}

      <form onSubmit={save} className="mt-8 space-y-10">
        <fieldset className="space-y-4">
          <legend className="text-lg font-semibold">About the business</legend>
          <label className="block">Registered name
            <input required className={input} value={profile.name} onChange={(e) => set("name", e.target.value)} />
          </label>
          <div className="grid gap-4 sm:grid-cols-3">
            <label className="block">Enterprise size (Udyam)
              <select className={input} value={profile.enterprise_size} onChange={(e) => set("enterprise_size", e.target.value as ProfileT["enterprise_size"])}>
                <option value="micro">Micro</option><option value="small">Small</option>
                <option value="medium">Medium</option><option value="large">Large</option>
              </select>
            </label>
            <label className="block">State
              <select className={input} value={profile.state} onChange={(e) => set("state", e.target.value)}>
                <option value="">Select</option>
                {STATES.map((s) => <option key={s}>{s}</option>)}
              </select>
            </label>
            <label className="block">Year established
              <input type="number" min={1900} max={2100} className={input} value={profile.incorporation_year ?? ""} onChange={(e) => set("incorporation_year", num(e.target.value))} />
            </label>
          </div>
          <div className="flex flex-wrap gap-x-6 gap-y-2">
            <label className="flex items-center gap-2"><input type="checkbox" checked={profile.dpiit_startup} onChange={(e) => set("dpiit_startup", e.target.checked)} /> DPIIT-recognised startup</label>
            <label className="flex items-center gap-2"><input type="checkbox" checked={profile.women_owned} onChange={(e) => set("women_owned", e.target.checked)} /> Women-owned</label>
            <label className="flex items-center gap-2"><input type="checkbox" checked={profile.sc_st_owned} onChange={(e) => set("sc_st_owned", e.target.checked)} /> SC/ST-owned</label>
          </div>
        </fieldset>

        <fieldset className="space-y-4">
          <legend className="text-lg font-semibold">Finances, in rupees</legend>
          <div className="grid gap-4 sm:grid-cols-3">
            {fys.map((fy) => (
              <label key={fy} className="block">Turnover FY {fy}
                <input type="number" min={0} className={input} value={profile.turnover_by_fy[fy] ?? ""}
                  onChange={(e) => {
                    const t = { ...profile.turnover_by_fy };
                    const v = num(e.target.value);
                    if (v == null) delete t[fy]; else t[fy] = v;
                    set("turnover_by_fy", t);
                  }} />
                <span className="text-sm text-ink-soft">{profile.turnover_by_fy[fy] != null ? inr(profile.turnover_by_fy[fy]) : " "}</span>
              </label>
            ))}
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">Net worth
              <input type="number" min={0} className={input} value={profile.net_worth_inr ?? ""} onChange={(e) => set("net_worth_inr", num(e.target.value))} />
              <span className="text-sm text-ink-soft">{profile.net_worth_inr != null ? inr(profile.net_worth_inr) : " "}</span>
            </label>
            <label className="block">Employees
              <input type="number" min={0} className={input} value={profile.employee_count ?? ""} onChange={(e) => set("employee_count", num(e.target.value))} />
            </label>
          </div>
        </fieldset>

        <fieldset className="space-y-4">
          <legend className="text-lg font-semibold">Registrations and certificates</legend>
          <div className="flex flex-wrap gap-x-5 gap-y-2">
            {REGISTRATIONS.map((r) => (
              <label key={r} className="flex items-center gap-2">
                <input type="checkbox" checked={profile.registrations.includes(r)}
                  onChange={(e) => set("registrations", e.target.checked ? [...profile.registrations, r] : profile.registrations.filter((x) => x !== r))} />
                {r}
              </label>
            ))}
          </div>
          <label className="block">Certifications, separated by commas
            <input className={input} placeholder="ISO 9001:2015, ISO 27001" value={profile.certifications.join(", ")}
              onChange={(e) => set("certifications", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))} />
          </label>
          <label className="block">OEM authorisations you hold, separated by commas
            <input className={input} value={profile.oem_authorizations.join(", ")}
              onChange={(e) => set("oem_authorizations", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))} />
          </label>
        </fieldset>

        <fieldset>
          <legend className="text-lg font-semibold">What you do</legend>
          <p className="mt-1 text-sm text-ink-soft">Tenders ask for "similar work". Pick the categories that describe your business.</p>
          <TagPicker tags={tags} value={profile.sector_tags} onChange={(v) => set("sector_tags", v)} />
        </fieldset>

        <fieldset>
          <legend className="text-lg font-semibold">Completed projects</legend>
          <p className="mt-1 text-sm text-ink-soft">List completed orders with their value. These are matched against experience requirements.</p>
          <div className="mt-4 space-y-4">
            {profile.past_projects.map((p, i) => (
              <div key={i} className="rounded-xl border border-rule bg-sheet p-4">
                <div className="grid gap-3 sm:grid-cols-[2fr_1fr_1fr_1fr]">
                  <label className="block text-sm">Project
                    <input required className={input} value={p.title} onChange={(e) => updateProject(i, { title: e.target.value })} />
                  </label>
                  <label className="block text-sm">Client
                    <select className={input} value={p.client_type} onChange={(e) => updateProject(i, { client_type: e.target.value as PastProject["client_type"] })}>
                      <option value="govt">Government</option><option value="psu">PSU</option><option value="private">Private</option>
                    </select>
                  </label>
                  <label className="block text-sm">Value (₹)
                    <input type="number" min={0} required className={input} value={p.value_inr || ""} onChange={(e) => updateProject(i, { value_inr: Number(e.target.value) })} />
                  </label>
                  <label className="block text-sm">Completed
                    <input type="number" min={1990} max={2100} required className={input} value={p.completed_year || ""} onChange={(e) => updateProject(i, { completed_year: Number(e.target.value) })} />
                  </label>
                </div>
                <TagPicker tags={tags} value={p.work_tags} onChange={(v) => updateProject(i, { work_tags: v })} />
                <button type="button" className="mt-3 text-sm font-semibold text-fail underline" onClick={() => set("past_projects", profile.past_projects.filter((_, j) => j !== i))}>
                  Remove project
                </button>
              </div>
            ))}
          </div>
          <button type="button" className="mt-4 rounded-lg border border-ink/20 bg-sheet px-4 py-2 font-semibold hover:border-stamp"
            onClick={() => set("past_projects", [...profile.past_projects, { title: "", client_type: "govt", value_inr: 0, completed_year: new Date().getFullYear(), work_tags: [] }])}>
            Add project
          </button>
        </fieldset>

        <div className="flex flex-wrap items-center gap-4 border-t border-rule pt-6">
          <button type="submit" className="rounded-lg bg-stamp px-6 py-3 font-semibold text-white hover:bg-stamp-deep">
            {isDemo ? "Save as my profile" : "Save profile"}
          </button>
          {status && <span role="status" className="text-met">{status}</span>}
        </div>
        {error && <ErrorNote message={error} />}
      </form>
    </div>
  );
}

function TagPicker({ tags, value, onChange }: { tags: Record<string, string>; value: string[]; onChange: (v: string[]) => void }) {
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {Object.entries(tags).map(([key, label]) => {
        const on = value.includes(key);
        return (
          <button key={key} type="button" aria-pressed={on}
            onClick={() => onChange(on ? value.filter((v) => v !== key) : [...value, key])}
            className={`rounded-full border px-3 py-1 text-sm ${on ? "border-stamp bg-stamp-soft font-semibold text-stamp" : "border-rule bg-sheet text-ink-soft hover:text-ink"}`}>
            {label}
          </button>
        );
      })}
    </div>
  );
}
