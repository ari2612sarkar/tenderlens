# TenderLens: 2-minute demo script

Record the browser at 1280×800 or larger. Speak slowly; it's fine to cut between takes.
The spoken lines describe what the sample report is expected to show; **adjust them to what the deployed report actually shows**.
Before recording: open the live app home page in tab 1, the Step Functions console (state machine
`TenderLens-AnalyzeTender`) in tab 2, and have a sample tender PDF handy.

| Time | Screen | Say |
|---|---|---|
| 0:00–0:15 | Home page hero | "Government tenders in India favour small businesses, but every bid is a 40-page PDF. TenderLens tells an MSME whether it can bid, and shows the exact line behind every answer." |
| 0:15–0:45 | Click a sample row → report. Pause on the stamp, then scroll the requirements table. Click a **p. N** tag to open the quote. | "This is a live GeM bid from the Indian Air Force, checked for a demo IT company. Each requirement has a status and a reason, and this tag opens the tender's own words from that page. Turnover isn't met, but the tender grants an MSE exemption, so it's marked exempt. TenderLens only applies exemptions the tender actually grants." |
| 0:45–1:05 | Scroll to risks → click **Copy query** | "A second agent reads the contract terms. Here's an uncapped penalty clause, and a pre-bid query you can send to the buyer, ready to copy." |
| 1:05–1:30 | **Analyze a tender** → choose a sample (or upload a PDF) → demo company → **Analyze tender**. Show the progress steps, then switch to tab 2 to show the Step Functions graph running. | "Here's a fresh run. It's an AWS Step Functions pipeline: text extraction, two Claude agents on Amazon Bedrock running in parallel, then plain code that checks every quote against its page before a rule engine decides." |
| 1:30–1:45 | Back in the app as the report lands; point at "Quotes verified X of Y" | "The model never decides eligibility. If a quote can't be found on its page, that item can only say 'check', never pass or fail." |
| 1:45–2:00 | Architecture image (or the Claude Code terminal) | "I built and deployed all of this with Claude Code connected to my AWS account: tests first, real GeM data, one CDK stack. TenderLens is Valivo.ai's first vertical. Thanks for watching." |

**If a live run takes longer than the recording:** start the analysis *before* you begin recording, so the
report lands during the 1:30 segment, or cut straight from the progress screen to a finished sample report.
