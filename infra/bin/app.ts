import { App, Tags } from "aws-cdk-lib";
import { TenderLensStack } from "../lib/stack";

const app = new App();
new TenderLensStack(app, "TenderLens", {
  env: { account: process.env.CDK_DEFAULT_ACCOUNT, region: "us-east-1" },
  description: "TenderLens: grounded government-tender eligibility analysis for Indian MSMEs",
});
Tags.of(app).add("project", "tenderlens");
