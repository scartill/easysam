# Fix Failing Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all failing tests in `tests/*.py` by updating `generate` and `resources` call sites to match their new signatures.

**Architecture:** Update call sites in tests. `generate` now takes a list of `deploy_ctxs` and returns a `benedict` results object. `resources` now takes `toolparams` as the first argument.

**Tech Stack:** Python, pytest, easysam

---

### Task 1: Fix `generate` calls in tests

**Files:**
- Modify: `tests/test_userenvvars.py`
- Modify: `tests/test_prismarine_all.py`
- Modify: `tests/test_prismarine.py`
- Modify: `tests/test_plugins.py`
- Modify: `tests/test_onelambda.py`
- Modify: `tests/test_myapp.py`
- Modify: `tests/test_local_envvars.py`
- Modify: `tests/test_kinesis_multiple_buckets.py`
- Modify: `tests/test_greedy_paths.py`
- Modify: `tests/test_function_url.py`
- Modify: `tests/test_errors.py`
- Modify: `tests/test_dynamottl.py`
- Modify: `tests/test_customlayer.py`
- Modify: `tests/test_conditionals.py`

- [ ] **Step 1: Update `generate` calls to use list for `deploy_ctxs` and handle `benedict` result**
  
  Old: `resources_data, errors = generate(cliparams, path, [], deploy_ctx)`
  New: 
  ```python
  results, errors = generate(cliparams, path, [deploy_ctx])
  resources_data = results[deploy_ctx['name']]
  ```
  Note: If `deploy_ctx` is not present, `generate` might use `'default'`. Check each file.

- [ ] **Step 2: Verify each file's implementation**

### Task 2: Fix `resources` calls in tests

**Files:**
- Modify: `tests/test_local_validation.py`
- Modify: `tests/test_function_url.py`
- Modify: `tests/test_envvars_expansion.py`

- [ ] **Step 1: Update `resources` calls to include `toolparams` as first argument**
  
  Old: `resources_data = resources(path, [], deploy_ctx, errors)`
  New: `resources_data = resources({}, path, deploy_ctx, errors)`

- [ ] **Step 2: Verify each file's implementation**

### Task 3: Run all tests to verify fixes

- [ ] **Step 1: Run pytest on the entire `tests/` directory**
  
  Run: `pytest tests/`
  Expected: All tests pass (or at least no more "incorrect argument count/type" errors for these functions).
