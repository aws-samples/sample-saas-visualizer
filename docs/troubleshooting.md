# Troubleshooting Guide

This guide covers common issues and their solutions when working with the SaaS Visualizer application.

## AWS Deployment Issues

### SAM Build/Deploy Failures

**Issue**: `sam build` or `sam deploy` fails with permission errors
**Solution**: 
- Verify AWS credentials: `aws sts get-caller-identity`
- Ensure your IAM user/role has CloudFormation, Lambda, and other required permissions
- Check the specific error message for missing permissions

**Issue**: Stack deployment times out
**Solution**:
- Check CloudFormation console for detailed error messages
- Verify resource limits in your AWS account
- Ensure unique resource names if deploying multiple stacks

### Database Connection Issues

**Issue**: Lambda functions can't connect to Aurora database
**Solution**:
- Check VPC configuration in CloudFormation template
- Verify security group rules allow Lambda to Aurora communication
- Ensure database credentials are properly stored in Secrets Manager

## Frontend Issues

### Configuration Problems

**Issue**: Frontend shows "Configuration not loaded" error
**Solution**:
- Ensure `config.js` exists in the `public/` directory
- Download latest config from S3: `aws s3 cp s3://$BUCKET_NAME/config.js public/config.js`
- Check browser console for specific configuration errors

### Authentication Issues

**Issue**: Login fails or redirects incorrectly
**Solution**:
- Verify Cognito User Pool configuration
- Check that user exists and password is correct
- Ensure Cognito domain and callback URLs are configured properly

## Hardware/IoT Issues

### Raspberry Pi Connection

**Issue**: Raspberry Pi can't connect to AWS IoT Core
**Solution**:
- Verify IoT endpoint URL is correct
- Check certificate file paths and permissions
- Ensure IoT policy allows required actions
- Test network connectivity from Pi

**Issue**: LED matrix doesn't display correctly
**Solution**:
- Verify hardware wiring matches [rpi-rgb-led-matrix wiring guide](https://github.com/hzeller/rpi-rgb-led-matrix/blob/cb6ef3adf643882603708962941c68e81c195ee4/wiring.md)
- Check power supply is adequate for your panels
- Ensure you're running the script with `sudo`
- Verify panel configuration in `main.py` matches your hardware

### IoT Message Issues

**Issue**: Messages not appearing on LED display
**Solution**:
- Check IoT Core message logs in AWS console
- Verify topic names match between backend and Pi configuration
- Test message publishing manually using AWS CLI
- Check Pi logs for connection and message reception

## Performance Issues

### Slow API Responses

**Issue**: API calls take too long to respond
**Solution**:
- Check Lambda function logs for performance bottlenecks
- Monitor Aurora database performance metrics
- Consider increasing Lambda memory allocation
- Review database query performance

**Issue**: Frontend loads slowly
**Solution**:
- Check CloudFront distribution configuration
- Optimize asset sizes and compression
- Review network performance from your location
- Consider enabling CloudFront caching

## Development Environment

### Local Development Issues

**Issue**: `npm run dev` fails to start
**Solution**:
- Ensure Node.js version is compatible (v18.x - v22.x)
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Check for port conflicts (default is 5173)

**Issue**: Hot reload not working
**Solution**:
- Restart the development server
- Check file system permissions
- Verify Vite configuration in `vite.config.js`

## Common Error Messages

### "Access Denied" in AWS CLI

**Cause**: Insufficient IAM permissions
**Solution**: Add required permissions to your IAM user/role

### "Certificate validation failed" in IoT

**Cause**: Incorrect certificate configuration
**Solution**: Regenerate certificates and update file paths

### "CORS policy blocked" in browser

**Cause**: Frontend domain not allowed by API
**Solution**: Ensure the `IsDevDeployment` CloudFormation parameter is set to `True`. This parameter sets a more permissive CORS policy which is necessary when using the localhost development server.

### "Database connection timeout"

**Cause**: Network or security group configuration
**Solution**: Check VPC and security group settings

## Getting Help

If you continue to experience issues:

1. Check the [project's GitHub issues](https://github.com/aws-samples/saas-visualiser/issues)
2. Review AWS service documentation for specific services
3. Check AWS CloudWatch logs for detailed error messages
4. Ensure you're using supported versions of all dependencies

## Debugging Tips

- Enable debug logging by setting `IsDevDeployment=True` in deployment
- Use browser developer tools to inspect network requests
- Check CloudWatch logs for Lambda function errors
- Monitor AWS service health dashboards
- Test components individually to isolate issues