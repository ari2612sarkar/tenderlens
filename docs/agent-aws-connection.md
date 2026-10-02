# Proof: coding agent working on AWS

The hackathon asks for *"a coding agent connected to the AWS console, with documented proof of the
connection."* TenderLens was built with **Claude Code** (Anthropic's coding agent).

**Current status, stated plainly:** my AWS account isn't fully activated yet (card verification pending),
so the agent could not yet sign in to the AWS console with IAM credentials. The live app therefore runs
on **AWS PartyRock** (Amazon Bedrock), which needs no AWS account, and the agent worked on AWS through the
browser instead.

## Evidence available now

1. **The agent building the live app on AWS:** `docs/submission/proof/partyrock-build.gif`, recorded by
   Claude in Chrome while Claude Code drove it. It shows the agent generating the PartyRock flow, editing
   each widget's prompt, switching every step to Claude Sonnet 5 on Amazon Bedrock
   (`bedrock-anthropic.claude-5-0-sonnet-v1-0`), disabling web search, uploading a live GeM bid,
   running the flow and sharing it.
2. **The live app and a real run:** `proof/partyrock-app.jpg`, `proof/partyrock-verdict.jpg`.
3. **Session record:** this repository's git history. Every commit carries a `Co-Authored-By: Claude`
   trailer and a link to the Claude Code session.
4. **AWS tooling set up by the agent:** AWS CLI v2 installed without admin rights; live Bedrock docs
   checked to choose the Messages API endpoint and the IAM action `bedrock-mantle:CreateInference`;
   `scripts/smoke_bedrock.py` written to verify model access as soon as credentials exist.

## When the AWS account is activated

Follow `docs/submission/runbook.md`. The agent then authenticates as IAM user `claude-code-agent`, and
the console-connection proof becomes:

- `aws sts get-caller-identity` → `arn:aws:iam::<account>:user/claude-code-agent`
- `cdk deploy TenderLens` output (SiteUrl, StateMachineArn)
- CloudTrail **Event history** filtered to user `claude-code-agent` (CreateStack, StartExecution, …)
- Step Functions graph of a succeeded `TenderLens-AnalyzeTender` execution
