# TenderLens — Design Spec

**Date:** 2026-10-01 · **Event:** AWS Builder Center "Zero to Shipped" (due 2026-10-02 23:59 PDT)
**Category / lane:** `#commercial-potential` · `#startups` (Valivo.ai's first vertical)

## 1. Problem and intent

Indian MSMEs lose government business not because they can't do the work, but because tender documents
(GeM / CPPP) are 20–200 page PDFs that bury eligibility rules, exemptions and risky contract terms.
Owners either skip tenders they could win, or bid on ones they're ineligible for and forfeit time and EMD.
Meanwhile MSME schemes they qualify for go unclaimed.

**TenderLens**: upload a tender PDF, get a grounded bid/no-bid verdict against your company profile in
about two minutes, plus risky clauses with ready-to-send pre-bid queries, a document checklist, and the
government schemes you qualify for.

**Success criteria (hackathon):**
- Live on AWS at a public URL; a judge sees a full result within one click (no login).
- Every extracted fact shows a verbatim quote and page number; unverifiable facts never drive the verdict.
- Story: "LLM extracts, code decides" — reliability over vibes.

## 2. Principles

1. **LLM extracts, code decides.** The model never outputs "eligible". It emits typed rules; a deterministic
   engine evaluates them.
2. **Every claim is grounded.** Each item carries `quote` + `page`; code verifies the quote appears on that page.
3. **Unknown is a first-class answer.** Anything not expressible as a typed rule → `NEEDS_REVIEW` (human in the loop).
4. **Judges first.** Sample tenders + demo profiles with cached results; uploads are optional.

## 3. Architecture

```
Browser (React + Vite + Tailwind, static)
   │  CloudFront: /* → S3 site bucket, /api/* → API Gateway
   ▼
API Gateway (HTTP API) ──► api Lambda (Python 3.12)
   POST /api/uploads        presigned S3 PUT (PDF, ≤25 MB)
   POST /api/profiles       create/update profile
   GET  /api/profiles/{id}
   POST /api/analyses       start Step Functions execution → analysis_id
   GET  /api/analyses/{id}  status per step + report
   GET  /api/schemes/match?profile_id=   pure-code scheme matching
   GET  /api/samples        sample tenders, demo profiles, cached analysis ids
   ▼
Step Functions (Standard) "AnalyzeTender"
   ExtractText → Parallel[EligibilityAgent, RiskAgent] → VerifyGrounding → Evaluate → Summarize → Save
   Catch(any) → MarkFailed
```

- **Region:** us-east-1. **Models:** Claude Sonnet (agents) and Claude Haiku (summary) on Amazon Bedrock via
  the Converse API with forced tool use for structured output.
- **Storage:** S3 bucket (`tenders/`, `pages/`, `results/`); DynamoDB tables `Profiles`, `Analyses`, `Schemes`.
- **IaC:** single AWS CDK (TypeScript) stack. Lambda dependencies vendored with `pip --platform manylinux2014_x86_64`
  (no Docker).
- **ExtractText:** `pypdf` per page; pages with < 40 chars of text are OCR'd with Textract. If the document
  exceeds the token budget (~350k chars), pages are ranked by eligibility/risk keyword density and the top
  pages are sent (page numbers preserved).
- **Retries:** Step Functions retries Bedrock `ThrottlingException`/`ServiceUnavailable` with exponential
  backoff (4 attempts); agent steps time out at 10 min.
- **Inter-step data:** large payloads live in S3; state carries keys only (256 KB limit).

## 4. Data model

### Company profile
```
name, enterprise_size: micro|small|medium|large, dpiit_startup: bool, state,
incorporation_year, net_worth_inr, employee_count,
turnover_by_fy: {"2024-25": int_inr, ...},
certifications: [str], registrations: [str],          # e.g. GST, PAN, EPF, ESIC, Udyam
past_projects: [{title, client_type: govt|psu|private, value_inr, completed_year, work_tags: [tag]}],
oem_authorizations: [str], sector_tags: [tag], women_owned: bool, sc_st_owned: bool
```

### Extracted items (all carry `quote`, `page`, and after verification `grounded: bool`)
```
Criterion {id, category, mandatory, exemptible_for: [mse|startup], rule, description}
  rule (discriminated on `type`):
    min_avg_turnover    {amount_inr, amount_text, fys | last_n}
    min_net_worth       {amount_inr, amount_text}
    min_years_in_op     {years}
    similar_work        {options: [{count, min_value_inr, min_value_text}], within_years, work_tags, definition_text}
    requires_cert       {any_of}
    requires_registration {any_of}
    oem_auth            {brands}
    enterprise_size     {any_of}            # schemes
    location            {states}            # schemes
    sector              {work_tags}         # schemes
    freeform            {text}              # → always NEEDS_REVIEW
Exemption  {for: mse|startup, waives: [emd|turnover|experience|...]}
KeyFacts   {tender_no, organisation, title, bid_end, emd_inr, est_value_inr, pbg_pct, contract_period}
RiskFlag   {category, severity: high|medium|low, explanation, suggested_prebid_query}
DocRequired{name, reason}
```

### Guards
1. **Quote grounding:** normalized fuzzy partial match (rapidfuzz, ≥ 85) against cited page ±1.
2. **Amount cross-check:** code parses `amount_text` (₹/Rs/INR, lakh, crore, commas); mismatch with
   `amount_inr` (> 1%) → NEEDS_REVIEW.
3. **Similar work:** fixed taxonomy of ~20 work tags; project matches if tags intersect.
4. **FY inference:** if tender gives "last N financial years", code derives the last N completed Indian FYs
   before `bid_end` (or today).

## 5. Evaluate (pure Python)

Per criterion status: `MET · NOT_MET · EXEMPT · NEEDS_REVIEW · MISSING_DATA` + one-line reason.
Exemption applies when the criterion is `exemptible_for` a class the company belongs to AND a grounded
`Exemption` waiving that category exists (MSE = micro/small).

Verdict:
- bid_end in the past → `CLOSED`
- any mandatory NOT_MET → `NOT_ELIGIBLE`
- else any mandatory NEEDS_REVIEW / MISSING_DATA → `CHECK_ITEMS`
- else `ELIGIBLE`; with ≥1 grounded high-severity risk → `ELIGIBLE_WITH_CAUTION`

Schemes reuse the same engine: `ELIGIBLE · POSSIBLY_ELIGIBLE · NOT_ELIGIBLE`.

## 6. UX

1. **Home:** one-line pitch, "Try a sample" cards (3 real tenders × demo profile, cached → instant),
   "Analyze your own tender" CTA, "How it works" strip showing the pipeline.
2. **Profile:** form with prefilled demo profiles; profile id kept in localStorage.
3. **Analyze:** drag-drop PDF + choose profile → live step progress mirroring the Step Functions states.
4. **Report:** verdict banner · key facts · criteria table (status chip, reason, expandable quote + page) ·
   risk flags with copyable pre-bid queries · document checklist · matched schemes · unverified items greyed.
5. **Schemes:** matches for the active profile with benefit summary + official link.

## 7. Guardrails

- API Gateway stage throttling (burst 20, rate 10 rps); per-IP limit of 10 analyses/day (DynamoDB counter).
- PDF only, ≤ 25 MB, ≤ 300 pages. Bedrock `maxTokens` capped per agent.
- AWS Budgets alarm at $25. Demo results pre-computed so judge traffic costs ~nothing.

## 8. Testing

- `pytest` unit tests (TDD) for amounts, FY, grounding, evaluate, scheme matching — the decision core.
- Local pipeline runner (`scripts/run_local.py`) runs the full pipeline against a PDF using real Bedrock.
- Post-deploy smoke test: hit `/api/samples`, fetch a cached analysis, run one live analysis end to end.

## 9. Build order (cut from the bottom if time runs short)

1. Core package + tests (models, amounts, FY, grounding, evaluate)
2. Bedrock agents + local runner on a real tender
3. CDK stack: storage, Lambdas, Step Functions, API, CloudFront; deploy
4. Frontend: home, report, analyze, profile
5. Sample tenders + precomputed analyses
6. Scheme corpus ingestion + matching UI
7. Guardrails (rate limit, budget alarm)
8. Submission: README, architecture diagram, agent-connection proof, demo video script
9. Stretch: "Ask this tender" Q&A

## 10. Submission deliverables

- Live URL; GitHub repo; Builder Center project post with tags `#commercial-potential` `#startups`.
- Proof of coding-agent ↔ AWS connection: Claude Code session transcript/screenshots running AWS CLI/CDK,
  plus CloudTrail events from the agent's credentials.
- Architecture diagram + Step Functions graph screenshot; 2–3 min demo video.
