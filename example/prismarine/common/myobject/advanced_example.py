'''
Advanced Prismarine Model Examples with Trigger Configurations

This file demonstrates various ways to configure DynamoDB triggers
using the Prismarine model decorator.
'''
from typing import TypedDict, NotRequired
from prismarine.runtime import Cluster


c = Cluster('MyAppWithPrismarine')


# Example 1: Simple trigger (string format)
# Uses default settings: viewtype='new-and-old', startingposition='latest'
@c.model(PK='UserID', SK='Timestamp', trigger='userlogger')
class UserActivity(TypedDict):
    UserID: str
    Timestamp: str
    Action: str


# Example 2: Full trigger configuration (dict format)
# Customize all trigger options
@c.model(
    PK='OrderID',
    trigger={
        'function': 'orderprocessor',
        'viewtype': 'new-and-old',    # Include both old and new images
        'batchsize': 50,               # Process up to 50 records per invocation
        'batchwindow': 10,             # Wait up to 10 seconds to fill batch
        'startingposition': 'trim-horizon'  # Process all existing records
    }
)
class Order(TypedDict):
    OrderID: str
    CustomerID: str
    Total: float
    Status: NotRequired[str]


# Example 3: Keys-only trigger
# Only receive key attributes, not full item data (more efficient)
@c.model(
    PK='EventID',
    SK='Version',
    trigger={
        'function': 'eventcounter',
        'viewtype': 'keys-only',      # Only keys, no attribute values
        'startingposition': 'latest'
    }
)
class Event(TypedDict):
    EventID: str
    Version: str
    Data: dict


# Example 4: Model without trigger
# Some tables don't need triggers
@c.model(PK='ConfigKey')
class Configuration(TypedDict):
    ConfigKey: str
    ConfigValue: str
    Description: NotRequired[str]


# Example 5: Trigger with new images only
# Useful when you only care about the new state, not what changed
@c.model(
    PK='SensorID',
    SK='ReadingTime',
    trigger={
        'function': 'sensoranalyzer',
        'viewtype': 'new',            # Only new images (after change)
        'batchsize': 100,
        'startingposition': 'latest'
    }
)
class SensorReading(TypedDict):
    SensorID: str
    ReadingTime: str
    Temperature: float
    Humidity: float
