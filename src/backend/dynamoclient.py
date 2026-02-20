import json
from dataclasses import asdict
from os import environ
from uuid import uuid4

import boto3

from datatypes import Item, Tenant

DATA_ACCESS_ROLE_ARN = environ["DATA_ACCESS_ROLE_ARN"]
TABLE_NAME = environ["TABLE_NAME"]

sts = boto3.client("sts")


def _get_scoped_session(tenant: Tenant):
    tenant_id = tenant.Name

    session_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "dynamodb:*",
                "Resource": "*",
                "Condition": {
                    "ForAllValues:StringEquals": {
                        "dynamodb:LeadingKeys": [f"{tenant_id}#item"]
                    }
                },
            }
        ],
    }

    sts_response = sts.assume_role(
        RoleArn=DATA_ACCESS_ROLE_ARN,
        RoleSessionName=f"tenant-session-{tenant_id}",
        Policy=json.dumps(session_policy),
    )

    return boto3.Session(
        aws_access_key_id=sts_response["Credentials"]["AccessKeyId"],
        aws_secret_access_key=sts_response["Credentials"]["SecretAccessKey"],
        aws_session_token=sts_response["Credentials"]["SessionToken"],
    )


def _get_table(tenant: Tenant):
    session = _get_scoped_session(tenant)
    dynamodb = session.resource("dynamodb")
    table = dynamodb.Table(TABLE_NAME)
    return table


def put_item(tenant: Tenant, item: Item):
    return put_items(tenant, [item])


def put_items(tenant: Tenant, items: list[Item]):
    tenant_id = tenant.Name
    table = _get_table(tenant)
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(
                Item={
                    "PK": f"{tenant_id}#item",
                    "SK": str(uuid4()),
                    **asdict(item),
                }
            )


def query_items(tenant: Tenant):
    tenant_id = tenant.Name
    table = _get_table(tenant)
    response = table.query(
        KeyConditionExpression="PK = :pk",
        ExpressionAttributeValues={":pk": f"{tenant_id}#item"},
    )
    return [
        Item(**{k: item[k] for k in item.keys() if k not in ("PK", "SK")})
        for item in response["Items"]
    ]


def create_tenant(tenant: Tenant):
    pass
