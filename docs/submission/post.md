# Builder Center project post: TenderLens

> Paste everything below the line into your Builder Center project. Replace each `[[...]]` placeholder
> after deployment (the runbook says when). Tags to add on the project: **#commercial-potential** and **#startups**.

---

## TenderLens: know if your MSME can bid on a government tender before you read 40 pages of it

**Live app:** [[LIVE_URL]]  ·  **Code:** [[GITHUB_URL]]  ·  **2-minute demo:** [[VIDEO_URL]]

**Category:** Commercial potential  ·  **Lane:** Startups

### The problem

The Indian government buys a huge share of its goods and services through the Government e-Marketplace
(GeM) and the Central Public Procurement Portal (CPPP), and the rules deliberately favour micro and small
enterprises (MSEs). Many tenders waive the bid security (EMD) for MSEs and relax the turnover and
experience criteria for MSEs and startups.

But every opportunity arrives as a 10 to 200 page PDF. The eligibility rules sit in bilingual tables,
annexures and boilerplate, and the exemptions are one "Yes" in a long list of fields. A small firm owner
has two bad options: spend hours reading every bid, or skip tenders they could have won. Bidding on the
wrong one wastes days of document preparation.

I co-founded **Valivo.ai**, an AI automation company in Gurugram that builds agentic systems for business
workflows. Long, messy procurement documents are exactly the kind of work we automate. TenderLens is the
first vertical product we're building on that foundation.

### What TenderLens does

Upload a tender PDF and choose your company profile. In about two to four minutes you get:

- **A verdict, stamped:** Eligible, Eligible with caution, Check items, Not eligible, or Closed.
- **Every requirement, one by one**: average turnover, similar-work experience, certificates, registrations,
  OEM authorisation. Each has your status (Met / Not met / Exempt / Check / Add data), the reason in plain
  language (for example "Average turnover ₹2.6 Cr (FY 2023-24 to 2025-26) ≥ required ₹50 L") and a
  **page tag that opens the tender's exact words**.
- **MSE and startup exemptions applied automatically**, but only when the tender itself grants them.
- **Risky clauses** (uncapped liquidated damages, long payment cycles, performance security, unlimited
  liability) explained for a business owner, each with a **ready-to-send pre-bid query**.
- **A document checklist** for the bid.
- **Government schemes you may qualify for** (CGTMSE, ZED, Public Procurement Policy for MSEs and others),
  matched by the same rule engine from official scheme documents.

### The idea that makes it trustworthy: the AI reads, rules decide

A language model is very good at finding requirements in a long PDF, and bad at guaranteeing it didn't
invent one. For a bid/no-bid decision, an invented requirement is worse than none. So TenderLens splits the
work:

1. **Extract.** Two Claude agents on Amazon Bedrock read the tender in parallel. The *eligibility agent*
   returns **typed rules** (`min_avg_turnover`, `similar_work`, `requires_cert`, MSE/startup exemptions and
   so on), not prose. The *risk agent* returns risky clauses. **Every item carries a verbatim quote and a
   page number.**
2. **Verify.** Plain code checks every quote against the page it cites (±1 page, tolerant of whitespace
   and hyphenation). Every number in the quote must appear on that page. Rupee amounts are re-parsed from
   the original wording ("₹ 2.5 Crore", "50 Lakh (s)") and cross-checked against what the model wrote. An
   item that fails **can never produce a pass or a fail**; it can only say "Check".
3. **Decide.** A deterministic rule engine, with 84 unit tests, compares the rules to the company profile.
   It understands Indian financial years, the common similar-work pattern (3 works of 40% / 2 of 50% / 1 of
   80% of estimated cost) and MSE/startup waivers. **The model never decides "eligible".**

Anything the model can't express as a typed rule becomes a `freeform` requirement that always asks for a
human check. "I don't know" is a first-class answer.

### Built on AWS

![TenderLens architecture](architecture.png)

- **Amazon Bedrock:** Claude [[MODEL_NAME]] through the Messages API endpoint, with tool-based structured
  extraction, Pydantic validation, one automatic repair round, and client-side refusal fallback.
- **AWS Step Functions:** the pipeline is a visible state machine: ExtractText → Parallel(EligibilityAgent,
  RiskAgent) → VerifyGrounding → EvaluateRules → Summarize → SaveReport. Throttling and transient errors
  are retried per step, and any failure is caught and shown to the user as a readable message.
- **AWS Lambda** (Python 3.12), **Amazon S3** (tenders and per-step artifacts), **Amazon DynamoDB**
  (analyses, profiles, per-IP rate limits, with TTL), **Amazon Textract** (scanned pages), **Amazon
  CloudFront** (React app plus same-origin API), **Amazon API Gateway** (HTTP API with throttling).
- Everything is one **AWS CDK** stack and costs nearly nothing when idle.

### How a coding agent helped me ship

I built TenderLens with **Claude Code connected to my AWS account** through the AWS CLI, using a dedicated
IAM user, `claude-code-agent`, so every action it took is visible in CloudTrail (proof below). It worked
as a full engineering partner, not an autocomplete:

- **Product discovery.** It read my CV, pitched three directions, and when I asked to combine two of them
  it proposed the tender copilot: tenders are eligibility rules and contract terms in one PDF. It then
  wrote a design spec before any code.
- **Test-first core.** It built the decision engine test-first (84 tests). A failing test caught a real
  bug, a page-boundary check that reached two pages away and could have "verified" a quote from the wrong
  page.
- **Real data, real problems.** It pulled live bids from GeM's public search and found that the Hindi half
  of GeM's bilingual labels extracts as garbled glyph pairs. It wrote a tested cleaner so both the model
  and the verifier see the same clean text.
- **Reading the docs instead of guessing.** Before writing the Bedrock code it checked the live
  documentation and found that structured outputs aren't available on the Bedrock Messages endpoint and
  that current models reject forced tool choice. It switched to a submit-tool pattern with Pydantic
  validation and a repair round, and found the exact IAM action (`bedrock-mantle:CreateInference`).
- **Getting unstuck.** It installed the AWS CLI without admin rights by extracting the MSI. When the Python
  CDK package stalled on PyPI, it measured the download speeds, saw npm was fast, and ported the stack to
  TypeScript CDK. The stack synthesized cleanly on the first try.
- **Deploy and verify.** [[DEPLOY_STORY: 2-3 sentences written after deployment: bootstrap/deploy,
  any issue it debugged from CloudWatch or Step Functions, the samples it precomputed]]

### Proof of the coding agent ↔ AWS connection

- Claude Code terminal running `aws sts get-caller-identity` → `arn:aws:iam::[[ACCOUNT_ID]]:user/claude-code-agent`
  [[SCREENSHOT_1]]
- Claude Code running `cdk deploy` for the TenderLens stack [[SCREENSHOT_2]]
- CloudTrail event history filtered to user `claude-code-agent` (CreateStack, StartExecution and more)
  [[SCREENSHOT_3]]
- The Step Functions graph of a real analysis run [[SCREENSHOT_4]]

### Try it in 30 seconds

Open the live app, choose any **"Real tenders, already analysed"** row, and click a **page tag** next to
a requirement to read the tender's exact words. To see the pipeline run live, go to **Analyze a tender**,
pick a sample tender and a demo company, and watch the steps complete.

### Where this goes next (Startups lane)

- **Who pays:** MSMEs that bid regularly on GeM/CPPP, and the consultants and CA firms who prepare bids for
  them. That's a recurring, per-tender job with a clear time saving.
- **Next 90 days:** daily alerts for new GeM bids that match a company profile, Hindi output, a saved
  document locker that pre-fills the checklist, and a bid-preparation workspace.
- **Moat:** the grounded, typed-rule approach generalises to any compliance-heavy document (state portals,
  PSU tenders, scheme applications), which is Valivo.ai's core competence.

*TenderLens is a decision aid, not legal advice. Always confirm requirements against the tender.*
