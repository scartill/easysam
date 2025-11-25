from typing import TypedDict, NotRequired
from prismarine.runtime import Cluster


c = Cluster('PrismaTTL')


@c.model(PK='Foo', SK='Bar', ttl='ExpireAt')
class Item(TypedDict):
    Foo: str
    Bar: str
    Baz: NotRequired[str]
    ExpireAt: int
