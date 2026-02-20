# AWS Deployment Guide

This guide covers deploying the SaaS Visualizer application to AWS using the Serverless Application Model (SAM).

> **Important**: Review the [Cost Considerations](#cost-considerations) section before deploying to understand the ongoing AWS service costs.

## Prerequisites

- AWS Serverless Application Model Command Line Interface (AWS SAM CLI) - [Installation guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- Node.js (v18.x - v22.x)
- AWS CLI configured with appropriate credentials
- An AWS account with IAM permissions to create AWS CloudFormation stacks and IAM roles

> **Note**
> You are responsible for the cost of the AWS services used while running this sample deployment. There is no additional cost for using this sample. Services that will incur costs include Amazon Aurora, AWS Lambda, Amazon API Gateway, Amazon S3, Amazon CloudFront, Amazon DynamoDB, Amazon Cognito, and AWS IoT Core. For full details, see the pricing pages for each AWS service. Prices are subject to change.

## Initial Setup

1. Configure your AWS credentials:
   ```
   aws configure
   ```

2. Install Node.js dependencies:
   ```
   npm install
   ```

3. **Configure your email for Cognito users:**
   
   Before building and deploying, edit the `samconfig.toml` file and update the Cognito email parameters:
   
   ```toml
   parameter_overrides=[
     "DBReaderInstanceClass=db.t3.medium",
     "DBWriterInstanceClass=db.t3.medium",
     "IsDevDeployment=True",
     "CognitoUserEmailPrefix=yourname+",
     "CognitoUserEmailSuffix=@example.com",
   ]
   ```
   
   Replace `yourname+` and `@example.com` with your desired email format. This will create 24 demo users with emails like:
   - `yourname+1@example.com`
   - `yourname+2@example.com`
   - ... up to `yourname+24@example.com`

4. Build and deploy the application:
   ```
   sam build
   sam deploy
   ```

   Monitor progress in your terminal or the AWS CloudFormation console.

5. Build and upload the frontend:
   ```
   npm run build
   BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name visualise-saas --query 'Stacks[0].Outputs[?OutputKey==`FrontendBucketName`].OutputValue' --output text)
   aws s3 sync dist/ s3://$BUCKET_NAME
   ```

6. View the stack outputs:
   ```
   aws cloudformation describe-stacks --stack-name visualise-saas --query 'Stacks[0].Outputs'
   ```

   Key outputs include:
   - `ApiGatewayUrl` - Base URL for all API endpoints
   - `FrontendBucketName` - Amazon S3 bucket containing the frontend files
   - `FrontendDistributionUrl` - URL for the deployed frontend via CloudFront
   - `CognitoUserPoolId` and `CognitoUserPoolClientId` - Authentication configuration

## Setting Up the LED Display

- (Optional) To set up the physical LED display with IoT connectivity, see the [Hardware Setup Guide](./hardware-setup.md).
- (Optional) Or, to deploy an emulated LED panel in your browser without physical hardware, see [LED Display Development](./development.md#3-led-display-development).

## Using the Application

Once deployment is complete and you've set up the LED display (emulator or hardware), you're ready to use the application! See the [Usage Guide](./use-sample.md) for:
- How to log in with demo credentials
- Testing the application features
- Watching transactions flow through the architecture on the LED display
- Understanding the multi-tenant visualization

## Viewing Distributed Traces with AWS X-Ray

This application is instrumented with [AWS X-Ray](https://docs.aws.amazon.com/xray/latest/devguide/aws-xray.html) to provide end-to-end visibility into request flows. X-Ray is capturing traces from:

- **Amazon API Gateway** - All API requests and response times
- **AWS Lambda functions** - Backend functions including API handlers and queue consumers
- **Amazon RDS Proxy** - Database connection pooling and SQL query routing to Aurora
- **Amazon SQS** - Message queue operations (shared and siloed queues)
- **AWS SDK calls** - Downstream service interactions

### Accessing the X-Ray Service Map

1. Log into the [AWS Console](https://console.aws.amazon.com/)
2. Navigate to **AWS X-Ray** service (search for "X-Ray" in the services search bar)
3. Click on **Service map** in the left navigation panel
4. Select your desired time range (last 5 minutes, 1 hour, etc.)

The [service map](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-using-xray-maps.html) displays a visual diagram of your application architecture, conceptually similar to the LED matrix visualization. The key differences are that X-Ray also includes latency metrics (average, p50, p90, p99), error rates, request volumes, and throttling indicators for each service. You can click on any service to drill down into [individual traces](https://docs.aws.amazon.com/xray/latest/devguide/xray-concepts.html#xray-concepts-traces) and see detailed timing breakdowns. Also, unlike the LED Solution, X-Ray provides persistent historical data that you can analyze across different time periods.

## Clean Up

> **Critical: Avoid Ongoing Charges**
> This demo application incurs ongoing costs (~$4.53/day or ~$135.95/month) while deployed. To avoid unnecessary charges, delete all resources when you're finished testing.

To remove all deployed resources:

1. Empty the Frontend S3 bucket (including all versions):
   
   Retrieve the relevant S3 Bucket name:
   ```bash
   BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name visualise-saas --query 'Stacks[0].Outputs[?OutputKey==`FrontendBucketName`].OutputValue' --output text)
   ```
   
   Delete all current objects:
   ```bash
   aws s3 rm s3://$BUCKET_NAME --recursive
   ```
   
   Delete all object versions (batch delete):
   ```bash
   aws s3api delete-objects --bucket $BUCKET_NAME \
     --delete "$(aws s3api list-object-versions --bucket $BUCKET_NAME --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}')" \
     2>/dev/null || echo "No versions to delete"
   ```
   
   Delete all delete markers (batch delete):
   ```bash
   aws s3api delete-objects --bucket $BUCKET_NAME \
     --delete "$(aws s3api list-object-versions --bucket $BUCKET_NAME --query '{Objects: DeleteMarkers[].{Key:Key,VersionId:VersionId}}')" \
     2>/dev/null || echo "No delete markers to delete"
   ```
   
   > **Note**: The batch delete commands above handle up to 1000 objects at a time. For buckets with more objects, you can use the AWS Console:
   > 1. Go to the S3 console
   > 2. Find the bucket (check CloudFormation outputs for the name)
   > 3. Select the bucket and click "Empty"
   > 4. Confirm deletion of all objects and versions

2. If you set up IoT certificates, delete them before deleting the stack:
   ```bash
   uv run scripts/setup_iot_certificates.py delete --delete-files --output-dir ./iot-certificates
   ```

3. Delete the CloudFormation stack:
   ```bash
   sam delete
   ```
   
   Or using AWS CLI:
   ```bash
   aws cloudformation delete-stack --stack-name visualise-saas
   ```

4. Wait for stack deletion to complete and verify all nested stacks are deleted:
   
   Monitor deletion status:
   ```bash
   aws cloudformation describe-stacks --stack-name visualise-saas --query 'Stacks[0].StackStatus'
   ```
   
   Check for any remaining nested stacks:
   ```bash
   aws cloudformation list-stacks --stack-status-filter DELETE_FAILED --query 'StackSummaries[?contains(StackName, `visualise-saas`)].StackName'
   ```

5. Clean up SAM deployment artifacts for this project only:
   ```bash
   SAM_BUCKET=$(aws cloudformation describe-stacks --stack-name aws-sam-cli-managed-default --query 'Stacks[0].Outputs[?OutputKey==`SourceBucket`].OutputValue' --output text 2>/dev/null)
   
   if [ ! -z "$SAM_BUCKET" ]; then
     echo "Cleaning up SAM artifacts for visualise-saas from: $SAM_BUCKET"
     aws s3 rm s3://$SAM_BUCKET/visualise-saas/ --recursive
     echo "SAM artifacts deleted. Other projects in the bucket are unaffected."
   else
     echo "SAM bucket not found or already deleted."
   fi
   ```
   
   > **Important**: This only deletes the `visualise-saas/` prefix from the SAM bucket. The SAM bucket itself (`aws-sam-cli-managed-default`) is shared across all your SAM projects and should NOT be deleted.

6. Clean up local SAM build artifacts and dependencies:
   ```bash
   rm -rf .aws-sam/
   rm -rf dist/
   rm -rf node_modules/
   rm -rf venv/
   
   echo "✓ Local build artifacts and dependencies removed"
   ```
   
   > **Note**: This removes:
   > - `.aws-sam/` - SAM build cache and packaged artifacts
   > - `dist/` - Frontend build output
   > - `node_modules/` - Node.js dependencies (can be reinstalled with `npm install`)
   > - `venv/` - Python virtual environment (if you created one)
   > - Optionally remove `package-lock.json` if you want a completely clean slate
   > 
   > These will be recreated on next deployment.

7. Verify complete cleanup:
   
   Check CloudFormation stacks (should return empty or no results):
   ```bash
   aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE --query 'StackSummaries[?contains(StackName, `visualise-saas`)].StackName'
   ```
   
   Verify SAM artifacts are gone from S3:
   ```bash
   SAM_BUCKET=$(aws cloudformation describe-stacks --stack-name aws-sam-cli-managed-default --query 'Stacks[0].Outputs[?OutputKey==`SourceBucket`].OutputValue' --output text 2>/dev/null)
   if [ ! -z "$SAM_BUCKET" ]; then
     echo "Checking for remaining visualise-saas artifacts..."
     if aws s3 ls s3://$SAM_BUCKET/visualise-saas/ 2>&1 | grep -q "NoSuchKey\|does not exist"; then
       echo "✓ All visualise-saas artifacts removed from S3"
     elif [ -z "$(aws s3 ls s3://$SAM_BUCKET/visualise-saas/ 2>/dev/null)" ]; then
       echo "✓ All visualise-saas artifacts removed from S3"
     else
       echo "⚠ Some artifacts may remain in S3"
     fi
   fi
   ```
   
   Verify local artifacts are gone:
   ```bash
   REMAINING=""
   [ -d ".aws-sam" ] && REMAINING="$REMAINING .aws-sam/"
   [ -d "dist" ] && REMAINING="$REMAINING dist/"
   [ -d "node_modules" ] && REMAINING="$REMAINING node_modules/"
   [ -d "venv" ] && REMAINING="$REMAINING venv/"
   
   if [ -z "$REMAINING" ]; then
     echo "✓ All local build artifacts and dependencies removed"
   else
     echo "⚠ Some local artifacts remain:$REMAINING"
   fi
   ```

> **Tip**: Set a billing alarm in AWS to notify you if costs exceed expected amounts.

> **Important**: If stack deletion fails, check the CloudFormation console for error messages. Common issues include:
> - S3 bucket not empty (return to step 1)
> - RDS snapshots preventing deletion (delete manually)
> - ENIs (Elastic Network Interfaces) still attached (wait a few minutes and retry)

## Cost Considerations

> **Important Cost Disclaimer**
> You are responsible for the cost of the AWS services used while running this sample deployment. This is a demonstration application and will incur ongoing costs while deployed. The costs below are estimates based on the default configuration in `samconfig.toml` and typical usage patterns. Actual costs may vary based on your configuration changes, usage patterns, AWS region, and current pricing. This list is non-exhaustive in terms of services and features - additional AWS services or features you enable may incur extra costs. Several services use AWS Free Tier allowances - costs will increase if you exceed free tier limits or if your AWS account is no longer eligible for free tier benefits.

### Estimated Runtime Costs

The following table provides estimated costs for running this application in the **us-east-1** region. **These are estimates only** - actual prices may vary. Please verify current pricing on the AWS pricing pages linked in the Service column before deploying.

**Note:** Several services below use AWS Free Tier allowances (marked as "free tier"). If you exceed these limits or your account is no longer eligible for free tier, additional charges will apply.

| Service | Component | Quantity/Usage | Unit Price (us-east-1) | Daily Cost | Monthly Cost |
|---------|-----------|----------------|------------------------|------------|--------------|
| [Amazon Aurora](https://aws.amazon.com/rds/aurora/pricing/) | Writer Instance (db.t3.medium) | 1 instance, 24 hours | ~$0.082/hour | ~$1.97 | ~$59.13 |
| [Amazon Aurora](https://aws.amazon.com/rds/aurora/pricing/) | Reader Instance (db.t3.medium) | 1 instance, 24 hours | ~$0.082/hour | ~$1.97 | ~$59.13 |
| [Amazon Aurora](https://aws.amazon.com/rds/aurora/pricing/) | Storage | 10 GB (estimated) | ~$0.10/GB-month | ~$0.03 | ~$1.00 |
| [Amazon Aurora](https://aws.amazon.com/rds/aurora/pricing/) | I/O Operations | 1M requests/day | ~$0.20/1M requests | ~$0.20 | ~$6.00 |
| [AWS Lambda](https://aws.amazon.com/lambda/pricing/) | API Functions | 10K requests/day, 256MB, 15s timeout | ~$0.0000041667/second (256MB) | ~$0.14 | ~$4.17 |
| [Amazon API Gateway](https://aws.amazon.com/api-gateway/pricing/) | REST API Requests | 10K requests/day | ~$3.50/million requests | ~$0.04 | ~$1.05 |
| [Amazon S3](https://aws.amazon.com/s3/pricing/) | Frontend Hosting | 1 GB storage, 1K requests/day | ~$0.023/GB-month + requests | ~$0.01 | ~$0.25 |
| [Amazon CloudFront](https://aws.amazon.com/cloudfront/pricing/) | CDN Distribution | 1 GB data transfer/day (~30GB/month) | Free tier: 100GB/month, then ~$0.085/GB | ~$0.00 | ~$0.00 (free tier) |
| [Amazon Cognito](https://aws.amazon.com/cognito/pricing/) | User Pool | 50 MAUs | Free for first 10K MAUs/month | ~$0.00 | ~$0.00 (free tier) |
| [AWS IoT Core](https://aws.amazon.com/iot-core/pricing/) | MQTT Messages | 10K messages/day | ~$1.00/million messages | ~$0.01 | ~$0.30 |
| [Amazon DynamoDB](https://aws.amazon.com/dynamodb/pricing/) | On-Demand Tables | 1K reads, 1K writes/day | ~$0.125/million reads, ~$0.625/million writes | ~$0.00 | ~$0.02 |
| [Amazon SQS](https://aws.amazon.com/sqs/pricing/) | Standard Queues | 10K requests/day | ~$0.40/million requests | ~$0.00 | ~$0.00 (free tier) |
| [AWS Secrets Manager](https://aws.amazon.com/secrets-manager/pricing/) | Database Credentials | 1 secret | ~$0.40/secret/month | ~$0.01 | ~$0.40 |
| [Amazon CloudWatch](https://aws.amazon.com/cloudwatch/pricing/) | Logs & Metrics | 1 GB logs, custom metrics | ~$0.50/GB ingested + metrics | ~$0.15 | ~$4.50 |
| **TOTAL** | | | | **~$4.53/day** | **~$135.95/month** |

### Cost Optimization Tips

- **Destroy resources when not in use**: This is a demo application. Delete the CloudFormation stacks when you're done testing to avoid ongoing charges.
- **Use smaller instance types**: For testing, you can use db.t3.small instances instead of db.t3.medium to reduce Aurora costs by ~50%.
- **Disable load generator**: Set `EnableLoadGenerator=False` in deployment parameters to reduce Lambda invocations and database load.
- **CloudFront free tier**: With typical demo usage (~30GB/month), CloudFront stays within the free tier (100GB/month). For higher traffic, consider CloudFront's new flat-rate pricing plans starting at $15/month for predictable costs.
- **Monitor usage**: Use AWS Cost Explorer to track actual spending and identify optimization opportunities.
- **Free tier benefits**: New AWS accounts receive free tier benefits for many services, which can significantly reduce costs for the first 12 months.

### Important Reminders

⚠️ **Remember to clean up resources after testing!** See the [Clean Up](#clean-up) section above.

⚠️ **Costs vary by region**: The estimates above are for us-east-1. Pricing may differ in other AWS regions.

⚠️ **Usage-based pricing**: Actual costs depend on your usage patterns.

## Next Steps

After completing the AWS deployment, you can proceed to the [Development Guide](./development.md) to set up local development and learn how to make changes to the application.