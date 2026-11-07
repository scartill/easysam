"""Reacher: a worked example of indexing and searching DynamoDB native vector
indexes *through the Prismarine-generated client*, embedding text with Amazon
Bedrock.

The function is invoked with an ``action``:

- ``index``   -> embed ``description`` with Bedrock, then ``ProductModel.put(...)``
                 the item (embedding stored on the ``Embedding`` attribute).
- ``search``  -> embed the query ``text`` with Bedrock, then
                 ``ProductModel.ByEmbedding.search(vector=..., category=...)``
                 and return the ranked hits (item + score).

EasySAM wires the IAM: ``services: - bedrock`` grants ``bedrock:InvokeModel``;
listing the ``Product`` table under ``resources.tables`` grants DynamoDB CRUD
plus ``dynamodb:SearchVectors`` scoped to the vector index ARN.
"""

import json
import os

import boto3

from common.catalog.db import ProductModel
from common.catalog.models import Product


# Amazon Titan Text Embeddings V2 (1024-dim, matches the model's vector_index).
EMBED_MODEL_ID = os.environ.get('EMBED_MODEL_ID', 'amazon.titan-embed-text-v2:0')

_bedrock = None


def _bedrock_client():
    """Lazily construct the Bedrock runtime client (region is set in Lambda)."""
    global _bedrock
    if _bedrock is None:
        _bedrock = boto3.client('bedrock-runtime')
    return _bedrock


def embed(text: str) -> list[float]:
    """Return a 1024-dim embedding for ``text`` using Amazon Titan via Bedrock."""
    response = _bedrock_client().invoke_model(
        modelId=EMBED_MODEL_ID,
        body=json.dumps({'inputText': text, 'dimensions': 1024, 'normalize': True}),
    )
    payload = json.loads(response['body'].read())
    return payload['embedding']


def do_index(event: dict) -> dict:
    vector = embed(event['description'])
    product: Product = {
        'ProductId': event['product_id'],
        'Category': event['category'],
        'Brand': event['brand'],
        'Description': event['description'],
        'Embedding': vector,
    }
    ProductModel.put(product)
    return {'indexed': event['product_id']}


def do_search(event: dict) -> dict:
    query_vector = embed(event['text'])
    results = ProductModel.ByEmbedding.search(
        vector=query_vector,
        category=event['category'],          # HASH — required by the search schema
        brand=event.get('brand'),            # optional inline filter
        top_k=event.get('top_k', 5),
        projection=['ProductId', 'Description'],
    )
    hits = [
        {'product_id': hit.item['ProductId'], 'description': hit.item.get('Description'), 'score': hit.score}
        for hit in results
    ]
    return {'hits': hits}


def handler(event, context):
    action = event.get('action')

    if action == 'index':
        body = do_index(event)
    elif action == 'search':
        body = do_search(event)
    else:
        return {'statusCode': 400, 'body': json.dumps({'error': f'unknown action: {action!r}'})}

    return {'statusCode': 200, 'body': json.dumps(body)}
