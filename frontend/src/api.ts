export type Status = "MET" | "NOT_MET" | "EXEMPT" | "NEEDS_REVIEW" | "MISSING_DATA";
export type Verdict = "ELIGIBLE" | "ELIGIBLE_WITH_CAUTION" | "CHECK_ITEMS" | "NOT_ELIGIBLE" | "CLOSED";
export type SchemeVerdict = "ELIGIBLE" | "POSSIBLY_ELIGIBLE" | "NOT_ELIGIBLE";

export interface Cited {
  quote: string;
  page: number;
  grounded?: boolean | null;
}

export interface Criterion extends Cited {
  id: string;
  category: string;
  description: string;
  mandatory: boolean;
  rule: { type: string; [key: string]: unknown };
}

export interface CriterionResult {
  criterion: Criterion;
  status: Status;
  reason: string;
  matched_projects: string[];
}

export interface Risk extends Cited {
  category: string;
  severity: "high" | "medium" | "low";
  title: string;
  explanation: string;
  suggested_prebid_query?: string | null;
}

export interface DocRequired extends Cited {
  name: string;
  reason: string;
}

export interface Exemption extends Cited {
  applies_to: "mse" | "startup";
  waives: string[];
}

export interface KeyFacts {
  tender_no?: string | null;
  organisation?: string | null;
  title?: string | null;
  bid_end?: string | null;
  emd_inr?: number | null;
  est_value_inr?: number | null;
  pbg_pct?: number | null;
  contract_period?: string | null;
}

export interface Report {
  key_facts: KeyFacts;
  verdict: Verdict;
  verdict_text: string;
  summary: { headline: string; summary: string; next_steps: string[] };
  results: CriterionResult[];
  counts: Partial<Record<Status, number>>;
  emd_exempt: boolean;
  exemptions: Exemption[];
  risks: Risk[];
  documents_required: DocRequired[];
  grounding: { checked: number; grounded: number };
  profile: { id: string; name: string };
  stats: { pages?: number; ocr_pages?: number; seconds?: number; tokens?: number; model?: string };
  analyzed_at: string;
}

export interface Analysis {
  id: string;
  status: "RUNNING" | "DONE" | "FAILED";
  step: string;
  steps_done: string[];
  error?: string;
  verdict?: Verdict;
  title?: string;
  organisation?: string;
  profile_id: string;
  report?: Report;
  pdf_url?: string;
}

export interface Sample {
  id: string;
  bid_number: string;
  title: string;
  organisation: string;
  sector: string;
  closes: string;
  pdf: string;
  profile_id: string;
  analysis_id: string;
}

export interface PastProject {
  title: string;
  client_type: "govt" | "psu" | "private";
  value_inr: number;
  completed_year: number;
  work_tags: string[];
}

export interface Profile {
  id?: string | null;
  name: string;
  enterprise_size: "micro" | "small" | "medium" | "large";
  dpiit_startup: boolean;
  state: string;
  incorporation_year: number | null;
  net_worth_inr: number | null;
  employee_count: number | null;
  turnover_by_fy: Record<string, number>;
  certifications: string[];
  registrations: string[];
  past_projects: PastProject[];
  oem_authorizations: string[];
  sector_tags: string[];
  women_owned: boolean;
  sc_st_owned: boolean;
}

export interface SchemeMatch {
  id: string;
  name: string;
  benefit: string;
  ministry?: string;
  source_url?: string;
  verdict: SchemeVerdict;
  results: CriterionResult[];
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.error ?? `Request failed (${res.status})`);
  return body as T;
}

export const api = {
  samples: () => call<{ samples: Sample[]; profiles: Profile[] }>("/samples"),
  taxonomy: () => call<{ work_tags: Record<string, string> }>("/taxonomy"),
  analysis: (id: string) => call<Analysis>(`/analyses/${id}`),
  startAnalysis: (body: { profile_id: string; tender_key?: string; sample_id?: string }) =>
    call<{ id: string }>("/analyses", { method: "POST", body: JSON.stringify(body) }),
  profile: (id: string) => call<Profile>(`/profiles/${id}`),
  saveProfile: (p: Profile) =>
    p.id && !p.id.startsWith("demo-")
      ? call<Profile>(`/profiles/${p.id}`, { method: "PUT", body: JSON.stringify(p) })
      : call<Profile>("/profiles", { method: "POST", body: JSON.stringify({ ...p, id: null }) }),
  schemes: (profileId: string) =>
    call<{ matches: SchemeMatch[] }>(`/schemes/match?profile_id=${encodeURIComponent(profileId)}`),
  async uploadPdf(file: File): Promise<string> {
    const { upload_url, tender_key } = await call<{ upload_url: string; tender_key: string }>("/uploads", {
      method: "POST",
      body: JSON.stringify({ filename: file.name, size: file.size }),
    });
    const put = await fetch(upload_url, { method: "PUT", body: file, headers: { "content-type": "application/pdf" } });
    if (!put.ok) throw new Error("Upload failed. Check your connection and try again.");
    return tender_key;
  },
};

const PROFILE_KEY = "tl.profileId";
export const DEFAULT_PROFILE = "demo-acme-infotech";

export function activeProfileId(): string {
  try {
    return localStorage.getItem(PROFILE_KEY) || DEFAULT_PROFILE;
  } catch {
    return DEFAULT_PROFILE;
  }
}

export function setActiveProfileId(id: string): void {
  try {
    localStorage.setItem(PROFILE_KEY, id);
  } catch {
    /* storage unavailable; the default profile is used */
  }
}

export function inr(amount?: number | null): string {
  if (amount == null) return "Not stated";
  const fmt = (v: number) => v.toFixed(2).replace(/\.?0+$/, "");
  if (amount >= 1e7) return `₹${fmt(amount / 1e7)} Cr`;
  if (amount >= 1e5) return `₹${fmt(amount / 1e5)} lakh`;
  return `₹${amount.toLocaleString("en-IN")}`;
}

export function dateTime(iso?: string | null): string {
  if (!iso) return "Not stated";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit" });
}
