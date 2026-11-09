# Deferred Items — vector-indices

**Date**: 2026-11-07
**Source spec**: docs/specs/vector-indices.md
**Mode**: autoflow

## Summary
Shipped EasySAM CloudFormation support for DynamoDB native vector indexes: it consumes
Prismarine's `vectorindices` table-dict block, renders the native `AWS::DynamoDB::Table`
`VectorIndexes` property (injecting `SearchSchema` attributes into `AttributeDefinitions`),
and grants referencing functions an index-scoped `dynamodb:SearchVectors` IAM statement, with
a hermetic `example/vectorindices/` fixture and 30 tests. Intentionally left out: IAM policy
consolidation, a couple of belt-and-suspenders validations, byte-level snapshot testing, and
an automated Prismarine-output verification checkpoint.

## Deferred Items

| ID | Origin | Priority | Item | Rationale / Next Step |
|----|--------|----------|------|-----------------------|
| D1 | Spec critique 💡 E5 | Low | Consolidate `SearchVectors` into one policy statement per table/function instead of one per index. | Current per-index statements are correct and least-privilege; consolidation only matters for functions touching many indexes (IAM role size). Revisit if role-size limits are hit. |
| D2 | Spec critique 💡 E6 (≈ Code review #3) | — | Validate the vector `attribute` (embedding) is disjoint from `hash`/`filters`. | **Partially addressed**: code review #3 added hash-in-filters rejection. The specific "embedding attribute also used as hash/filter" check is still not enforced; add to `process_default_vectorindices` if it proves a real foot-gun. |
| D3 | Spec critique 💡 P1 | Done-ish | Numeric/binary (`N`/`B`) filter types via pre-declaring the attribute in `table.attributes`. | Documented in README; no code change. True first-class numeric-filter support (contract carries a type) remains a v2 item requiring a coordinated Prismarine change. |
| D4 | Spec critique 💡 P2 | Low | Step-by-step migration guidance for the one-index-per-stack-operation limit. | Documented in `docs/CLI_REFERENCE.md` + README cross-reference. No programmatic enforcement (EasySAM can't see deployed state). |
| D5 | Spec critique 🤔 P3 / Code review | Medium | Automated verification that `prisma_easysam.build_dynamo_tables` output is accepted by EasySAM's loader (end-to-end Prismarine→EasySAM). | Tests are hermetic (literal `tables:`), per plan Q4. Add a coordinated integration check at the joint Prismarine/EasySAM release (seed Q6). |
| D6 | Code review 💡 LOW #6 | Done | `local_schemas.json` + flat-index test coverage. | Added in the code-review fix commit. |
| D7 | Code review 💡 LOW #7 | Done | Clarify the `tables: None` guard test name/docstring. | Renamed to `test_template_empty_tables_guard_does_not_crash` with an accurate scope note. |
| D8 | Pre-existing | Low | `scripts/test_examples_generation.py` reports `SystemExit: 0` under pytest (harness calls `sys.exit`), and `example/prismapydantic` test needs AWS creds/region. | Unrelated to this feature; both fail identically on baseline. Candidate cleanup: make the harness pytest-friendly (return instead of `sys.exit`). |

## Suggested Follow-up
Candidates for a future iteration: **D5** (coordinated Prismarine→EasySAM integration check at
joint release) and **D2** (embedding-attribute-disjoint validation) are the highest-signal.
**D3** (first-class numeric filter types) is a larger v2 feature needing a Prismarine contract
change. **D1** (IAM consolidation) and **D8** (test-harness cleanup) are low-priority polish.
