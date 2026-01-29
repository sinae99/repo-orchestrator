# reporker

**reporker** is an Ansible-based repository orchestrator designed to operate on *many repositories at scale* in a safe, auditable, and repeatable way.

It discovers repositories from a HamGit group, materializes them locally, scans for targets, executes a user-defined **Action**, generates structured reports, and optionally publishes changes as isolated git branches.

---

## What reporker does

- Discovers repositories in a HamGit group using `glab`
- Clones or updates repositories locally
- Scans repositories for configurable target patterns
- Executes an **idempotent Action** on discovered targets
- Produces machine-readable and human-readable reports
- Optionally creates branches, commits, and pushes changes

## What reporker does NOT do

- ❌ Does not merge branches
- ❌ Does not modify default branches directly
- ❌ Does not create merge requests automatically
- ❌ Does not assume anything about repository internals

All irreversible steps are intentionally left to human operators.

---

## Prerequisites

Required tools on the execution host:

- `ansible`
- `git`
- `glab`
- `jq`

Authentication requirements:

- SSH keys configured for git clone/push
- HamGit access token (used **only** for repository discovery via API)

---

## Repository layout

```
reporker/
├── ansible/
│   ├── playbooks/run.yml
│   ├── roles/
│   │   ├── discovery/
│   │   ├── workspace/
│   │   ├── scan/
│   │   ├── action/
│   │   ├── report/
│   │   └── publish/
│   ├── group_vars/all.yml
│   ├── workspace/      # cloned repositories
│   └── reports/        # generated outputs
├── glab/
│   ├── hamgit-token
│   └── repos.txt
├── notes/              # planning & design notes
└── README.md
```

---

## Configuration

All runtime configuration lives in:

```
ansible/group_vars/all.yml
```

---

## Execution model (phases)

Each phase can be executed independently using Ansible tags.

---

## The Action (core concept)

The **Action** is the heart of reporker.

An Action is:
- User-defined
- Idempotent
- Executed only on discovered targets
- Fully replaceable without changing orchestration

### Example Action used in this repository

For this repository, a **sample Action** is implemented to validate the full workflow:

> Ensure a specific comment line exists in all Dockerfiles.

This Action:
- scans for `Dockerfile*`
- inserts a comment line if missing
- makes no duplicate changes on re-runs

This Action exists **only as a demonstration** of the orchestration flow.

### Action reference example

A real-world example of an Action-oriented project is **dockerfile-check**.

In `reporker`, the Dockerfile line insertion is used purely as a sample Action to test the complete playbook flow.

---

## Reports

All reports are written to:

```
ansible/reports/
```

Including:
- `scan.json`
- `action.json`
- `report.json`
- `changed.json`
- `publish.json`

---

## Safety & idempotency

- Safe to re-run
- No default branches modified
- Changes isolated to branches
- Human-reviewed merges only
