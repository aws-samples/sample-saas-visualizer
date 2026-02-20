import logging
import os

import boto3
from crhelper import CfnResource

helper = CfnResource(json_logging=False, log_level="DEBUG", boto_level="CRITICAL")

logger = logging.getLogger()
logger.setLevel(os.getenv("LogLevel", logging.INFO))
s3 = boto3.client("s3")


@helper.create
@helper.update
def create(event, context):
    acl, bucket, object, content_type, content = (
        event["ResourceProperties"][k]
        for k in (
            "ACL",
            "BucketName",
            "ObjectKey",
            "ContentType",
            "Content",
        )
    )
    logger.info(f"Creating {object} in {bucket}")
    s3.put_object(
        ACL=acl,
        Bucket=bucket,
        Key=object,
        ContentType=content_type,
        Body=content.encode(),
    )


@helper.delete
def delete(event, context):
    return None


def handler(event, context):
    helper(event, context)
