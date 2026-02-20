import json
import random
import time
from dataclasses import asdict
from itertools import batched
from os import getenv
from uuid import uuid4

import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import (
    APIGatewayRestResolver,
    CORSConfig,
    Response,
)
from aws_lambda_powertools.event_handler.middlewares import NextMiddleware
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.batch import (
    SqsFifoPartialProcessor,
    process_partial_response,
)
from aws_lambda_powertools.utilities.data_classes.sqs_event import SQSRecord
from aws_lambda_powertools.utilities.typing.lambda_context import LambdaContext

import constants
from datatypes import REQUEST_STAGE, Item, Tenant
from mysqlclient import put_item, put_items, query_items

CORS_ALLOW_ORIGIN = getenv("CORS_ALLOW_ORIGIN")
IOT_SQS_STAGE_TYPE = getenv("IOT_SQS_STAGE_TYPE")
IOT_TOPIC = getenv("IOT_TOPIC")
SHARED_QUEUE_URL = getenv("SHARED_QUEUE_URL")
SILOED_QUEUE_URL = getenv("SILOED_QUEUE_URL")

tracer = Tracer()
logger = Logger()
cors_config = CORSConfig(allow_origin=CORS_ALLOW_ORIGIN)
app = APIGatewayRestResolver(enable_validation=True, cors=cors_config)
iot = boto3.client("iot-data")
processor = SqsFifoPartialProcessor()
sqs = boto3.resource("sqs")


def inject_tenant(
    app: APIGatewayRestResolver, next_middleware: NextMiddleware
) -> Response:
    app.append_context(
        tenant=Tenant(
            Name=app.current_event.request_context.authorizer.claims.get(
                "custom:tenantName"
            ),
            Color=app.current_event.request_context.authorizer.claims.get(
                "custom:tenantColor"
            ),
        )
    )
    result = next_middleware(app)
    return result


def inject_iot_transaction_id(
    app: APIGatewayRestResolver, next_middleware: NextMiddleware
) -> Response:
    transaction_id = app.current_event.request_context.request_id
    app.append_context(iot_transaction_id=transaction_id)
    result = next_middleware(app)
    return result


def random_date():
    start = "1/1/2024 1:30 PM"
    end = "10/4/2025 11:59 PM"
    prop = random.random()
    time_format = "%d/%m/%Y %I:%M %p"
    stime = time.mktime(time.strptime(start, time_format))
    etime = time.mktime(time.strptime(end, time_format))
    ptime = stime + prop * (etime - stime)
    return time.strftime(time_format, time.localtime(ptime))


def random_item():
    return Item(
        Product=random.choice(constants.PRODUCTS),
        Price=random.randint(100, 999),
        Order_Date=random_date(),
        Status=random.choice(constants.STATUSES),
        Rating=random.randint(2, 5),
    )


@tracer.capture_method
def emit_iot_event(
    tenant: Tenant, position: list[REQUEST_STAGE], transaction_id: str
) -> None:
    iot.publish(
        topic=IOT_TOPIC,
        payload=json.dumps(
            {
                "TransactionId": transaction_id,
                "timestamp": time.time(),
                "tenantid": tenant.Name,
                "tenantcolor": tenant.Color,
                "position": position,
            }
        ),
    )


@tracer.capture_method
def enqueue_create_items(
    tenant: Tenant, items: list[Item], queue_url: str = SHARED_QUEUE_URL
) -> None:
    max_messages = 10  # Maximum number of messages per https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sqs/queue/send_messages.html
    iot_transaction_id = app.context["iot_transaction_id"]
    logger.info(f"Enqueueing {len(items)} items to queue {queue_url}")
    queue = sqs.Queue(queue_url)
    for batch in batched(items, max_messages):
        entries = [
            {
                "Id": str(uuid4()),
                "MessageBody": json.dumps(
                    {
                        "iot_transaction_id": iot_transaction_id,
                        "item": asdict(p),
                        "tenant": asdict(tenant),
                    }
                ),
                "MessageGroupId": str(tenant.Name),
            }
            for p in batch
        ]
        queue.send_messages(Entries=entries)


@tracer.capture_method
def handle_queue_message(record: SQSRecord):
    iot_transaction_id = record.json_body["iot_transaction_id"]
    item = Item(**record.json_body["item"])
    tenant = Tenant(**record.json_body["tenant"])
    sqs_stage = (
        REQUEST_STAGE.SILOED_SQS
        if IOT_SQS_STAGE_TYPE == "siloed"
        else REQUEST_STAGE.SHARED_SQS
    )
    emit_iot_event(
        position=[REQUEST_STAGE.LAMBDA],
        tenant=tenant,
        transaction_id=iot_transaction_id,
    )
    put_item(tenant, item)
    emit_iot_event(
        position=[
            REQUEST_STAGE.RDS_PROXY,
            REQUEST_STAGE.RDS,
            REQUEST_STAGE.RDS_PROXY,
            REQUEST_STAGE.LAMBDA,
            REQUEST_STAGE.AMPLIFY,
        ],
        tenant=tenant,
        transaction_id=iot_transaction_id,
    )


@app.put(
    "/orders",
    middlewares=[
        inject_tenant,
        inject_iot_transaction_id,
    ],
)
@tracer.capture_method
def create_order_shared(item: Item):
    tenant = app.context["tenant"]
    emit_iot_event(
        position=[
            REQUEST_STAGE.AMPLIFY,
            REQUEST_STAGE.API_GATEWAY,
            REQUEST_STAGE.SHARED_SQS,
        ],
        tenant=tenant,
        transaction_id=app.context["iot_transaction_id"],
    )
    enqueue_create_items(
        tenant=tenant,
        items=[item],
        queue_url=SHARED_QUEUE_URL,
    )
    return item


@app.put(
    "/orders_siloed",
    middlewares=[
        inject_tenant,
        inject_iot_transaction_id,
    ],
)
@tracer.capture_method
def create_order_siloed(item: Item):
    tenant = app.context["tenant"]
    emit_iot_event(
        position=[
            REQUEST_STAGE.AMPLIFY,
            REQUEST_STAGE.API_GATEWAY,
            REQUEST_STAGE.SILOED_SQS,
        ],
        tenant=tenant,
        transaction_id=app.context["iot_transaction_id"],
    )
    enqueue_create_items(
        tenant=tenant,
        items=[item],
        queue_url=SILOED_QUEUE_URL,
    )
    return item


@app.put(
    "/new_tenant",
    middlewares=[
        inject_tenant,
        inject_iot_transaction_id,
    ],
)
@tracer.capture_method
def create_tenant():
    tenant = app.context["tenant"]
    items = [
        random_item()
        for _ in range(
            random.randint(
                constants.NEW_TENANT_MIN_PRODUCTS, constants.NEW_TENANT_MAX_PRODUCTS
            )
        )
    ]
    emit_iot_event(
        position=[
            REQUEST_STAGE.AMPLIFY,
            REQUEST_STAGE.API_GATEWAY,
            REQUEST_STAGE.LAMBDA,
        ],
        tenant=tenant,
        transaction_id=app.context["iot_transaction_id"],
    )
    put_items(tenant, items)
    emit_iot_event(
        position=[
            REQUEST_STAGE.RDS_PROXY,
            REQUEST_STAGE.RDS,
            REQUEST_STAGE.RDS_PROXY,
            REQUEST_STAGE.LAMBDA,
            REQUEST_STAGE.API_GATEWAY,
            REQUEST_STAGE.AMPLIFY,
        ],
        tenant=tenant,
        transaction_id=app.context["iot_transaction_id"],
    )
    return items


@app.get(
    "/orders",
    middlewares=[
        inject_tenant,
        inject_iot_transaction_id,
    ],
)
@tracer.capture_method
def get_items():
    tenant = app.context["tenant"]
    emit_iot_event(
        position=[
            REQUEST_STAGE.AMPLIFY,
            REQUEST_STAGE.API_GATEWAY,
            REQUEST_STAGE.LAMBDA,
        ],
        tenant=tenant,
        transaction_id=app.context["iot_transaction_id"],
    )
    items = query_items(tenant)
    emit_iot_event(
        position=[
            REQUEST_STAGE.RDS_PROXY,
            REQUEST_STAGE.RDS,
            REQUEST_STAGE.RDS_PROXY,
            REQUEST_STAGE.LAMBDA,
            REQUEST_STAGE.API_GATEWAY,
            REQUEST_STAGE.AMPLIFY,
        ],
        tenant=tenant,
        transaction_id=app.context["iot_transaction_id"],
    )
    return items


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def queue_handler(event: dict, context: LambdaContext) -> dict:
    return process_partial_response(
        event=event,
        record_handler=handle_queue_message,
        processor=processor,
        context=context,
    )


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
def api_handler(event: dict, context: LambdaContext) -> dict:
    return app.resolve(event, context)
