# ***reporker*** 

***repository orchestrator***

## Phase 0 — preconditions

### Inputs

- HamGit hostname  
  - Example: `hamgit.ir`

- Target group identifier  
  - Group ID: `44436`  
  - (or full group path)

- HamGit access token  
  - Used **only** for repository discovery via `glab api`
  - Not used for git clone or push

- Local SSH keys  
  - Must already be configured
  - Used for all git operations (clone, push)

- Workspace directory  
  - Local path where repositories will be cloned
  - Example: `~/glab/workspace`

---

## Phase 1 — Repository discovery

**Tool:** `glab`  
**Executor:** Ansible

- Ansible invokes:
  ```
  glab api groups/<group_id>/projects --paginate
  ```
- The raw API response is collected
- Projects are filtered:
  - archived projects are excluded
- SSH clone URLs are extracted

### Artifacts

- `repos.json`  
  - Raw API response (full project metadata)

- `repos.txt`  
  - One SSH clone URL per line  

---

## Phase 2 — Clone repositories locally

**Tool:** `git`  
**Executor:** Ansible

For each repository listed in `repos.txt`:

- If the repository directory does not exist:
  - `git clone`

- If the repository already exists:
  - `git fetch --prune`

---

## Phase 3 — Target file discovery

**Tool:** Ansible file discovery (`find`)  


For each cloned repository:

- Search for files relevant to the configured **action**
- File patterns are action-defined and configurable

### Outputs

- Per-repository discovery result:
  ```json
  {
    "repo": "example-repo",
    "targets": [
      "./path/to/file1",
      "./path/to/file2"
    ]
  }
  ```

- Combined summary:
  - repositories with matching targets
  - repositories with no matching targets

This phase scans **all repositories**

---

## Phase 4 — the action

**Tool:** Ansible  
**Executor:** Local

### Action

An **action** is a deterministic, idempotent operation applied to discovered targets
inside each repository.

The orchestration layer does **not** define the action itself.

### Outputs

- Per-target:
  - changed: true / false

- Per-repository:
  - changed: true / false  

---

## Phase 5 — Reporting

**Tool:** Ansible templating + JSON output

### reports

#### Full scan report

Includes:
- repositories scanned
- targets discovered
- per-repository change status


#### Changed repositories report

Includes:
- repositories with changes
- targets modified
- branch name to be created/pushed

---

## Phase 6 — Push

**Tool:** `git`  
**Executor:** Ansible

### What happens

For each repository where Phase 4 produced changes:

1. Detect default branch
2. Create a new branch  
   Example:
   ```
   org/ansible/action-20260128
   ```
3. Stage modified files
4. Commit with a consistent message
5. Push the branch to origin


---

## Expected end state (per run)

After a successful run:

- Local workspace with cloned repositories
- `repos.txt`
- `report.json` and `report.md`
- Remote branches pushed 

Human operators open merge requests manually when ready

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
  - Action execution (idempotent)
  - Conditional logic
  - Reporting
