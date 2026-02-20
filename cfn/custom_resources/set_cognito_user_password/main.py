import logging

import boto3
from crhelper import CfnResource

logger = logging.getLogger(__name__)
helper = CfnResource()

try:
    cognito = boto3.client("cognito-idp")
    secretsmanager = boto3.client("secretsmanager")
except Exception as e:
    helper.init_failure(e)


def _get_secret(secret_arn: str) -> str:
    return secretsmanager.get_secret_value(SecretId=secret_arn)["SecretString"]


@helper.create
@helper.update
def create(event, context):
    logger.info("Got Create")
    user_pool_id = event["ResourceProperties"]["UserPoolId"]
    user_email = event["ResourceProperties"]["UserEmail"]
    user_password_secret_arn = event["ResourceProperties"]["UserPasswordSecretArn"]
    user_password = _get_secret(user_password_secret_arn)
    response = cognito.admin_set_user_password(
        UserPoolId=user_pool_id,
        Username=user_email,
        Password=user_password,
        Permanent=True,
    )


@helper.delete
def delete(event, context):
    pass


def handler(event, context):
    helper(event, context)
