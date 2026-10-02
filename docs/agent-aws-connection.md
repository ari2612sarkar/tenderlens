# Proof: coding agent ↔ AWS connection

The hackathon requires *"a coding agent connected to the AWS console, with documented proof of the
connection."* TenderLens was built with **Claude Code** (Anthropic's coding agent, running in the terminal)
connected to the AWS account through the **AWS CLI v2**. It authenticates as a dedicated IAM user,
**`claude-code-agent`**, so every AWS action the agent performed is attributable to it in AWS CloudTrail.

## Evidence

Each item lists how it's produced. Screenshots go in `docs/submission/proof/`.

1. **Identity**: in the Claude Code session the agent runs
   `aws sts get-caller-identity`. The output shows `arn:aws:iam::<account>:user/claude-code-agent`.
   → `proof/1-identity.png`
2. **Infrastructure deployed by the agent**: the agent runs `bash scripts/deploy.sh`
   (`cdk deploy TenderLens`) and the CloudFormation outputs appear (SiteUrl, StateMachineArn, ...).
   → `proof/2-cdk-deploy.png`
3. **CloudTrail attribution**: AWS Console → CloudTrail → **Event history** → filter
   **User name = claude-code-agent**. Events such as `CreateStack`, `CreateFunction`, `CreateStateMachine`,
   `StartExecution`, `PutObject` all come from the agent's credentials.
   → `proof/3-cloudtrail.png`
4. **The pipeline the agent built, running**: Step Functions console → `TenderLens-AnalyzeTender` → a
   succeeded execution's graph view (ExtractText → ExtractionAgents → VerifyGrounding → EvaluateRules →
   Summarize → SaveReport). → `proof/4-step-functions.png`
5. **Session record**: this repository's git history. Every commit carries a `Co-Authored-By: Claude`
   trailer and a link to the Claude Code session.

## What the agent did with AWS access

Before the account was connected:
- Installed the AWS CLI v2 without admin rights (extracted the MSI into the user profile).
- Checked live Bedrock documentation to pick the right endpoint (Messages API on `bedrock-mantle`) and
  the IAM action `bedrock-mantle:CreateInference`.

On deploy day (update this list to match what actually happened):
- Ran `scripts/smoke_bedrock.py` to find which Claude models the account can call and pinned one for the stack.
- Bootstrapped CDK, deployed the `TenderLens` stack, precomputed the sample reports through the live
  Step Functions pipeline, and smoke-tested the public URL.
