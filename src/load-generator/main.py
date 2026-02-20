import random
from os import environ
from time import strftime

import boto3
import requests
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities import parameters
from aws_lambda_powertools.utilities.typing import LambdaContext
from pycognito import Cognito
from ratelimit import limits, sleep_and_retry

logger = Logger()
tracer = Tracer()
cognito = boto3.client("cognito-idp")

API_ENDPOINT = environ["API_ENDPOINT"]
COGNITO_CLIENT_ID = environ["COGNITO_CLIENT_ID"]
COGNITO_USER_POOL_ID = environ["COGNITO_USER_POOL_ID"]
COGNITO_USER_POOL_REGION = environ["COGNITO_USER_POOL_REGION"]
MAX_ITEMS = int(environ["MAX_ITEMS"])
MIN_ITEMS = int(environ["MIN_ITEMS"])
PASSWORD_SECRET_ARN = environ["PASSWORD_SECRET_ARN"]
TIME_FORMAT = "%d/%m/%Y %I:%M %p"
USERNAMES = environ["USERNAMES"].split(",")

_auth_objects = {}


def _get_id_token(username: str):
    logger.info(f"Getting auth for {username}")
    if username not in _auth_objects:
        password = parameters.get_secret(PASSWORD_SECRET_ARN)
        _auth_objects[username] = Cognito(
            client_id=COGNITO_CLIENT_ID,
            user_pool_id=COGNITO_USER_POOL_ID,
            user_pool_region=COGNITO_USER_POOL_REGION,
            username=username,
        )
        _auth_objects[username].authenticate(password=password)
    else:
        _auth_objects[username].check_token()
    return _auth_objects[username].id_token


@sleep_and_retry
@limits(calls=1, period=1)
def make_order_request(username):
    id_token = _get_id_token(username)
    headers = {
        "Authorization": id_token,
    }

    item = {
        "Product": "Load Generator",
        "Price": 100,
        "Order_Date": strftime(TIME_FORMAT),
        "Status": "Ordered",
        "Rating": 5,
    }

    return requests.put(f"{API_ENDPOINT}orders", headers=headers, json=item)


@logger.inject_lambda_context
def handler(event: dict, context: LambdaContext):
    number_of_items = random.randint(MIN_ITEMS, MAX_ITEMS)
    logger.info(f"Making {number_of_items} order requests")
    for _ in range(number_of_items):
        username = random.choice(USERNAMES)
        logger.info(f"Making order request as {username}")
        response = make_order_request(username)
        logger.info(f"Response: {response.status_code} {response.text}")
