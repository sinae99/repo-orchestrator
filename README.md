# reporker

an Ansible-based repository orchestrator 

designed to operate on *many repositories at scale*

It discovers repositories from a Gitlab Instance group, 

clone them locally ----> scans for targets ---->

executes an **Action** ----> generates structured reports ----> 

publishes changes ----> as isolated git branches


---

## REPORKER

- Discovers repositories in a Gitlab Instance like `Hamgit` group using `glab`
- Clones or updates repositories locally
- Scans repositories for configurable target patterns
- Executes an **Action** on discovered targets
- Produces machine-readable and human-readable reports
- creates branches, commits, and pushes changes

## What reporker does NOT do

- ❌ Does not merge branches
- ❌ Does not modify default branches directly
- ❌ Does not create merge requests automatically


All irreversible steps are intentionally left to human operators

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

## Repo layout

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
├── notes/              
└── README.md
```

---

## Conf

All runtime configuration lives in:

```
ansible/group_vars/all.yml
```

---

## Execution model ---> phases

Each phase can be executed independently using Ansible tags.

---

## The Action

The **Action** is the heart of reporker

An Action is:
- User-defined
- Idempotent
- Executed only on discovered targets
- Fully replaceable without changing orchestration

### Example Action used in this repository

For this repository, an **Action** is implemented to validate the full workflow:

> Ensure a specific comment line exists in all Dockerfiles.

This Action:
- scans for `Dockerfile*`
- inserts a comment line if missing
- makes no duplicate changes on re-runs


### reference example

another project that can be used as an action is **dockerfile-check** ----> (Asible inside Ansible)

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
