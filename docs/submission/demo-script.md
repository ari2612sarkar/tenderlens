# TenderLens: 2-minute demo script (PartyRock live app)

Record the browser at 1280×800 or larger (Windows: **Win + Alt + R** starts and stops recording).
Before recording: open the live app, sign in to PartyRock, and keep `data/samples/gem_9622880.pdf` handy.
Tip: run the flow once *before* recording, so you can show finished outputs while the live run happens.

| Time | Screen | Say |
|---|---|---|
| 0:00–0:15 | App title and description | "Government tenders in India favour small businesses, but every bid is a 40-page PDF. TenderLens tells an MSME whether it can bid, and shows the exact line behind every answer." |
| 0:15–0:35 | Press **Play**, upload the Air Force bid PDF, show the pre-filled demo company | "This is a live GeM bid from the Indian Air Force. I upload the bid document, and here's a demo small IT company from Haryana." |
| 0:35–1:05 | Open **Can you bid?**: scroll the table, pause on row 1 | "Every requirement gets a status and the numbers behind it. Turnover: the tender needs five crore, the company averages two point six, but the tender grants an MSE relaxation on page 4, and it's quoted right here, so it's marked exempt. The verdict: eligible with caution, because the tender wants a service centre near Bangalore." |
| 1:05–1:25 | Open **Risky clauses and pre-bid queries** | "A second step reads the contract terms like a lawyer would, and drafts a pre-bid query for each risk." |
| 1:25–1:40 | **Documents to prepare**, then ask the chatbot "Is EMD required for MSEs?" | "A checklist of only what this tender asks for, and a chatbot that answers by quoting the tender." |
| 1:40–2:00 | `architecture.png` | "It runs on Claude on Amazon Bedrock. The production version in the repo adds code that verifies every quote and a tested rule engine on Step Functions. I built all of it with Claude Code. TenderLens is Valivo.ai's first vertical. Thanks for watching." |
