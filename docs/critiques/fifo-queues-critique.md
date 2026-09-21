# Specification Critique Report: FIFO Queue Support

- **Target Spec**: `docs/specs/fifo-queues.md`
- **Pass**: 1st Critique Pass
- **Date**: 2026-09-21
- **Status**: ⚠️ **PROCEED WITH UPDATES**

---

## Executive Summary

The proposed specification `docs/specs/fifo-queues.md` introduces FIFO queue support to EasySAM while maintaining backward compatibility with existing standard queue declarations (`null` values). The overall architecture is clean, minimal, and fits naturally into EasySAM's declarative schema and Jinja template rendering pipeline.

However, the critique identified **two must-address issues** and several **high-value recommendations**:
1. **CloudFormation Incompatibility**: A validation rule mismatch between SQS FIFO parameters (`deduplication_scope: messageGroup` requires `fifo_throughput_limit: perMessageGroupId`) will cause CloudFormation stack creation failures if a user sets `deduplication_scope: messageGroup` without explicitly overriding `fifo_throughput_limit`.
2. **Operational Head-of-Line Blocking Risk**: FIFO queues without Dead-Letter Queues (DLQ) or poison message handling can lock up message groups permanently on repeated Lambda failures.

With targeted updates to schema validation rules, Jinja template rendering guards, and documentation guidance, the spec will be robust and ready for implementation.

---

## Product Lens Findings

### 1a. Problem Validation
- **Clear Pain Point**: EasySAM currently only supports standard SQS queues, preventing teams from building ordered message processing pipelines (e.g., e-commerce order processing, financial transactions, state sync).
- **Scope Boundary**: Excluding API Gateway `sqs` integration targeting FIFO queues for V1 is a sound product decision. API Gateway SQS integration requires complex velocity template mappings for `MessageGroupId` and `MessageDeduplicationId`, which adds significant complexity. Rejecting it cleanly via `validate_schema.py` prevents user misconfiguration.

### 1b. User Value Assessment
- **Default Behavior (`content_based_deduplication`)**: The spec proposes defaulting `content_based_deduplication` to `true`. While this simplifies producer code by auto-deriving `MessageDeduplicationId` from payload body hashes, it differs from AWS SQS's native default (`false`).
  - *Risk*: If producers emit distinct event instances with identical payloads (e.g., `{"type": "ping"}`) within a 5-minute deduplication window, SQS will silently drop the duplicate messages.
  - *Recommendation*: Align with AWS default (`false`) or prominently document the 5-minute content hash deduplication window.

### 1c. Alternative Approaches
- **Declarative Object Extension**: Allowing queues to accept an object (`{ fifo: true, ... }`) alongside `null` preserves backward compatibility for existing standard queues while enabling property configuration (`visibility_timeout`, `message_retention_period`) for standard queues as well.

### 1d. Edge Cases & User Experience
- **Queue Replacement Warning**: AWS SQS does not allow converting an existing standard queue to FIFO in place. Users updating `myqueue: null` to `myqueue: { fifo: true }` in `resources.yaml` will trigger CloudFormation resource replacement (queue deletion and recreation), resulting in potential message loss if not planned.

### 1e. Success Measurement
- The specification includes clear acceptance criteria and requires a runnable example under `example/fifoqueue/` verified by generation tests.

---

## Engineering Lens Findings

### 2a. Architecture Soundness
- **CloudFormation Parameter Constraints (Must-Address)**:
  - AWS SQS CloudFormation validation rule: If `DeduplicationScope` is set to `messageGroup`, `FifoThroughputLimit` **must** be set to `perMessageGroupId`.
  - The spec sets independent defaults (`deduplication_scope: queue`, `fifo_throughput_limit: perQueue`). If a user specifies `deduplication_scope: messageGroup` without setting `fifo_throughput_limit`, EasySAM will render:
    ```yaml
    DeduplicationScope: messageGroup
    FifoThroughputLimit: perQueue
    ```
    This causes AWS CloudFormation deployment to fail with a template error.
  - *Fix*: Update schema validation and Jinja template logic to enforce that `fifo_throughput_limit` automatically defaults to `perMessageGroupId` when `deduplication_scope` is `messageGroup`.

### 2b. Failure Mode Analysis
- **Queue Name Length Boundary**: AWS SQS enforces an 80-character maximum length limit for queue names. EasySAM constructs FIFO queue names as `!Sub "{{ lprefix }}-{{ queue_name }}-${Stage}.fifo"`. Long prefix, queue, or stage names could breach the 80-character limit during deployment.

### 2c. Security & Privacy Review
- IAM poller policies (`SQSPollerPolicy`) and sender policies (`SQSSendMessagePolicy`) use `!GetAtt Queue.QueueName` and `!GetAtt Queue.Arn`. For FIFO queues, CloudFormation returns names with the `.fifo` suffix. IAM policy evaluation remains scoped correctly to the specific FIFO queue ARN.

### 2d. Performance & Scalability
- **Batch Size & Retries**: In Lambda SQS FIFO event source mappings (`polls`), if `batchsize > 1` and Lambda fails to process a record, the entire batch is retried. Developers using FIFO queues should be advised to handle errors per record or use `batchsize: 1` to prevent unnecessary batch retries.

### 2e. Testing Strategy
- The proposed test plan covers schema validation, Jinja rendering, API Gateway rejection, and end-to-end example generation. Adding explicit test cases for invalid parameter combinations (`deduplication_scope: messageGroup` with `fifo_throughput_limit: perQueue`) will prevent regressions.

---

## Cross-Lens Insights

### Poison Messages & Head-of-Line Blocking (Scope × Operational Risk)
Both Product and Engineering lenses highlight the operational risk of SQS FIFO queues without Dead-Letter Queues (DLQs):
- SQS FIFO preserves strict sequence within a `MessageGroupId`.
- If a "poison message" causes a Lambda function to throw an unhandled exception repeatedly, processing for that entire `MessageGroupId` stops indefinitely ("head-of-line blocking").
- *Synthesis*: While DLQ / RedrivePolicy is currently Out of Scope for V1, the spec should explicitly document this operational constraint and provide developer guidance on handling unhandled exceptions in Lambda consumers.

---

## Findings Summary Table

| ID | Lens | Severity | Category | Finding | Suggestion |
|----|------|----------|----------|---------|------------|
| E1 | Engineering | 🎯 | Architecture Soundness | `deduplication_scope: messageGroup` with `fifo_throughput_limit: perQueue` is rejected by CloudFormation. | Enforce in schema/Jinja that `deduplication_scope: messageGroup` requires `fifo_throughput_limit: perMessageGroupId`. |
| X1 | Both | 🎯 | Operational Risk | Poison messages in FIFO queues without DLQ cause permanent head-of-line blocking. | Document head-of-line blocking risk in spec and `RESOURCE_REFERENCE.md`, noting Lambda error handling recommendations. |
| P1 | Product | 💡 | User Value Assessment | Defaulting `content_based_deduplication` to `true` differs from AWS SQS default (`false`) and may silently drop identical payloads. | Reconsider default to `false` or add clear documentation warning about content hash deduplication. |
| P2 | Product | 💡 | User Experience | Converting standard queue to FIFO in `resources.yaml` causes CloudFormation resource deletion and recreation. | Add migration note in `docs/RESOURCE_REFERENCE.md` explaining queue replacement behavior. |
| E2 | Engineering | 💡 | Failure Mode Analysis | Queue names exceeding 80 characters (with prefix, stage, and `.fifo`) will fail CloudFormation creation. | Add queue name length validation in `src/easysam/validate_schema.py`. |
| E3 | Engineering | 💡 | Implementation Risk | `{{ queue.content_based_deduplication \| default(true) \| lower }}` in Jinja can fail or render uncleanly on explicit boolean `false`. | Use explicit Jinja condition: `{{ 'true' if (queue.content_based_deduplication is not defined or queue.content_based_deduplication) else 'false' }}`. |

---

## Verdict

### ⚠️ PROCEED WITH UPDATES

The specification is well-conceived and near implementation-ready. Resolving the parameter combination constraint (E1) and documenting operational risks (X1, P1, P2) will ensure a flawless implementation.

---

## Remediation & Suggested Spec Edits

Below are the recommended updates to `docs/specs/fifo-queues.md`:

### 1. Fix Parameter Combination Constraint in Requirements & Solution (Fixes E1)

**In `docs/specs/fifo-queues.md` under Section `Requirements`, item 3**:
```markdown
3. FIFO-specific configurable properties, each with a reasonable default when the queue is FIFO:
   - `content_based_deduplication` → `ContentBasedDeduplication` (default `true`)
   - `deduplication_scope` → `DeduplicationScope`, enum `messageGroup` | `queue` (default `queue`)
   - `fifo_throughput_limit` → `FifoThroughputLimit`, enum `perQueue` | `perMessageGroupId` (default `perQueue`; automatically set to `perMessageGroupId` if `deduplication_scope` is `messageGroup`)
```

**In `docs/specs/fifo-queues.md` under Section `Proposed Solution -> Template rendering (queue loop)`**:
```jinja
{% for queue_name, queue in queues.items() %}
{{ lprefix }}{{ queue_name.replace('-', '') }}Queue:
  Type: AWS::SQS::Queue
  Properties:
    {% if queue and queue.fifo %}
    QueueName: !Sub "{{ lprefix }}-{{ queue_name }}-${Stage}.fifo"
    FifoQueue: true
    ContentBasedDeduplication: {{ 'true' if (queue.content_based_deduplication is not defined or queue.content_based_deduplication) else 'false' }}
    DeduplicationScope: {{ queue.deduplication_scope | default('queue') }}
    FifoThroughputLimit: {{ queue.fifo_throughput_limit | default('perMessageGroupId' if queue.deduplication_scope == 'messageGroup' else 'perQueue') }}
    {% else %}
    QueueName: !Sub "{{ lprefix }}-{{ queue_name }}-${Stage}"
    {% endif %}
    {% if queue and queue.visibility_timeout is defined %}
    VisibilityTimeout: {{ queue.visibility_timeout }}
    {% endif %}
    {% if queue and queue.message_retention_period is defined %}
    MessageRetentionPeriod: {{ queue.message_retention_period }}
    {% endif %}
{% endfor %}
```

### 2. Add Head-of-Line Blocking & Operational Guidance (Fixes X1, P1, P2)

**In `docs/specs/fifo-queues.md` under Section `Out of Scope`**:
```markdown
## Out of Scope & Operational Considerations

- API Gateway `sqs` integration targeting a FIFO queue (would require `MessageGroupId`/`MessageDeduplicationId` handling in the swagger request template). Explicitly rejected by validation in Task 3.
- Dead-letter queue / redrive policy configuration (not requested for V1).
- KMS encryption configuration for queues (not requested).

### Operational Considerations for Implementers & Documentation
- **Head-of-Line Blocking**: In SQS FIFO queues, failing Lambda executions block processing for that `MessageGroupId` until resolved. Documentation should advise catching exceptions within Lambda handlers.
- **Resource Replacement**: Converting an existing standard queue to a FIFO queue in `resources.yaml` causes CloudFormation to delete and recreate the SQS resource.
- **Deduplication Window**: Content-based deduplication automatically drops messages with matching body hashes sent within 5 minutes.
```
