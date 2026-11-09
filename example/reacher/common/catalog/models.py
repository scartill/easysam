from typing import TypedDict, NotRequired

from prismarine.runtime import Cluster


# The Cluster prefix MUST start with the EasySAM app prefix ("Reacher").
c = Cluster('Reacher')


# NOTE: keep @c.vector_index on a single line. Prismarine's client generator
# strips decorators with a line-oriented regex, so a multi-line decorator would
# leak its arguments into the generated client.
@c.vector_index(index='by-embedding', attribute='Embedding', dimensions=1024, distance='COSINE', hash='Category', filters=['Brand'])
@c.model(PK='ProductId')
class Product(TypedDict):
    ProductId: str
    Category: str
    Brand: str
    Description: str
    # Embedding is Optional: DynamoDB SearchVectors omits the embedding attribute
    # from results unless it is explicitly projected, so a required field would
    # break deserialization.
    Embedding: NotRequired[list[float]]
