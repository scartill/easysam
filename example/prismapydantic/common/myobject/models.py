from prismarine.runtime import Cluster
from pydantic import BaseModel, Field


c = Cluster('PrismaPydantic')


@c.export
class NestedItem(BaseModel):
    NestedFoo: str = Field(description="The nested foo attribute")


@c.model(PK='Foo', SK='Bar')
class Item(BaseModel):
    Foo: str = Field(description="The Foo attribute")
    Bar: str = Field(description="The Bar attribute")
    Baz: str = Field(description="The Baz attribute")
    Nested: NestedItem = Field(description="The Nested attribute")
