import os

import aws_cdk as cdk

from stack import TenderLensStack

app = cdk.App()
TenderLensStack(
    app, "TenderLens",
    env=cdk.Environment(account=os.environ.get("CDK_DEFAULT_ACCOUNT"), region="us-east-1"),
    description="TenderLens: grounded government-tender eligibility analysis for Indian MSMEs",
)
cdk.Tags.of(app).add("project", "tenderlens")
app.synth()
