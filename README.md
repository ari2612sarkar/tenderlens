# TenderLens

**Know if your MSME can bid on a government tender before you read 40 pages of it.**

Upload a GeM or CPPP tender PDF. TenderLens reads it, checks every eligibility rule against your company
profile, and shows the exact line, on the exact page, behind each answer. It also flags risky contract
clauses with ready-to-send pre-bid queries, lists the documents to prepare, and matches you to central
MSME schemes.

**Live app (AWS PartyRock, Amazon Bedrock):** https://partyrock.aws/u/soviet1991/OCmIbF0Qg/TenderLens-Lite%253A-Government-Bid-Eligibility-Checker

**Code:** https://github.com/ari2612sarkar/tenderlens

Built for **AWS Builder Center: Zero to Shipped (2026)** · Category `#commercial-potential` · Lane `#startups`
(Valivo.ai's first vertical).

## Why

India's government buys lakhs of crores of goods and services every year through GeM and CPPP, with
explicit preferences for micro and small enterprises: EMD exemptions, relaxed turnover and experience
criteria for MSEs and startups. But each bid is a 10 to 200 page PDF where those rules are buried in
bilingual tables, annexures and boilerplate. Small firms either skip tenders they could win or bid on
ones they're ineligible for.

## The core idea: the AI reads, rules decide

A language model is good at finding requirements in a long PDF and bad at guaranteeing it didn't
invent one. TenderLens splits the job:

1. **Extract**: two Claude agents on Amazon Bedrock read the tender in parallel. The eligibility agent
   emits *typed rules* (`min_avg_turnover`, `similar_work`, `requires_cert`, MSE/startup exemptions, ...).
   The risk agent finds clauses like uncapped liquidated damages. Every item carries a verbatim quote and
   page number.
2. **Verify**: code fuzzy-matches each quote against the cited page (±1 page). Numbers in the quote must
   appear on the page. Amounts are re-parsed from the original text ("₹ 2.5 Crore", "50 Lakh (s)") and
   cross-checked. Anything that fails is marked unverified and can only ever produce "Check".
3. **Decide**: a deterministic, unit-tested rule engine evaluates each rule against the company profile
   (Indian financial years, MSE/startup exemptions, similar-work thresholds such as 3×40% / 2×50% / 1×80%
   of estimated cost) and produces the verdict. The model never says "eligible".

## Architecture

```
Browser ── CloudFront ──┬── S3 (React app)
                        └── /api/* ── API Gateway (HTTP API) ── Lambda (api)
                                                                  │ start
                                                                  ▼
             Step Functions: ExtractText ─► Parallel[EligibilityAgent, RiskAgent]
                             ─► VerifyGrounding ─► EvaluateRules ─► Summarize ─► SaveReport
                                    │                     │
                          Textract (scanned pages)   Claude on Amazon Bedrock
             S3 (tenders, page text, artifacts) · DynamoDB (analyses, profiles, rate limits)
```

- **Amazon Bedrock**: Claude via the Messages API endpoint (`AnthropicBedrockMantle`), tool-based
  structured extraction with a validation and repair round, and client-side refusal fallback.
- **AWS Step Functions**: each stage is a visible state with retries for throttling and transient errors.
  A catch-all marks the analysis failed with a readable reason.
- **AWS Lambda** (Python 3.12), **Amazon S3**, **Amazon DynamoDB** (TTL), **Amazon CloudFront** (SPA
  plus same-origin API), **Amazon Textract** for scanned pages.
- Infrastructure as code: one **AWS CDK (TypeScript)** stack in `infra/`.

## Repository

| Path | What |
|---|---|
| `backend/tenderlens/` | Core package: models, grounding, rule engine, document handling, agents |
| `backend/tests/` | Unit tests for the decision core (`pytest`) |
| `backend/handlers/` | Lambda handlers: HTTP API and Step Functions tasks |
| `frontend/` | React + Vite + Tailwind web app |
| `infra/` | AWS CDK stack (TypeScript) |
| `data/samples/` | Live GeM bid documents used as samples |
| `data/schemes/` | Official scheme sources and extracted, grounded rules |
| `scripts/` | Build, deploy, scheme ingestion, sample precompute |
| `docs/` | Design spec, submission pack (`docs/submission/`: post, runbook, demo script, architecture) |

## Run it

```bash
# tests for the decision core
cd backend && python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt && .venv/Scripts/python -m pytest

# full pipeline locally against a PDF (needs AWS credentials with Bedrock access)
.venv/Scripts/python scripts/run_local.py ../data/samples/gem_9622880.pdf ../data/profiles/acme_infotech.json out.json

# deploy (us-east-1)
bash scripts/deploy.sh
```

## How a coding agent built and shipped this

The app was designed and built with **Claude Code**. The agent wrote the code and tests, synthesised the
CDK stack, and built the live PartyRock version through Claude in Chrome (recorded in
`docs/submission/proof/partyrock-build.gif`). The production stack deploys with `scripts/deploy.sh` once the
AWS account is activated. See
[`docs/agent-aws-connection.md`](docs/agent-aws-connection.md) for the evidence.

---

TenderLens is a decision aid, not legal advice. Always confirm requirements against the tender.
# AWS-Hackathon-2026
