---
generated-by: "Split Tasks"
source: docs/specs/vector-indices.md
generated-at: 2026-11-07T13:30:00+02:00
inputs-ready: false
completed: false
status: not-started
---

# Task 07: Documentation — README, CLI reference, CHANGELOG

- [ ] **Completion**
- **Source spec**: `docs/specs/vector-indices.md`
- **Depends on**: `task-01-schema.md`..`task-05-example-app.md`
- **Blocks**: `None`
- **Parallelism**: `Safe with task-06 (docs only, no code)`

## Objective
Document the `vectorindices` feature, its constraints, the string-only filter-type
limitation + numeric workaround, the one-index-per-stack-operation caveat, and the
coordinated Prismarine release.

## Scope & Traceability
- **Requirements / acceptance criteria**: seed follow-ups; spec "Out of Scope" caveats.
- **Testing & risk strategy items**: documents Critique P1 (numeric workaround), P2
  (migration guidance), and the one-index-per-op caveat.
- **Out of scope**: code/behaviour changes.

## Implementation Guidance
- **Files to create or modify**:
  - `README.md`: add a `vectorindices` section under the tables documentation — the block
    shape (`name`, `attribute`, `dimensions`, `distance`, optional `hash`, optional `filters`;
    `filters` requires `hash`), the generated `VectorIndexes` + `SearchVectors` IAM behavior,
    the on-demand (`PAY_PER_REQUEST`) requirement, limits (≤5 indexes, 1..4096 dims, ≤18
    filters), and the **numeric/binary filter workaround**: injected attributes default to
    `S`, but a user can pre-declare the attribute in `table.attributes` with `type: N`/`B`
    (Critique P1).
  - `docs/CLI_REFERENCE.md`: add/extend the tables reference with `vectorindices` and the
    **one-index-per-stack-operation** caveat + migration guidance: on an existing stack, add
    one index (GSI or vector) per `deploy`; initial `CreateTable` allows multiple at once
    (Critique P2, P3 note).
  - `CHANGELOG.md`: a new entry noting vector-index support and the **coordinated Prismarine
    release** (this EasySAM change consumes Prismarine's `vectorindices` block; ship together;
    during development it tracks the Prismarine `vector-indices` branch) (seed Q6).
- **Established patterns to follow**: existing table/trigger/ttl documentation style in
  `README.md` and `docs/CLI_REFERENCE.md`; the existing `CHANGELOG.md` entry format.
- **Constraints and non-goals**: documentation only; do not alter behavior.

## Verification Requirements
- **Automated tests**: none (docs).
- **Manual / integration checks**: README renders the new section; the example in Task 5
  matches the documented block shape.
- **Risk coverage**: documents the operational caveats and the string-only limitation.
- **Demo command**: n/a (prose review).
- **Expected result**: the three docs updated and internally consistent with the example.

## Handoff Notes
Keep the documented block shape identical to the Task 1 schema and Task 5 example to avoid
drift. Note that `Finalize` may add deferred items to `docs/feedback/`.
