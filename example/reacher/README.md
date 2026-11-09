# Reacher — Prismarine vector search + Bedrock embeddings

A worked example of **indexing and searching a DynamoDB native vector index through the
Prismarine-generated client**, with embeddings produced by **Amazon Bedrock**.

It ties together three EasySAM capabilities:

- **Prismarine integration** — the `Product` model (`common/catalog/models.py`) declares a
  `@c.vector_index`. Prismarine materializes it into an EasySAM `vectorindices` table block
  *and* generates a client whose `ProductModel.ByEmbedding.search(...)` method wraps the
  DynamoDB `SearchVectors` API.
- **Vector indexes** — EasySAM renders the native `AWS::DynamoDB::Table VectorIndexes`
  property and grants the function `dynamodb:SearchVectors` scoped to the index ARN.
- **`services: - bedrock`** — grants `bedrock:InvokeModel` so the function can call Amazon
  Titan Text Embeddings to embed text.

## Layout

```
resources.yaml                               # prefix, import, prismarine block
thirdparty/requirements.txt                  # boto3, prismarine[vectors], numpy (lambda layer)
common/
  utils.py                                   # get_env()
  dynamo_access.py                           # access-module (get_dynamo_access; inherits get_client)
  catalog/
    models.py                                # @c.vector_index + @c.model Product
    prismarine_client.py                     # GENERATED (do not edit)
    db.py                                     # stable import surface (ProductModel)
backend/function/reacher/
  easysam.yaml                               # tables: [Product] + services: [bedrock]
  index.py                                   # embed -> index / embed -> search handler
```

## The handler

Invoke with an `action`:

- `index` — embeds `description` via Bedrock, then `ProductModel.put(...)` stores the item
  with its `Embedding`.
- `search` — embeds the query `text`, then `ProductModel.ByEmbedding.search(vector=...,
  category=..., brand=..., top_k=...)` returns ranked hits (`item` + `score`).

```jsonc
// index
{"action": "index", "product_id": "p1", "category": "books",
 "brand": "acme", "description": "a hard-boiled detective novel"}

// search
{"action": "search", "text": "noir mystery", "category": "books", "top_k": 5}
```

## Generate / deploy

```bash
uv run easysam --environment reacherdev --target-region us-east-1 generate example/reacher/
uv run easysam --aws-profile <profile> --environment reacherdev --target-region us-east-1 deploy example/reacher/
```

## Notes

- The `Embedding` field is `NotRequired` (Optional): `SearchVectors` omits the embedding from
  results unless explicitly projected, so a required field would break deserialization.
- `dimensions=1024` matches Amazon Titan Text Embeddings V2.
- Keep `@c.vector_index(...)` on a single line — Prismarine's client generator strips
  decorators line-by-line.
- Vector indexes require on-demand billing (`PAY_PER_REQUEST`), which EasySAM always emits.
