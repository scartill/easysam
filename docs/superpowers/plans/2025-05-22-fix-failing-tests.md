# Fix Failing Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update all failing tests in `tests/*.py` to match the new signatures for `generate()` and `resources()`.

**Architecture:** Surgical updates to call sites in test files.

**Tech Stack:** Python, pytest

---

### Task 1: Fix `generate()` calls in simple test files

**Files:**
- Modify: `tests/test_aoss.py`
- Modify: `tests/test_customlayer.py`
- Modify: `tests/test_dynamottl.py`
- Modify: `tests/test_errors.py`
- Modify: `tests/test_function_url.py`
- Modify: `tests/test_kinesis_multiple_buckets.py`
- Modify: `tests/test_myapp.py`
- Modify: `tests/test_onelambda.py`
- Modify: `tests/test_plugins.py`
- Modify: `tests/test_prismarine.py`

- [ ] **Step 1: Update `tests/test_aoss.py`**
Replace:
```python
    resources_data, errors = generate(cliparams, example_path, [], deploy_ctx)
```
With:
```python
    results, errors = generate(cliparams, example_path, [deploy_ctx])
    resources_data = results['default']
```

- [ ] **Step 2: Update `tests/test_customlayer.py`**
Replace:
```python
    resources_data, errors = generate(cliparams, example_path, [], deploy_ctx)
```
With:
```python
    results, errors = generate(cliparams, example_path, [deploy_ctx])
    resources_data = results['default']
```

- [ ] **Step 3: Update `tests/test_dynamottl.py`**
Replace:
```python
    resources_data, errors = generate(cliparams, example_path, [], deploy_ctx)
```
With:
```python
    results, errors = generate(cliparams, example_path, [deploy_ctx])
    resources_data = results['default']
```

- [ ] **Step 4: Update `tests/test_errors.py`**
Replace:
```python
    resources_data, errors = generate(cliparams, example_path, [], deploy_ctx)
```
With:
```python
    results, errors = generate(cliparams, example_path, [deploy_ctx])
    resources_data = results['default']
```

- [ ] **Step 5: Update `tests/test_function_url.py`**
Replace:
```python
    resources_data, errors = generate(cliparams, example_path, [], deploy_ctx)
```
With:
```python
    results, errors = generate(cliparams, example_path, [deploy_ctx])
    resources_data = results['default']
```

- [ ] **Step 6: Update `tests/test_kinesis_multiple_buckets.py`**
Replace:
```python
    resources_data, errors = generate(cliparams, example_path, [], deploy_ctx)
```
With:
```python
    results, errors = generate(cliparams, example_path, [deploy_ctx])
    resources_data = results['default']
```

- [ ] **Step 7: Update `tests/test_myapp.py`**
Replace:
```python
    resources_data, errors = generate(cliparams, example_path, [], deploy_ctx)
```
With:
```python
    results, errors = generate(cliparams, example_path, [deploy_ctx])
    resources_data = results['default']
```

- [ ] **Step 8: Update `tests/test_onelambda.py`**
Replace:
```python
    resources_data, errors = generate(cliparams, example_path, [], deploy_ctx)
```
With:
```python
    results, errors = generate(cliparams, example_path, [deploy_ctx])
    resources_data = results['default']
```

- [ ] **Step 9: Update `tests/test_plugins.py`**
Replace:
```python
    resources_data, errors = generate(cliparams, example_path, [], deploy_ctx)
```
With:
```python
    results, errors = generate(cliparams, example_path, [deploy_ctx])
    resources_data = results['default']
```

- [ ] **Step 10: Update `tests/test_prismarine.py`**
Replace:
```python
        resources_data, errors = generate(cliparams, example_path, [], deploy_ctx)
```
With:
```python
        results, errors = generate(cliparams, example_path, [deploy_ctx])
        resources_data = results['default']
```

- [ ] **Step 11: Run tests to verify**
Run: `C:\Users\boris\projects\var\easysam\.venv\Scripts\python.exe -m pytest tests/test_aoss.py tests/test_customlayer.py tests/test_dynamottl.py tests/test_errors.py tests/test_function_url.py tests/test_kinesis_multiple_buckets.py tests/test_myapp.py tests/test_onelambda.py tests/test_plugins.py tests/test_prismarine.py`

### Task 2: Fix `resources()` calls and more complex `generate()` calls

**Files:**
- Modify: `tests/test_conditionals.py`
- Modify: `tests/test_envvars_expansion.py`
- Modify: `tests/test_greedy_paths.py`
- Modify: `tests/test_local_envvars.py`
- Modify: `tests/test_local_validation.py`

- [ ] **Step 1: Update `tests/test_conditionals.py`**
Update `get_resources` function and the direct call in `test_conditionals_generation`.
Replace:
```python
    resources_data, errors = generate(cliparams, example_path, [], deploy_ctx)
```
With:
```python
    results, errors = generate(cliparams, example_path, [deploy_ctx])
    resources_data = results['default']
```
(Twice in this file)

- [ ] **Step 2: Update `tests/test_envvars_expansion.py`**
Replace:
```python
    res = resources(tmp_path, [], {}, [])
```
With:
```python
    res = resources({}, tmp_path, {}, [])
```
Replace:
```python
    res = resources(tmp_path, [], {}, errors)
```
With:
```python
    res = resources({}, tmp_path, {}, errors)
```

- [ ] **Step 3: Update `tests/test_greedy_paths.py`**
Replace:
```python
    _, errors = generate({}, tmp_path, [], deploy_ctx)
```
With:
```python
    _, errors = generate({}, tmp_path, [deploy_ctx])
```

- [ ] **Step 4: Update `tests/test_local_envvars.py`**
Replace:
```python
    data, errors = generate({}, tmp_path, [], deploy_ctx)
```
With:
```python
    results, errors = generate({}, tmp_path, [deploy_ctx])
    data = results['default']
```

- [ ] **Step 5: Update `tests/test_local_validation.py`**
Replace:
```python
    resources_data = resources(tmp_path, [], deploy_ctx, errors)
```
With:
```python
    resources_data = resources({}, tmp_path, deploy_ctx, errors)
```
(Multiple occurrences)

- [ ] **Step 6: Run tests to verify**
Run: `C:\Users\boris\projects\var\easysam\.venv\Scripts\python.exe -m pytest tests/test_conditionals.py tests/test_envvars_expansion.py tests/test_greedy_paths.py tests/test_local_envvars.py tests/test_local_validation.py`

### Task 3: Final verification of all tests

- [ ] **Step 1: Run all specified tests**
Run: `C:\Users\boris\projects\var\easysam\.venv\Scripts\python.exe -m pytest tests/test_aoss.py tests/test_conditionals.py tests/test_customlayer.py tests/test_dynamottl.py tests/test_envvars_expansion.py tests/test_errors.py tests/test_function_url.py tests/test_greedy_paths.py tests/test_kinesis_multiple_buckets.py tests/test_local_envvars.py tests/test_local_validation.py tests/test_myapp.py tests/test_onelambda.py tests/test_plugins.py tests/test_userenvvars.py`
