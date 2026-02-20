import json
from contextlib import contextmanager
from os import environ

import boto3
import pymysql.cursors
from aws_lambda_powertools import Tracer

from datatypes import Item, Tenant

DATA_ACCESS_ROLE_ARN = environ["DATA_ACCESS_ROLE_ARN"]
MYSQL_READ_HOST = environ["MYSQL_READ_HOST"]
MYSQL_READ_PORT = int(environ["MYSQL_READ_PORT"])
MYSQL_TABLE_NAME = environ["MYSQL_TABLE_NAME"]
MYSQL_USERNAME_PREFIX = environ["MYSQL_USERNAME_PREFIX"]
MYSQL_WRITE_HOST = environ["MYSQL_WRITE_HOST"]
MYSQL_WRITE_PORT = int(environ["MYSQL_WRITE_PORT"])
RDS_USER_ARN_PREFIX = environ["RDS_USER_ARN_PREFIX"]

sts = boto3.client("sts")
tracer = Tracer()


@tracer.capture_method
def _get_scoped_session(tenant: Tenant):
    tenant_id = tenant.Name

    session_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "rds-db:connect",
                "Resource": f"{RDS_USER_ARN_PREFIX}{MYSQL_USERNAME_PREFIX}{tenant_id}",
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


@contextmanager
@tracer.capture_method
def _get_mysql_connection(tenant: Tenant, writeable: bool = False):
    mysql_host = MYSQL_WRITE_HOST if writeable else MYSQL_READ_HOST
    mysql_port = MYSQL_WRITE_PORT if writeable else MYSQL_READ_PORT
    mysql_user = f"{MYSQL_USERNAME_PREFIX}{tenant.Name}"
    mysql_database = mysql_user

    session = _get_scoped_session(tenant)
    rds = session.client("rds")

    token = rds.generate_db_auth_token(
        DBHostname=mysql_host,
        Port=mysql_port,
        DBUsername=mysql_user,
    )

    connection = pymysql.connect(
        host=mysql_host,
        port=mysql_port,
        ssl={"ca": "Amazon RDS"},
        ssl_verify_cert=True,
        user=mysql_user,
        password=token,
        db=mysql_database,
        cursorclass=pymysql.cursors.DictCursor,
    )

    try:
        yield connection
    finally:
        connection.close()


@tracer.capture_method
def put_item(tenant: Tenant, item: Item):
    return put_items(tenant, [item])


@tracer.capture_method
def put_items(tenant: Tenant, items: list[Item]):
    table = MYSQL_TABLE_NAME

    with _get_mysql_connection(tenant=tenant, writeable=True) as connection:
        connection.begin()
        with connection.cursor() as cursor:
            cursor.executemany(
                f"INSERT INTO {table} (Product, Price, Order_Date, Status, Rating) VALUES (%s, %s, %s, %s, %s)",
                [
                    (
                        item.Product,
                        item.Price,
                        item.Order_Date,
                        item.Status,
                        item.Rating,
                    )
                    for item in items
                ],
            )
        connection.commit()


@tracer.capture_method
def query_items(tenant: Tenant):
    table = MYSQL_TABLE_NAME

    with _get_mysql_connection(tenant=tenant) as connection:
        with connection.cursor() as cursor:
            # String interpolation is unavoidable here. SQL injection is mitigated as the table is not user input.
            # nosemgrep: sqlalchemy-execute-raw-query
            cursor.execute(
                f"SELECT Product, Price, Order_Date, Status, Rating FROM {table} ORDER BY id DESC LIMIT 100"
            )
            # nosemgrep: sqlalchemy-execute-raw-query
            cursor.execute(
                f"SELECT Product, Price, Order_Date, Status, Rating FROM {table} WHERE Last_Modified >= DATE_SUB(NOW(), INTERVAL 15 MINUTE) ORDER BY id DESC LIMIT 100"
            )
            response = cursor.fetchall()
            return [Item(**item) for item in response]


def create_tenant(tenant: Tenant):
    pass
