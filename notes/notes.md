# repo-orch — Execution Phases Notes

This document describes the **planned execution phases** of `repo-orch`.

It is a **design and planning reference**, not a user guide.
The purpose is to make the orchestration flow explicit, auditable, and easy to reason about
before implementation.

---

## Phase 0 — Preconditions

This phase defines the **inputs and environment assumptions** required before any automation runs.

### Inputs (provided once)

- HamGit hostname  
  - Example: `hamgit.ir`

- Target group identifier  
  - Group ID: `44436`  
  - (or full group path, if preferred)

- HamGit access token  
  - Used **only** for repository discovery via `glab api`
  - Not used for git clone/push

- Local SSH keys  
  - Must already be configured
  - Used for all git operations (clone, push)

- Workspace directory  
  - Local path where repositories will be cloned
  - Example: `~/Desktop/glab/workspace`

This phase performs **no actions**.  
It exists only to validate assumptions.

---

## Phase 1 — Repository discovery (HamGit)

**Tool:** `glab`  
**Executor:** Ansible (local)

### What happens

- Ansible invokes:
  ```
  glab api groups/<group_id>/projects --paginate
  ```
- The raw API response is collected
- Projects are filtered:
  - archived projects are excluded
  - deletion-scheduled projects are excluded
- SSH clone URLs are extracted

### Outputs / artifacts

- `repos.json`  
  - Raw API response (full project metadata)

- `repos.txt`  
  - One SSH clone URL per line
  - Source of truth for subsequent phases

- Optional: `repos.csv`  
  - Human-friendly summary for review

### Notes

- This is the **only phase that depends on glab**
- After this phase, the workflow is git-only
- Repo discovery is intentionally explicit and inspectable

---

## Phase 2 — Clone or update repositories locally

**Tool:** `git`  
**Executor:** Ansible (local)

### What happens

For each repository listed in `repos.txt`:

- If the repository directory does not exist:
  - `git clone`

- If the repository already exists:
  - `git fetch --prune`
  - reset to default branch (safe re-run behavior)

### Why this phase exists before scanning

- All scanning and actions operate on **real repository contents**
- Avoids relying on API-based file inspection
- Makes the workflow deterministic and debuggable

### Outputs

- Local repository directories in the workspace
- Per-repository status:
  - cloned
  - updated
  - failed (if applicable)

---

## Phase 3 — Dockerfile discovery

**Tool:** Ansible file discovery (or `find`)  
**Scope:** Local filesystem

### What happens

For each cloned repository:

- Search for files matching:
  - `Dockerfile*`
- Matching behavior (case-sensitive or insensitive) is configurable

### Outputs

- Per-repository list of Dockerfiles:
  ```json
  {
    "repo": "example-repo",
    "dockerfiles": [
      "./Dockerfile",
      "./docker/Dockerfile.prod"
    ]
  }
  ```

- Combined summary:
  - repositories with Dockerfiles
  - repositories with **no Dockerfiles** (e.g. `deploy`)

### Notes

- This phase scans **all repositories**
- Repositories without Dockerfiles are still tracked
- Discovery is separate from modification

---

## Phase 4 — Execute the action (idempotent)

**Tool:** Ansible (file editing modules)

### Defined action (current)

- Add the following comment line to Dockerfiles:
  ```
  # this line was added via ansible tool
  ```

### Idempotency rules

- If the line already exists:
  - no change
- If the line does not exist:
  - insert it (location configurable)

Ansible naturally supports this via:
- “ensure line exists” semantics
- optional placement rules (e.g., after `FROM ...`)

### Outputs

- Per-Dockerfile:
  - changed: true / false

- Per-repository:
  - changed: true / false  
    (any Dockerfile changed → repo changed)

---

## Phase 5 — Reporting

**Tool:** Ansible templating + JSON output

### Required reports

#### Full scan report (global)

Includes:
- repositories scanned
- Dockerfiles discovered
- per-repo change status
- errors (if any)

#### Changed repositories report (actionable)

Includes:
- repositories with changes
- Dockerfiles modified
- branch name to be created/pushed

### Purpose

- Audit trail
- Debugging
- Confidence before review/merge
- Historical record of bulk operations

---

## Phase 6 — Publish changes (git)

**Tool:** `git`  
**Executor:** Ansible (local)

### What happens

For each repository where Phase 4 produced changes:

1. Detect default branch
2. Create a new branch  
   Example:
   ```
   org/ansible/dockerfile-comment-20260128
   ```
3. Stage modified Dockerfiles
4. Commit with a consistent message
5. Push the branch to origin

### Skipped cases

- Repositories with no Dockerfiles
- Repositories where no changes occurred

### Notes

- No merge requests are created
- No default branches are modified
- Noise is minimized (changed-only push)

---

## Why this workflow is clean and safe

- No automated merging
- Idempotent changes prevent duplication
- Git history remains the source of truth
- Reports provide full visibility
- Re-running the workflow is safe

---

## Expected end state (per run)

After a successful run:

- Local workspace with cloned repositories
- `repos.txt`
- `report.json` and `report.md`
- Remote branches pushed **only** for changed repositories:
  - `login-service`
  - `signup-service`
  - `api-gateway`
- No changes pushed for repositories like `deploy`

Human operators open merge requests manually when ready.

---

## Tool responsibility summary

- **glab**
  - Repository discovery only
  - API interaction and pagination

- **git**
  - Clone
  - Branch
  - Commit
  - Push

- **ansible**
  - Orchestration
  - Idempotent action execution
  - Conditional logic
  - Reporting
