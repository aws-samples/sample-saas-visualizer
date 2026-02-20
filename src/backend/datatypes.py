from enum import Enum
from typing import Annotated, Literal

from pydantic import Field
from pydantic.dataclasses import dataclass

from constants import STATUSES


@dataclass
class Item:
    Product: Annotated[str, Field(pattern=r"^[a-zA-Z0-9\(\)\-\,\. ]{1,100}$")]
    Price: Annotated[int, Field(gt=0, le=1000)]
    Order_Date: Annotated[
        str,
        Field(
            pattern=r"^(0[1-9]|[12][0-9]|3[01])/(0[1-9]|1[0-2])/\d{4}\s(0[1-9]|1[0-2]):([0-5][0-9])\s(AM|PM)$"
        ),
    ]
    Status: Literal[tuple(STATUSES)]
    Rating: Annotated[int, Field(ge=0, le=5)]


@dataclass
class Tenant:
    Name: Annotated[str, Field(pattern=r"^[0-9]{1,4}$")]
    Color: Annotated[str, Field(pattern=r"^#?([a-fA-F0-9]{6}|[a-fA-F0-9]{3})$")]


class REQUEST_STAGE(str, Enum):
    AMPLIFY = "amplify"
    API_GATEWAY = "apigateway"
    LAMBDA = "lambda"
    RDS = "rds"
    RDS_PROXY = "rdsproxy"
    SHARED_SQS = "sharedsqs"
    SILOED_SQS = "siloedsqs"
