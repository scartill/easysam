# Fix Indentation in SAM Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the indentation in `src/easysam/template.j2` to follow standard CloudFormation/SAM YAML indentation (2 spaces) and simplify `write_result` in `src/easysam/generate.py`.

**Architecture:** 
1. Update `src/easysam/generate.py` to simplify `write_result` and configure Jinja2 to trim blocks and lstrip blocks.
2. Update `src/easysam/template.j2` with correct indentation for all sections.

**Tech Stack:** Python, Jinja2, YAML (SAM)

---

### Task 1: Simplify `write_result` and Configure Jinja2

**Files:**
- Modify: `src/easysam/generate.py`

- [ ] **Step 1: Update `write_result` to write text directly**

```python
def write_result(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text)
```

- [ ] **Step 2: Update Jinja2 Environment configuration to use `trim_blocks=True` and `lstrip_blocks=True`**

In `_generate_with_context` and `invoke_plugin`.

```python
        jenv = Environment(loader=loader, trim_blocks=True, lstrip_blocks=True)
```

- [ ] **Step 3: Run existing tests to ensure no regression**

Run: `pytest tests/test_myapp.py`
Expected: PASS (even with broken indentation in template, since it's currently "valid" but structure-wise wrong, and the test might already be passing with that structure if it was written that way, but actually the test checks for `myfunction['Properties']['Events']`, which would fail if `Events` is not nested correctly).

### Task 2: Fix Indentation in `src/easysam/template.j2`

**Files:**
- Modify: `src/easysam/template.j2`

- [ ] **Step 1: Fix indentation for `Globals`, `Resources`, and `Outputs`**

- [ ] **Step 2: Fix indentation for all nested properties (Functions, Tables, Buckets, etc.)**

- [ ] **Step 3: Run existing tests to verify the fix**

Run: `pytest tests/test_myapp.py`
Expected: PASS

### Task 3: Verify with a new test case if necessary

- [ ] **Step 1: Create a test that specifically checks for the correct YAML structure**

Actually, `tests/test_myapp.py` already checks for `myfunction['Properties']['Events']`. If the indentation was broken such that `Properties` was a top-level key instead of under `myfunctionFunction`, it would fail.

Wait, if the template currently has:
```yaml
myfunctionFunction:
Type: AWS::Serverless::Function
Properties:
...
```
Then `yaml.safe_load` will see `myfunctionFunction: null`, `Type: AWS::Serverless::Function`, `Properties: ...` as top-level keys.

So if `tests/test_myapp.py` is passing, maybe some parts ARE indented correctly or the test is not checking what I think it is.

Let's check `src/easysam/template.j2` again.
```yaml
{{ function_name.replace('-', '' )}}Function:
Type: AWS::Serverless::Function
Properties:
{% if function.timeout is defined %}
Timeout: {{ function.timeout }}
{% endif %}
```
Yes, `Type` and `Properties` are at zero indentation relative to `{{ function_name.replace('-', '' )}}Function:`. This is WRONG for YAML.

If `tests/test_myapp.py` is passing, it might be because it's looking for `myfunctionFunction` in `resources`, but if it's at zero indentation, it's NOT in `resources`?
Wait, `Resources:` is also at zero indentation.
```yaml
Resources:
{% if paths is defined %}
...
ApiGwAccountConfig:
Type: "AWS::ApiGateway::Account"
```
So `Resources` is `null`, and `ApiGwAccountConfig` is a top-level key.

Let's verify this by running the test.
