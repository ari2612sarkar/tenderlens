// TenderLens on AWS: CloudFront + S3 site, HTTP API + Lambda, Step Functions agent pipeline, DynamoDB.
import * as path from "node:path";
import {
  CfnOutput, Duration, Fn, RemovalPolicy, Stack, StackProps,
  aws_apigatewayv2 as apigw,
  aws_apigatewayv2_integrations as integrations,
  aws_cloudfront as cf,
  aws_cloudfront_origins as origins,
  aws_dynamodb as ddb,
  aws_iam as iam,
  aws_lambda as lambda,
  aws_s3 as s3,
  aws_s3_deployment as s3deploy,
  aws_stepfunctions as sfn,
  aws_stepfunctions_tasks as tasks,
} from "aws-cdk-lib";
import { Construct } from "constructs";

const ROOT = path.resolve(__dirname, "..", "..");
const TRANSIENT_LLM_ERRORS = ["RateLimitError", "InternalServerError", "APIConnectionError", "APITimeoutError", "LLMError"];

export class TenderLensStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);
    const model = this.node.tryGetContext("model") ?? "anthropic.claude-opus-5-5";
    const fallbackModel = this.node.tryGetContext("fallback_model") ?? "anthropic.claude-opus-4-8";

    // --- storage ------------------------------------------------------------------------
    const data = new s3.Bucket(this, "Data", {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      cors: [{ allowedMethods: [s3.HttpMethods.PUT, s3.HttpMethods.GET], allowedOrigins: ["*"], allowedHeaders: ["*"], maxAge: 3000 }],
      lifecycleRules: [{ prefix: "uploads/", expiration: Duration.days(30) }],
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });
    const tableProps: ddb.TableProps = {
      partitionKey: { name: "id", type: ddb.AttributeType.STRING },
      billingMode: ddb.BillingMode.PAY_PER_REQUEST,
      timeToLiveAttribute: "expires_at",
      removalPolicy: RemovalPolicy.DESTROY,
    };
    const analyses = new ddb.Table(this, "Analyses", tableProps);
    const profiles = new ddb.Table(this, "Profiles", tableProps);

    // --- lambdas ------------------------------------------------------------------------
    const code = lambda.Code.fromAsset(path.join(ROOT, "build", "lambda"));
    const environment = {
      TL_BUCKET: data.bucketName,
      TL_ANALYSES_TABLE: analyses.tableName,
      TL_PROFILES_TABLE: profiles.tableName,
      TL_MODEL: model,
      TL_FALLBACK_MODEL: fallbackModel,
    };
    const fn = (name: string, handler: string, timeoutS: number, memory = 512) => {
      const f = new lambda.Function(this, name, {
        runtime: lambda.Runtime.PYTHON_3_12,
        architecture: lambda.Architecture.X86_64,
        handler,
        code,
        timeout: Duration.seconds(timeoutS),
        memorySize: memory,
        environment,
        tracing: lambda.Tracing.ACTIVE,
      });
      data.grantReadWrite(f);
      analyses.grantReadWriteData(f);
      profiles.grantReadData(f);
      return f;
    };

    const bedrock = new iam.PolicyStatement({
      actions: ["bedrock-mantle:CreateInference", "bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
      resources: ["*"],
    });
    const extractFn = fn("ExtractFn", "handlers.steps.extract", 180, 1536);
    extractFn.addToRolePolicy(new iam.PolicyStatement({ actions: ["textract:DetectDocumentText"], resources: ["*"] }));
    const eligibilityFn = fn("EligibilityFn", "handlers.steps.eligibility", 900);
    const risksFn = fn("RisksFn", "handlers.steps.risks", 900);
    const summarizeFn = fn("SummarizeFn", "handlers.steps.summarize_step", 300);
    for (const f of [eligibilityFn, risksFn, summarizeFn]) f.addToRolePolicy(bedrock);
    const verifyFn = fn("VerifyFn", "handlers.steps.verify_step", 60, 1024);
    const evaluateFn = fn("EvaluateFn", "handlers.steps.evaluate_step", 60);
    const saveFn = fn("SaveFn", "handlers.steps.save", 60);
    const failFn = fn("FailFn", "handlers.steps.fail", 30);

    // --- state machine ------------------------------------------------------------------
    const failed = new tasks.LambdaInvoke(this, "MarkFailed", {
      lambdaFunction: failFn, payloadResponseOnly: true, resultPath: "$.failed",
    }).next(new sfn.Fail(this, "AnalysisFailed"));

    const step = (name: string, f: lambda.IFunction, resultPath?: string, llm = false) => {
      const t = new tasks.LambdaInvoke(this, name, {
        lambdaFunction: f, payloadResponseOnly: true, resultPath, retryOnServiceExceptions: true,
      });
      if (llm) t.addRetry({ errors: TRANSIENT_LLM_ERRORS, interval: Duration.seconds(20), maxAttempts: 2, backoffRate: 2 });
      return t;
    };

    const agents = new sfn.Parallel(this, "ExtractionAgents", { resultPath: "$.agents" })
      .branch(step("EligibilityAgent", eligibilityFn, undefined, true))
      .branch(step("RiskAgent", risksFn, undefined, true))
      .addCatch(failed, { resultPath: "$.error" });

    const catchAll = (t: tasks.LambdaInvoke) => t.addCatch(failed, { resultPath: "$.error" });
    const definition = sfn.Chain.start(catchAll(step("ExtractText", extractFn, "$.extract")))
      .next(agents)
      .next(catchAll(step("VerifyGrounding", verifyFn, "$.grounding")))
      .next(catchAll(step("EvaluateRules", evaluateFn, "$.evaluation")))
      .next(catchAll(step("Summarize", summarizeFn, "$.summary", true)))
      .next(catchAll(step("SaveReport", saveFn, "$.saved")))
      .next(new sfn.Succeed(this, "ReportReady"));

    const machine = new sfn.StateMachine(this, "AnalyzeTender", {
      stateMachineName: "TenderLens-AnalyzeTender",
      definitionBody: sfn.DefinitionBody.fromChainable(definition),
      timeout: Duration.minutes(30),
      tracingEnabled: true,
    });

    // --- api ------------------------------------------------------------------------------
    const apiFn = fn("ApiFn", "handlers.api.handler", 29, 1024);
    apiFn.addEnvironment("TL_STATE_MACHINE_ARN", machine.stateMachineArn);
    machine.grantStartExecution(apiFn);
    profiles.grantReadWriteData(apiFn);
    const httpApi = new apigw.HttpApi(this, "HttpApi", {
      defaultIntegration: new integrations.HttpLambdaIntegration("ApiIntegration", apiFn),
    });
    (httpApi.defaultStage!.node.defaultChild as apigw.CfnStage).addPropertyOverride("DefaultRouteSettings", {
      ThrottlingBurstLimit: 50,
      ThrottlingRateLimit: 20,
    });

    // --- website ------------------------------------------------------------------------
    const site = new s3.Bucket(this, "Site", {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });
    const spaRewrite = new cf.Function(this, "SpaRewrite", {
      runtime: cf.FunctionRuntime.JS_2_0,
      code: cf.FunctionCode.fromInline(
        "function handler(event){var r=event.request;if(r.uri.indexOf('.')===-1){r.uri='/index.html';}return r;}",
      ),
    });
    const apiDomain = Fn.select(2, Fn.split("/", httpApi.apiEndpoint));
    const distribution = new cf.Distribution(this, "Cdn", {
      comment: "TenderLens",
      defaultRootObject: "index.html",
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessControl(site),
        viewerProtocolPolicy: cf.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        cachePolicy: cf.CachePolicy.CACHING_OPTIMIZED,
        functionAssociations: [{ function: spaRewrite, eventType: cf.FunctionEventType.VIEWER_REQUEST }],
      },
      additionalBehaviors: {
        "/api/*": {
          origin: new origins.HttpOrigin(apiDomain, { protocolPolicy: cf.OriginProtocolPolicy.HTTPS_ONLY }),
          viewerProtocolPolicy: cf.ViewerProtocolPolicy.HTTPS_ONLY,
          allowedMethods: cf.AllowedMethods.ALLOW_ALL,
          cachePolicy: cf.CachePolicy.CACHING_DISABLED,
          originRequestPolicy: cf.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
        },
      },
    });
    new s3deploy.BucketDeployment(this, "DeploySite", {
      sources: [s3deploy.Source.asset(path.join(ROOT, "frontend", "dist"))],
      destinationBucket: site,
      distribution,
      distributionPaths: ["/*"],
    });
    new s3deploy.BucketDeployment(this, "DeploySamples", {
      sources: [s3deploy.Source.asset(path.join(ROOT, "data", "samples"), { exclude: ["*.json"] })],
      destinationBucket: data,
      destinationKeyPrefix: "samples/",
      prune: false,
    });

    new CfnOutput(this, "SiteUrl", { value: `https://${distribution.distributionDomainName}` });
    new CfnOutput(this, "ApiUrl", { value: httpApi.apiEndpoint });
    new CfnOutput(this, "StateMachineArn", { value: machine.stateMachineArn });
    new CfnOutput(this, "DataBucket", { value: data.bucketName });
    new CfnOutput(this, "AnalysesTable", { value: analyses.tableName });
  }
}
