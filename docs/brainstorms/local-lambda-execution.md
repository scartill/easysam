# Local Lambda Execution Mode

**Date:** 2026-07-25

## Concept

A local HTTP server that mocks API Gateway, allowing Lambda handler code to be called directly without deployment. Real cloud resources (DynamoDB, S3, SQS, etc.) remain on AWS — only the API Gateway routing and auth layers are mocked locally.

---

## Options Explored

### Option 1: Built-in EasySAM `local` Command (Recommended)

A thin Python HTTP server (FastAPI or plain ASGI) that:
- Reads `resources.yaml` / `easysam.yaml` definitions
- Maps each `integration.path` + method to a local route
- Imports and calls the Lambda handler directly (in-process)
- Passes a synthesized API Gateway event + context object
- Skips authorizer logic (or runs it with a hardcoded allow)

**Pros:**
- Zero external deps beyond what EasySAM already uses
- Full control over event shaping, context mocking, environment injection
- Can reuse EasySAM's resource graph to auto-set env vars (table names, bucket names, etc.)
- Fast iteration — no Docker, no SAM build step
- Natural fit: `uv run easysam --environment dev local .`

**Cons:**
- You own the API Gateway event fidelity (v1 vs v2 payloads, multiValueHeaders, etc.)
- No binary payload / streaming parity out of the box
- Need to handle CORS, path params, query strings manually

**Architecture sketch:**

```
easysam local .
  ├─ parse resources.yaml → route table
  ├─ load .env + expand envvars into os.environ
  ├─ start uvicorn/hypercorn on localhost:3000
  └─ for each request:
       ├─ match route → find handler module
       ├─ build APIGatewayProxyEvent (v1 or v2)
       ├─ call handler(event, mock_context)
       └─ translate response dict → HTTP response
```

### Option 2: SAM Local (existing, heavy)

`sam local start-api` via Docker containers.

**Pros:**
- Exact Lambda runtime parity (Docker image)
- Handles layers, binary responses

**Cons:**
- Slow cold starts (Docker spin-up per invocation)
- Requires Docker Desktop / Colima
- Doesn't understand EasySAM's resource model — must `generate` first
- Auth mocking requires custom authorizer Lambda or manual header injection
- Doesn't auto-wire real cloud resource env vars unless you maintain `env.json`

Could still be exposed as: `uv run easysam --environment dev sam-local .` (generate + launch)

### Option 3: Hybrid — EasySAM Thin Proxy + SAM Local Backend

EasySAM runs the HTTP front with auth bypass and route matching, but delegates actual handler execution to `sam local invoke` for runtime fidelity.

**Pros:**
- Fast routing + real runtime isolation
- Can selectively run some functions in-process (fast) and others in Docker (fidelity)

**Cons:**
- Complexity; two processes to manage
- Still needs Docker for the SAM side

### Option 4: In-process with Framework Detection

If a handler uses a framework (e.g., FastAPI via Mangum), the local mode detects that and mounts the ASGI app directly — skipping event translation entirely for maximum speed.

---

## Recommended Approach: Option 1

Fits EasySAM's philosophy: opinionated, minimal config, just works.

### Key Design Decisions

| Decision | Options |
|----------|---------|
| Event format | API GW v1 (REST) vs v2 (HTTP API) — pick one default, flag for other |
| Handler invocation | In-process import vs subprocess isolation |
| Hot reload | watchfiles-based auto-restart on code change |
| Auth mock | Skip entirely (default) / run authorizer locally / accept static token |
| Env vars | Auto-resolve from resource graph (table ARNs → names, bucket names, etc.) |
| CORS | Wide-open in local mode by default |
| Layers / common code | Prepend to `sys.path` like EasySAM already does for packaging |
| Function URLs | Also expose as separate routes (e.g., `/__fn/<name>`) |
| Non-HTTP triggers | `easysam local invoke <function> --event file.json` for SQS/Kinesis/DynamoDB stream testing |

### Proposed UX

```bash
# Start local API server
uv run easysam --environment dev local . --port 3000

# Invoke a specific function with a custom event
uv run easysam --environment dev local invoke myfunction --event event.json
```

### What to Mock vs What Stays Real

| Resource | Local mode behavior |
|----------|-------------------|
| API Gateway | Mocked (local HTTP server) |
| Authorizers | Bypassed or stub-allowed |
| Lambda runtime | In-process Python call |
| DynamoDB | Real (cloud) |
| S3 | Real (cloud) |
| SQS / Kinesis | Real (cloud), but trigger polling is manual |
| Environment vars | Loaded from .env + resource graph resolution |

---

## Open Questions

### 1. Which event payload format should be the default?

API Gateway v1 (REST API) or v2 (HTTP API)?

**Answer:** HTTP API

### 2. Should handler invocation be in-process or subprocess-isolated?

In-process is faster but shares memory/global state. Subprocess is safer but slower.

**Answer:** In-process is enough in terms of safety. However, I'm not sure the python dependencies and module resolution process can handle multiple lambdas properly.

### 3. How should `common/` code and layers be resolved on the local path?

Need to match the packaging layout that EasySAM creates for deployment.

**Answer:** Python's `path` shall be amended, so the lambda code sees it as if deployed.

### 4. Should hot reload be included in v1 or deferred?

watchfiles adds a dependency but massively improves DX.

**Answer:** defer

### 5. How to handle greedy routes (`{proxy+}`)?

Need a route-matching strategy that supports path parameters and catch-all patterns.

**Answer:** all lambda integrations have a boolean `greedy` parameter.

### 6. What env var resolution strategy for real cloud resources?

Options: read from deployed stack outputs, derive from naming conventions, require manual `.env` entries.

**Answer:** `resources.yaml` and `easysam.yaml` files have `envvars` clauses. Use these. Not vars are set in the cloud manually.

### 7. Should non-HTTP trigger invocation (`local invoke`) be part of the same command or separate?

**Answer:** Separate

### 8. What HTTP server library to use?

Options: uvicorn + raw ASGI, FastAPI (adds dependency), Flask, http.server (stdlib).

**Answer:** FastAPI
