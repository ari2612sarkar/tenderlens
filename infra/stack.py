"""TenderLens on AWS: CloudFront + S3 site, HTTP API + Lambda, Step Functions agent pipeline, DynamoDB."""

from pathlib import Path

from aws_cdk import (
    CfnOutput, Duration, Fn, RemovalPolicy, Stack,
    aws_apigatewayv2 as apigw,
    aws_apigatewayv2_integrations as integrations,
    aws_cloudfront as cf,
    aws_cloudfront_origins as origins,
    aws_dynamodb as ddb,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
from constructs import Construct

ROOT = Path(__file__).resolve().parents[1]
TRANSIENT_LLM_ERRORS = ["RateLimitError", "InternalServerError", "APIConnectionError", "APITimeoutError", "LLMError"]


class TenderLensStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        model = self.node.try_get_context("model") or "anthropic.claude-opus-5-5"
        fallback_model = self.node.try_get_context("fallback_model") or "anthropic.claude-opus-4-8"

        # --- storage ------------------------------------------------------------------
        data = s3.Bucket(
            self, "Data",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL, enforce_ssl=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            cors=[s3.CorsRule(allowed_methods=[s3.HttpMethods.PUT, s3.HttpMethods.GET],
                              allowed_origins=["*"], allowed_headers=["*"], max_age=3000)],
            lifecycle_rules=[s3.LifecycleRule(prefix="uploads/", expiration=Duration.days(30))],
            removal_policy=RemovalPolicy.DESTROY, auto_delete_objects=True,
        )
        table_props = dict(partition_key=ddb.Attribute(name="id", type=ddb.AttributeType.STRING),
                           billing_mode=ddb.BillingMode.PAY_PER_REQUEST, time_to_live_attribute="expires_at",
                           removal_policy=RemovalPolicy.DESTROY)
        analyses = ddb.Table(self, "Analyses", **table_props)
        profiles = ddb.Table(self, "Profiles", **table_props)

        # --- lambdas --------------------------------------------------------------------
        code = lambda_.Code.from_asset(str(ROOT / "build" / "lambda"))
        env = {"TL_BUCKET": data.bucket_name, "TL_ANALYSES_TABLE": analyses.table_name,
               "TL_PROFILES_TABLE": profiles.table_name, "TL_MODEL": model, "TL_FALLBACK_MODEL": fallback_model}

        def fn(name: str, handler: str, timeout_s: int, memory: int = 512) -> lambda_.Function:
            f = lambda_.Function(
                self, name, runtime=lambda_.Runtime.PYTHON_3_12, architecture=lambda_.Architecture.X86_64,
                handler=handler, code=code, timeout=Duration.seconds(timeout_s), memory_size=memory,
                environment=env, tracing=lambda_.Tracing.ACTIVE,
            )
            data.grant_read_write(f)
            analyses.grant_read_write_data(f)
            profiles.grant_read_data(f)
            return f

        bedrock = iam.PolicyStatement(
            actions=["bedrock-mantle:CreateInference", "bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
            resources=["*"],
        )
        extract_fn = fn("ExtractFn", "handlers.steps.extract", 180, 1536)
        extract_fn.add_to_role_policy(iam.PolicyStatement(actions=["textract:DetectDocumentText"], resources=["*"]))
        eligibility_fn = fn("EligibilityFn", "handlers.steps.eligibility", 900)
        risks_fn = fn("RisksFn", "handlers.steps.risks", 900)
        summarize_fn = fn("SummarizeFn", "handlers.steps.summarize_step", 300)
        for f in (eligibility_fn, risks_fn, summarize_fn):
            f.add_to_role_policy(bedrock)
        verify_fn = fn("VerifyFn", "handlers.steps.verify_step", 60, 1024)
        evaluate_fn = fn("EvaluateFn", "handlers.steps.evaluate_step", 60)
        save_fn = fn("SaveFn", "handlers.steps.save", 60)
        fail_fn = fn("FailFn", "handlers.steps.fail", 30)

        # --- state machine ------------------------------------------------------------------
        failed = tasks.LambdaInvoke(self, "MarkFailed", lambda_function=fail_fn, payload_response_only=True,
                                    result_path="$.failed").next(sfn.Fail(self, "AnalysisFailed"))

        def step(name: str, f: lambda_.Function, result_path: str | None, llm: bool = False) -> tasks.LambdaInvoke:
            t = tasks.LambdaInvoke(self, name, lambda_function=f, payload_response_only=True,
                                   result_path=result_path, retry_on_service_exceptions=True)
            if llm:
                t.add_retry(errors=TRANSIENT_LLM_ERRORS, interval=Duration.seconds(20), max_attempts=2,
                            backoff_rate=2)
            return t

        agents = sfn.Parallel(self, "ExtractionAgents", result_path="$.agents")
        agents.branch(step("EligibilityAgent", eligibility_fn, None, llm=True))
        agents.branch(step("RiskAgent", risks_fn, None, llm=True))
        agents.add_catch(failed, result_path="$.error")

        chain_steps = [
            step("ExtractText", extract_fn, "$.extract"),
            agents,
            step("VerifyGrounding", verify_fn, "$.grounding"),
            step("EvaluateRules", evaluate_fn, "$.evaluation"),
            step("Summarize", summarize_fn, "$.summary", llm=True),
            step("SaveReport", save_fn, "$.saved"),
        ]
        for s in chain_steps:
            if isinstance(s, tasks.LambdaInvoke):
                s.add_catch(failed, result_path="$.error")
        definition = chain_steps[0]
        chain = sfn.Chain.start(definition)
        for s in chain_steps[1:]:
            chain = chain.next(s)
        chain = chain.next(sfn.Succeed(self, "ReportReady"))

        machine = sfn.StateMachine(
            self, "AnalyzeTender", state_machine_name="TenderLens-AnalyzeTender",
            definition_body=sfn.DefinitionBody.from_chainable(chain), timeout=Duration.minutes(30),
            tracing_enabled=True,
        )

        # --- api ------------------------------------------------------------------------------
        api_fn = fn("ApiFn", "handlers.api.handler", 29, 1024)
        api_fn.add_environment("TL_STATE_MACHINE_ARN", machine.state_machine_arn)
        machine.grant_start_execution(api_fn)
        profiles.grant_read_write_data(api_fn)
        http_api = apigw.HttpApi(self, "HttpApi",
                                 default_integration=integrations.HttpLambdaIntegration("ApiIntegration", api_fn))
        http_api.default_stage.node.default_child.add_property_override(
            "DefaultRouteSettings", {"ThrottlingBurstLimit": 50, "ThrottlingRateLimit": 20})

        # --- website ------------------------------------------------------------------------
        site = s3.Bucket(self, "Site", block_public_access=s3.BlockPublicAccess.BLOCK_ALL, enforce_ssl=True,
                         removal_policy=RemovalPolicy.DESTROY, auto_delete_objects=True)
        spa_rewrite = cf.Function(
            self, "SpaRewrite", runtime=cf.FunctionRuntime.JS_2_0,
            code=cf.FunctionCode.from_inline(
                "function handler(event){var r=event.request;if(r.uri.indexOf('.')===-1){r.uri='/index.html';}return r;}"),
        )
        api_domain = Fn.select(2, Fn.split("/", http_api.api_endpoint))
        distribution = cf.Distribution(
            self, "Cdn", default_root_object="index.html", comment="TenderLens",
            default_behavior=cf.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(site),
                viewer_protocol_policy=cf.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cf.CachePolicy.CACHING_OPTIMIZED,
                function_associations=[cf.FunctionAssociation(function=spa_rewrite,
                                                               event_type=cf.FunctionEventType.VIEWER_REQUEST)],
            ),
            additional_behaviors={
                "/api/*": cf.BehaviorOptions(
                    origin=origins.HttpOrigin(api_domain, protocol_policy=cf.OriginProtocolPolicy.HTTPS_ONLY),
                    viewer_protocol_policy=cf.ViewerProtocolPolicy.HTTPS_ONLY,
                    allowed_methods=cf.AllowedMethods.ALLOW_ALL,
                    cache_policy=cf.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=cf.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
                ),
            },
        )
        s3deploy.BucketDeployment(self, "DeploySite", sources=[s3deploy.Source.asset(str(ROOT / "frontend" / "dist"))],
                                  destination_bucket=site, distribution=distribution, distribution_paths=["/*"])
        s3deploy.BucketDeployment(self, "DeploySamples",
                                  sources=[s3deploy.Source.asset(str(ROOT / "data" / "samples"), exclude=["*.json"])],
                                  destination_bucket=data, destination_key_prefix="samples/", prune=False)

        CfnOutput(self, "SiteUrl", value=f"https://{distribution.distribution_domain_name}")
        CfnOutput(self, "ApiUrl", value=http_api.api_endpoint)
        CfnOutput(self, "StateMachineArn", value=machine.state_machine_arn)
        CfnOutput(self, "DataBucket", value=data.bucket_name)
        CfnOutput(self, "AnalysesTable", value=analyses.table_name)
