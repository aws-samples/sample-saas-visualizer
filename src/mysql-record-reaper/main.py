import logging
from contextlib import contextmanager
from os import environ

import boto3
import pymysql.cursors

logger = logging.getLogger(__name__)
logger.setLevel("INFO")

MYSQL_HOST = environ["MYSQL_HOST"]
MYSQL_PORT = int(environ["MYSQL_PORT"])
MYSQL_USER = environ["MYSQL_USER"]
TABLE_NAME = environ["TABLE_NAME"]
USERNAMES = environ["USERNAMES"].split(",")

rds = boto3.client("rds")


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


def handler(event, context):
    logger.info("Starting MySQL record reaper")
    with _get_mysql_connection() as connection:
        for user in USERNAMES:
            logger.info(f"Processing {user}")
            database = user
            connection.begin()
            with connection.cursor() as cursor:
                # String interpolation is unavoidable here. SQL injection is mitigated as the table is not user input.
                # nosemgrep: sqlalchemy-execute-raw-query
                cursor.execute(f"USE {database};")
                # nosemgrep: sqlalchemy-execute-raw-query
                cursor.execute(
                    f"DELETE FROM {TABLE_NAME} WHERE Last_Modified >= DATE_SUB(NOW(), INTERVAL 15 MINUTE);"
                )
            logger.info("Committing transaction")
            connection.commit()
