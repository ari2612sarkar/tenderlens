#!/usr/bin/env bash
# Build the Lambda asset and the web app, then deploy the CDK stack to us-east-1.
set -euo pipefail
cd "$(dirname "$0")/.."

backend/.venv/Scripts/python scripts/build_lambda.py
(cd frontend && npm run build)
(cd infra && npx --yes aws-cdk@2 deploy TenderLens --require-approval never --outputs-file ../build/outputs.json "$@")
cat build/outputs.json
