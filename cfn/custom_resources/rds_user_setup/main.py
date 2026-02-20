import json
import logging
import re
from contextlib import contextmanager
from os import environ

import boto3
import pymysql.cursors
from crhelper import CfnResource

logger = logging.getLogger(__name__)
helper = CfnResource()

try:
    INIT_TABLE_NAME = environ["INIT_TABLE_NAME"]
    MYSQL_HOST = environ["MYSQL_HOST"]
    MYSQL_PORT = int(environ["MYSQL_PORT"])
    MYSQL_USER = environ["MYSQL_USER"]
    rds = boto3.client("rds")
except Exception as e:
    helper.init_failure(e)


@contextmanager
def _get_mysql_connection():
    logger.info("Getting DB auth token")
    token = rds.generate_db_auth_token(
        DBHostname=MYSQL_HOST,
        Port=MYSQL_PORT,
        DBUsername=MYSQL_USER,
    )
    logger.info("Connecting to MySQL host")
    connection = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        ssl={"ca": "Amazon RDS"},
        ssl_verify_cert=True,
        user=MYSQL_USER,
        password=token,
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        yield connection
    finally:
        connection.close()


def is_valid_username(username: str) -> bool:
    return bool(re.match(r"^[^\\/?%*:|\"<>.]{1,64}$", username))


@helper.create
def create(event, context):
    logger.info("Got Create")
    user = event["ResourceProperties"]["Username"]
    database = user
    if not is_valid_username(user):
        raise ValueError(f"Invalid username: {user}")
    logger.info(f"Creating user {user}")
    with _get_mysql_connection() as connection:
        logger.info("Beginning transaction")
        connection.begin()
        with connection.cursor() as cursor:
            # For lines with semgrep exclusions, string interpolation is unavoidable here.
            # SQL injection is mitigated by (a) the value is provided in CloudFormation and is not regular user input
            # and (b) the value is checked by is_valid_username().
            logger.info("Creating user")
            cursor.execute(
                "CREATE USER IF NOT EXISTS %s IDENTIFIED WITH AWSAuthenticationPlugin AS 'RDS' REQUIRE SSL;", (user,)
            )
            logger.info("Creating database")
            # nosemgrep: sqlalchemy-execute-raw-query
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database};")
            logger.info("Granting privileges")
            # nosemgrep: sqlalchemy-execute-raw-query
            cursor.execute(
                f"GRANT SELECT, INSERT, UPDATE ON {database}.* TO %s;", (user,)
            )
            cursor.execute("FLUSH PRIVILEGES;")
            logger.info("Creating table")
            # nosemgrep: sqlalchemy-execute-raw-query
            cursor.execute(f"USE {database};")
            # nosemgrep: sqlalchemy-execute-raw-query
            cursor.execute(
                f"CREATE TABLE IF NOT EXISTS {INIT_TABLE_NAME} (ID INT AUTO_INCREMENT PRIMARY KEY, Product VARCHAR(100), Price INT, Order_Date VARCHAR(100), Status ENUM('Ordered', 'Confirmed', 'Dispatched', 'Delivered', 'Returned'), Rating TINYINT, Last_Modified DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP);"
            )
        logger.info("Committing transaction")
        connection.commit()


@helper.delete
def delete(event, context):
    logger.info("Got Delete")
    user = event["ResourceProperties"]["Username"]
    if not is_valid_username(user):
        raise ValueError(f"Invalid username: {user}")
    with _get_mysql_connection() as connection:
        connection.begin()
        with connection.cursor() as cursor:
            logger.info(f"Deleting user: {user}")
            cursor.execute("DROP USER IF EXISTS %s;", (user,))
        connection.commit()


def handler(event, context):
    helper(event, context)
