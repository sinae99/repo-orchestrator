
## REP-ORKER

### an Ansible-based repository orchestrator 


---

#### REPORKER

- discovers --->  repositories in a Gitlab Instance like `Hamgit` group using `glab`
- Clones ---> repositories locally
- Scans  ---> repositories for configurable target patterns
- Executes ---> an **Action** on discovered targets
- Produces machine-readable and human-readable reports
- creates **branches**, **commits**, and **pushes** changes

## What reporker does NOT do

- Does not merge branches
- Does not modify default branches
- Does not create merge requests automatically


All irreversible steps are intentionally left to ---> human operators

---

## pre-requisites

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

For this repository, an **Action** is implemented to validate this:

> Ensure a specific comment line exists in all Dockerfiles.

This Action:
- scans for `Dockerfile*`
- inserts a comment line if missing
- makes no duplicate changes on re-runs


### reference example

another project that can be used as an action is **dockerfile-check** ----> (Asible inside Ansible)

---

## reports

All reports are written to:

```
ansible/reports/
```

Including:
- `scan.json`
- `action.json`
- `report.json`
- `changed.json`


------------------------
## run :

## there is 2 way to use this playbook:

- ***automated script***

- ***manually***


## 1 - Run manually


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

### 5) Run 
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

and other Phases

### Run everything
```bash
ansible-playbook -i localhost, playbooks/run.yml --tags discovery,workspace,scan,action,report,publish
```

---

## 2 - Run using the helper script 


### What the script does
`scripts/run.sh`:
- loads inputs from `scripts/envs.txt`
- generates `ansible/group_vars/all.yml`
- runs the Ansible playbook with selected phases (tags)
- prints a small execution summary
- writes reports to `ansible/reports/`

---

### Prepare HamGit token

Create a Personal Access Token in HamGit UI with scopes:
- `api`
- `write_repository`

Store it locally:

```bash
mkdir -p glab
printf '%s' "PASTE_TOKEN_HERE" > glab/hamgit-token
chmod 600 glab/hamgit-token
```

---

### Configure REPORKER (one file)

Copy and edit the environment file:

```bash
cp scripts/envs.example.txt scripts/envs.txt
nano scripts/envs.txt
```

Common values to edit:
- `HAMGIT_HOST`
- `HAMGIT_GROUP_ID`
- `BRANCH_NAME`
- `COMMIT_MESSAGE`
- `TARGET_PATTERNS`
- `ENSURE_LINE`
- `TAGS`

> Do **not** edit `ansible/group_vars/all.yml` manually when using the script.

---

### First run (safe / read-only)

Run only discovery, clone, and scan phases:

```bash
# inside scripts/envs.txt
TAGS="discovery,workspace,scan"
```

Run:

```bash
bash scripts/run.sh
```

### FULL
```bash
# inside scripts/envs.txt
TAGS="discovery,workspace,scan,action,report,publish"
```

Run:

```bash
bash scripts/run.sh
```

---





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

## re-running

reporker is designed to be safe to re-run:
- discovery regenerates `glab/repos.txt`
- workspace syncs repos without recloning unnecessarily
- action is idempotent (no duplicate edits)
- publish only pushes when there is something to commit

**Best practice:** use a unique branch name per run (include date/time) to avoid overwriting an existing branch.

---

