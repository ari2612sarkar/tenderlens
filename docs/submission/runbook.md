# TenderLens: deploy-day runbook

**Deadline:** Oct 2, 11:59 PM PDT = **Oct 3, 12:29 PM IST**. Everything except the AWS account is ready.

| If the access key exists by… | Plan |
|---|---|
| Oct 3, 7:00 AM IST | Full plan: 4 samples, schemes, polish, video |
| Oct 3, 9:00 AM IST | Lean plan: 3 samples, schemes only if first try works, 1-take video |
| Oct 3, 10:30 AM IST | Minimum plan: deploy plus 2 samples, screenshots, submit (video optional) |
| after Oct 3, 10:30 AM IST | Too tight to deploy safely. Submit isn't possible without a live URL. |

---

## Part 1: whoever provides the AWS account (10–20 min, browser)

Any adult with a card can do this: a parent, sibling, friend, or the Valivo.ai co-founder.

### 1a. If they don't have an AWS account yet
1. Go to <https://aws.amazon.com> → **Create an AWS account**.
2. Enter an email, account name ("TenderLens") and verify the email.
3. Add a **Visa/Mastercard debit or credit card** with online/international use enabled in the bank app.
   AWS holds about ₹2 to verify it, then releases it.
4. Verify the phone number (OTP) and choose **Basic support (free)**.
5. When asked for a plan, **Free plan** is fine to start.
6. Wait for the "Your account is ready" email (usually minutes, can take longer).

### 1b. Create a key for the coding agent (existing or new account)
1. Sign in → open <https://console.aws.amazon.com/iam/home#/users> → **Create user**.
2. User name: `claude-code-agent` → **Next**.
3. **Attach policies directly** → tick **AdministratorAccess** → **Next** → **Create user**.
4. Click `claude-code-agent` → **Security credentials** tab → **Create access key**.
5. Choose **Command Line Interface (CLI)** → tick the confirmation → **Next** → **Create access key**.
6. Keep this page open. Type the **Access key** and **Secret access key** straight into the builder's
   computer (Part 2). Don't send the secret over chat or email if you can avoid it.

### 1c. Turn on Claude in Amazon Bedrock
1. Top-right region selector → **US East (N. Virginia) us-east-1**.
2. Search **Amazon Bedrock** → **Model catalog** → filter provider **Anthropic**.
3. Open **Claude Opus 4.8** and **Claude Opus 5.5**. If you see **Request access**, a use-case form, or
   **Subscribe**, complete it. Use case: "Hackathon prototype: analysing public government tender documents."
4. If the console says the Free plan can't use this model, click **Upgrade plan** (top banner or Billing).
   Expected spend for the hackathon is a few hundred rupees: about ₹20–60 per tender analysis, and
   near-zero for everything else.

### 1d. (Recommended) Budget alert
Billing → **Budgets** → **Create budget** → **Use a template** → **Monthly cost budget** → amount **$20** →
add your email → **Create**.

---

## Part 2: you, on your laptop (3 min)

Open **PowerShell** (Start → type "PowerShell") and run these three lines, pasting the values from 1b:

```powershell
& "C:\Users\TUF\AppData\Local\awscliv2\Amazon\AWSCLIV2\aws.exe" configure set aws_access_key_id PASTE_ACCESS_KEY
& "C:\Users\TUF\AppData\Local\awscliv2\Amazon\AWSCLIV2\aws.exe" configure set aws_secret_access_key PASTE_SECRET_KEY
& "C:\Users\TUF\AppData\Local\awscliv2\Amazon\AWSCLIV2\aws.exe" configure set region us-east-1
```

Then tell Claude Code: **"keys are in, run the runbook"**.

---

## Part 3: Claude Code (about 2 hours, mostly unattended)

| Step | Command / action | Time box |
|---|---|---|
| 1 | `aws sts get-caller-identity` (screenshot = proof #1) | 2 min |
| 2 | `backend/.venv/Scripts/python scripts/smoke_bedrock.py`: finds a Claude model the account can use, then pins it in `infra/cdk.json` | 10 min |
| 3 | `backend/.venv/Scripts/python backend/scripts/run_local.py data/samples/gem_9622880.pdf data/profiles/acme_infotech.json build/local_report.json`: fix prompts if needed | 30 min |
| 4 | `cd infra && npx cdk bootstrap aws://ACCOUNT_ID/us-east-1` | 10 min |
| 5 | `bash scripts/deploy.sh` (screenshot = proof #2) | 20 min |
| 6 | `backend/.venv/Scripts/python scripts/precompute_samples.py`, then wait for 4 reports | 15 min |
| 7 | `backend/.venv/Scripts/python scripts/ingest_schemes.py`, then redeploy. **One try**: if it fails, hide the Schemes nav | 15 min |
| 8 | Smoke test the public URL: home → sample report → page tag → live analysis | 10 min |
| 9 | Screenshots: Step Functions graph (proof #4), CloudTrail filtered to `claude-code-agent` (proof #3), report page | 10 min |
| 10 | Fill `[[...]]` placeholders in `docs/submission/post.md`; update the home-page specimen to match a real report | 15 min |

---

## Part 4: you (40 min)

1. **Record the demo** with `docs/submission/demo-script.md` (Windows: **Win + Alt + R** starts/stops Xbox
   Game Bar recording; or use OBS). Upload to YouTube as **Unlisted** and copy the link.
2. **Publish the code**: on github.com → **New repository** `tenderlens` (Public) → copy the URL → tell
   Claude Code "push to <url>". It adds the remote and pushes.
3. **Builder Center**: open your project → paste `docs/submission/post.md` → upload the architecture image
   and the 4 proof screenshots → add tags **#commercial-potential** and **#startups** → **Submit** before
   **12:29 PM IST, Oct 3**.
4. After judging, delete the `claude-code-agent` access key in IAM.
