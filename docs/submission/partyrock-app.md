# TenderLens Lite on PartyRock: app definition

> **As built (Oct 2, 2026):** live at https://partyrock.aws/u/soviet1991/OCmIbF0Qg/TenderLens-Lite%253A-Government-Bid-Eligibility-Checker
> (shared with "Anyone with the link"). PartyRock generated the flow from a description; the agent then appended the
> grounding rules below to each AI step, set every step to Claude Sonnet 5 on Bedrock with web search off, and
> pre-filled the demo company. Live widget names: Tender PDF, Eligibility Requirements and MSE Exemptions,
> Company Profile, Tender Chatbot, Document Preparation Checklist, Risky Contract Clauses and Pre-Bid Queries,
> Eligibility Check and Verdict. The definition below is the reference spec (and a manual rebuild guide).

Live demo of TenderLens that runs on AWS PartyRock (Amazon Bedrock) with no AWS account needed.
Build at <https://partyrock.aws/> → **Build your own app** → start from a blank app and add the widgets below in order.
In each AI widget's settings, pick the most capable **Claude** model offered.

**App title:** TenderLens Lite: can your MSME bid on this tender?
**App description:** Upload a GeM or CPPP tender PDF and your company details. TenderLens Lite lists every
bidder requirement with the tender's exact words and page, checks each one against your company (including
MSE and startup exemptions), flags risky clauses with pre-bid queries, and lists the documents to prepare.

---

## Widget 1: Document
**Title:** Tender document
**Placeholder / description:** Upload the GeM or CPPP bid document (PDF).

## Widget 2: User input
**Title:** Your company profile
**Default value:**
```
Company: Acme Infotech Pvt Ltd (demo)
Udyam category: Small enterprise (MSE)
DPIIT-recognised startup: No
State: Haryana
Established: 2017
Turnover: FY 2025-26 ₹3.1 Cr; FY 2024-25 ₹2.6 Cr; FY 2023-24 ₹2.1 Cr
Net worth: ₹3.2 Cr
Certifications: ISO 9001:2015, ISO 27001:2022
Registrations: GST, PAN, Udyam, EPF, ESIC
Completed projects:
- Document management system for a state PSU: ₹95 lakh, 2025 (software development)
- e-Office rollout for a district administration: ₹62 lakh, 2024 (software development, IT support)
- Scanning and digitisation of land records: ₹48 lakh, 2023 (data services, software)
OEM authorisations: none
```

## Widget 3: AI-powered text
**Title:** Requirements in this tender
**Prompt:**
```
You are a senior Indian public-procurement analyst. Read the tender: [Tender document]

List every eligibility or pre-qualification requirement placed on the BIDDER. Do not list the technical specification of the goods or services. Also find every exemption or relaxation the tender grants to MSEs (micro and small enterprises) or startups, and the key facts.

Copy the tender's exact words in quotation marks for every item and give the page number. Never add a requirement that is not written in this tender. If the tender says "No" for an exemption, say it is not granted.

Format:
Key facts: bid number, buyer organisation, bid end date and time, EMD amount, estimated value (write "not stated" when missing).
Requirements: a numbered list. Each line: plain-English requirement — "exact quote" (p. N) — Mandatory or Optional.
Exemptions: bullets with "exact quote" (p. N), or "None stated".
```

## Widget 4: AI-powered text
**Title:** Can you bid?
**Prompt:**
```
Compare this company: [Your company profile]
against these tender requirements: [Requirements in this tender]

For each numbered requirement give exactly one status and a one-line reason that shows the numbers:
✅ Met: the profile clearly satisfies it (e.g. "average turnover ₹2.6 Cr ≥ required ₹50 lakh").
❌ Not met: the profile clearly fails it.
🟦 Exempt: the company fails or lacks data, BUT the tender explicitly grants an exemption this company qualifies for (MSE = micro or small enterprise; startup = DPIIT-recognised). Quote that exemption.
⚠️ Check: the profile doesn't contain the information, or it can't be judged from the text.

Rules: average turnover means the mean over the financial years the tender asks for. Never assume an exemption that isn't quoted in the requirements. When in doubt, use ⚠️ Check.

Finish with one line:
VERDICT: Eligible / Eligible with caution / Check N items / Not eligible, followed by the single most important reason.
```

## Widget 5: AI-powered text
**Title:** Risky clauses and pre-bid queries
**Prompt:**
```
You are a government-contracts lawyer advising the owner of a small Indian business. From this tender: [Tender document]

List up to 6 clauses that create real commercial or legal risk for a small bidder: liquidated damages or penalties, payment terms, performance security, liability or indemnity, termination, vague scope, blacklisting or EMD forfeiture. Skip harmless boilerplate.

For each clause:
- Severity: High, Medium or Low
- The exact quote and page
- Why it matters, in one plain sentence
- A polite pre-bid query the bidder could send to the buyer
```

## Widget 6: AI-powered text
**Title:** Documents to prepare
**Prompt:**
```
Using this tender: [Tender document]
and this company: [Your company profile]

Write a checklist of the documents this company must submit with its bid, grouped as:
Eligibility proofs, Exemption proofs (for example the Udyam certificate if claiming an MSE exemption), and Other.
One line per document, with the tender page that asks for it.
```

## Widget 7: Chatbot
**Title:** Ask this tender
**Prompt:**
```
You answer questions about this tender for a small business owner: [Tender document]
Quote the tender's exact words with the page number when you answer. If the tender doesn't say, reply that it doesn't say.
```

---

After building: run it once with `data/samples/gem_9622880.pdf` (Indian Air Force software tender) to check the
output, then **Make public** and copy the share link. That link is `[[LIVE_URL]]` in `post.md`.
