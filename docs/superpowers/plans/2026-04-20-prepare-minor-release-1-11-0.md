# Prepare Minor Release 1.11.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bump version to 1.11.0, update CHANGELOG.md with recent changes, and prepare for release.

**Architecture:** Standard version bump and changelog update.

**Tech Stack:** Python (Hatchling/pyproject.toml).

---

### Task 1: Update Version in pyproject.toml

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Bump version to 1.11.0**

```toml
version = "1.11.0"
```

- [ ] **Step 2: Commit**

```bash
git add pyproject.toml
git commit -m "chore: bump version to 1.11.0"
```

### Task 2: Update CHANGELOG.md

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Add 1.11.0 section with recent changes**

Summary of changes:
- Added `budget` service support for Lambda functions.
- Added environment variable expansion and local `.env` support.
- Added comprehensive deployment guide and expanded documentation for services.
- Normalized greedy root paths for API Gateway routes.
- Removed unused `yaml.YAMLObject` inheritance and validation stubs.

- [ ] **Step 2: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: update CHANGELOG.md for 1.11.0"
```

### Task 3: Verify and Wrap Up

- [ ] **Step 1: Verify version in pyproject.toml**
- [ ] **Step 2: Verify CHANGELOG.md entry**
- [ ] **Step 3: Check for any other version occurrences**
