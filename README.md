# reporker

**reporker** is an Ansible-based repository orchestrator for applying a repeatable, auditable change (**Action**) across many repositories in a HamGit group.

It:
1) discovers repositories from a HamGit group (via `glab` API),
2) clones/updates them locally,
3) scans for target files,
4) runs an idempotent Action,
5) generates reports,
6) optionally publishes changes as branches (commit + push).

> **Safety-first:** reporker does **not** merge branches and does **not** modify default branches directly.

---

## Who this is for

DevOps/platform teams who need a reliable “bulk operation” workflow across many repos:
- enforcing a policy,
- applying a migration,
- updating CI templates,
- modifying manifests,
- running linters/fixers,
- etc.

---

## Core concept: the Action

An **Action** is the only “business logic” part of reporker.

**Definition**
- A deterministic, idempotent operation that runs on discovered target files.
- Replaceable: you can implement any Action without changing discovery/workspace/publish plumbing.

**Example Action in this repo**
This repository includes a **sample Action** used to validate the end-to-end flow:
- scan for `Dockerfile*`
- ensure a comment line exists:
  - `# this line was added via ansible tool`

This sample Action exists only as a demonstration.

**Reference**
A real Action example is the separate project **dockerfile-check** (mentioned here only as a reference example for an Action-style workflow).

---

## What reporker does

- Discovers repositories in a HamGit group using `glab`
- Clones/updates repos locally via `git`
- Scans local workspaces for target patterns
- Executes an idempotent Action on those targets
- Produces reports for audit and troubleshooting
- Optionally creates a branch, commits, and pushes (changed repos only)

## What reporker does NOT do

- ❌ does not auto-merge
- ❌ does not open merge requests
- ❌ does not modify default branches
- ❌ does not require CI/CD changes in each repo

---

## Requirements

### Tools (local machine)
Install on the machine that runs reporker:

- `ansible`
- `git`
- `glab`
- `jq`

### Access
- SSH keys configured for HamGit clone/push (`git@hamgit.ir:...`)
- HamGit access token for discovery (**api + write_repository** scope)
  - token is used by `glab api` only (not by git operations)

---

## Repository structure

```
reporker/
├── ansible/
│   ├── ansible.cfg
│   ├── group_vars/all.yml
│   ├── playbooks/run.yml
│   ├── roles/
│   │   ├── discovery/
│   │   ├── workspace/
│   │   ├── scan/
│   │   ├── action/
│   │   ├── report/
│   │   └── publish/
│   ├── reports/             # run outputs (generated)
│   └── workspace/           # local clones (generated)
├── glab/
│   ├── hamgit-token         # token file (local secret; do not commit)
│   └── repos.txt            # discovery output (generated)
└── notes/
    └── notes.md             # planning notes
```

> **Important:** `ansible/workspace/`, `ansible/reports/`, `glab/repos.txt`, and `glab/hamgit-token` are runtime artifacts.  
> Do not commit secrets. Add local artifacts to `.gitignore`.

---

## Quick start (user guide)

### 1) Clone
```bash
git clone <THIS_REPO_URL>
cd reporker
```

### 2) Create a HamGit token
In HamGit UI, create a Personal Access Token with scopes:
- `api`
- `write_repository`

Store it locally:
```bash
mkdir -p glab
printf '%s' "PASTE_TOKEN_HERE" > glab/hamgit-token
chmod 600 glab/hamgit-token
```

### 3) Authenticate glab
```bash
cat glab/hamgit-token | glab auth login --hostname hamgit.ir --stdin
glab api user --hostname hamgit.ir
```

### 4) Configure reporker
Edit:
```bash
nano ansible/group_vars/all.yml
```

Set at least:
- `hamgit.host` (example: `hamgit.ir`)
- `hamgit.group_id` (example: `44436`)
- `paths.workspace` and `paths.reports`
- `git.branch_name` and `git.commit_message`
- Action settings (patterns / parameters)

### 5) Run phase-by-phase (recommended)
Run from `ansible/`:
```bash
cd ansible
```

Phase 1 — discovery:
```bash
ansible-playbook -i localhost, playbooks/run.yml --tags discovery
```

Phase 2 — workspace:
```bash
ansible-playbook -i localhost, playbooks/run.yml --tags workspace
```

Phase 3 — scan:
```bash
ansible-playbook -i localhost, playbooks/run.yml --tags scan
```

Phase 4 — action:
```bash
ansible-playbook -i localhost, playbooks/run.yml --tags action
```

Phase 5 — report:
```bash
ansible-playbook -i localhost, playbooks/run.yml --tags report
```

Phase 6 — publish (branch/commit/push for changed repos only):
```bash
ansible-playbook -i localhost, playbooks/run.yml --tags publish
```

### Run everything
```bash
ansible-playbook -i localhost, playbooks/run.yml --tags discovery,workspace,scan,action,report,publish
```

---

## Reports

Reports are written to `ansible/reports/`:

- `repos.json` — repository discovery output (raw API)
- `scan.json` — scan results (targets found per repo)
- `action.json` — Action execution summary
- `report.json` — full run summary (aggregated)
- `changed.json` — only changed repos (operator-focused)
- `publish.json` — publish results (per repo command output)

---

## Re-running safely

reporker is designed to be safe to re-run:
- discovery regenerates `glab/repos.txt`
- workspace syncs repos without recloning unnecessarily
- action is idempotent (no duplicate edits)
- publish only pushes when there is something to commit

**Best practice:** use a unique branch name per run (include date/time) to avoid overwriting an existing branch.

---

## Customize / replace the Action

To implement your own Action:
- modify `ansible/roles/action/tasks/main.yml`
- adjust scan patterns in `ansible/group_vars/all.yml` as needed

All other roles remain reusable plumbing.

---

## License

Internal tool / project policy applies.
