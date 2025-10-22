from typing import TypedDict, NotRequired
from prismarine.runtime import Cluster


c = Cluster('MyAppWithPrismarine')


@c.model(PK='Foo', SK='Bar', trigger='itemlogger')
class Item(TypedDict):
    Foo: str
    Bar: str
    Baz: NotRequired[str]
