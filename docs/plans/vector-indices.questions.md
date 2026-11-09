---
generated-by: "Plan Spec"
spec: docs/specs/vector-indices.md
generated-at: 2026-11-07T13:00:00+02:00
status: resolved
round: 1
---

# Plan Questionnaire: EasySAM Vector Index Support

- **Seed(s)**: `docs/seed/vector-indices.md`
- **Refining notes**: None (run via Autoflow; brainstorm already resolved Q1–Q6)

## Round 1 — 2026-11-07

### Q1: Where does SearchSchema-attribute injection into `attributes` happen?
- **Why it matters**: Determines whether the template or `load.py` owns the dedup logic.
- **Recommended default**: `load.py` preprocessing (new `process_default_vectorindices`
  wired into `preprocess_defaults`), per brainstorm Approach C.
- **Status**: `default-applied`
- **Answer**:
    <!-- USER_INPUT_START:Q1 -->
    [REPLACE THIS TEXT WITH YOUR ANSWER / PREFERENCE]
    <!-- USER_INPUT_END:Q1 -->

### Q2: Should EasySAM validate `distance` enum / `dimensions` range itself?
- **Why it matters**: Prismarine already validates these at decorator time, but a
  hand-written `vectorindices` block (literal `tables:`) would bypass that.
- **Recommended default**: Yes — enforce via JSON Schema: `distance` enum
  {COSINE, EUCLIDEAN, DOT_PRODUCT}, `dimensions` integer 1..4096. Cheap, catches
  hand-written errors, and documents the contract.
- **Status**: `default-applied`
- **Answer**:
    <!-- USER_INPUT_START:Q2 -->
    [REPLACE THIS TEXT WITH YOUR ANSWER / PREFERENCE]
    <!-- USER_INPUT_END:Q2 -->

### Q3: How is the vector index ARN constructed in the SearchVectors IAM statement?
- **Why it matters**: Two valid forms (physical-name `!Sub` vs `.Arn`-based `!Sub`).
- **Recommended default**: `!Sub "${<prefix><table>.Arn}/index/<index-name>"` — reuses the
  table logical id's `.Arn` attribute, avoids hardcoding partition/region/account/stage.
- **Status**: `default-applied`
- **Answer**:
    <!-- USER_INPUT_START:Q3 -->
    [REPLACE THIS TEXT WITH YOUR ANSWER / PREFERENCE]
    <!-- USER_INPUT_END:Q3 -->

### Q4: Example app — Prismarine-sourced or literal `tables:` block?
- **Why it matters**: Seed Q6 says track the Prismarine branch; but a self-contained example
  that generates without a Prismarine dependency is more robust for CI.
- **Recommended default**: Use a **literal `tables:` block** with a `vectorindices` entry for
  the example/test (self-contained, no Prismarine import needed for EasySAM's own tests).
  The Prismarine end-to-end path is exercised separately/manually per the release-coordination
  note. This keeps `tests/test_vectorindices.py` hermetic.
- **Status**: `default-applied`
- **Answer**:
    <!-- USER_INPUT_START:Q4 -->
    [REPLACE THIS TEXT WITH YOUR ANSWER / PREFERENCE]
    <!-- USER_INPUT_END:Q4 -->

### Q5: `AttributeType` for injected hash/filters — fixed `S`, or honor a `type` hint if present?
- **Why it matters**: `local_schemas.json`'s `table_attribute_schema` already allows a `type`
  (S/N/B) on attributes; the vector block carries none.
- **Recommended default**: Default `S` (seed Q2(a)). Do not add a type field to the
  `vectorindices` schema in this pass; document the string-only limitation.
- **Status**: `default-applied`
- **Answer**:
    <!-- USER_INPUT_START:Q5 -->
    [REPLACE THIS TEXT WITH YOUR ANSWER / PREFERENCE]
    <!-- USER_INPUT_END:Q5 -->

## Assumptions (applied if questions are left at their defaults)
- Q1: injection in `load.py::process_default_vectorindices`, wired into `preprocess_defaults`.
- Q2: schema enforces `distance` enum + `dimensions` 1..4096 and `name`/`attribute` required.
- Q3: ARN via `!Sub "${<TableLogicalId>.Arn}/index/<name>"`.
- Q4: hermetic literal-`tables:` example + test; Prismarine path verified out of band.
- Q5: injected attributes are `AttributeType: S`; string-only limitation documented.
