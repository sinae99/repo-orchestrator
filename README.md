# Reporker

Ansible orchestration: discover GitLab projects with **`glab`**, clone/update with **`git`**, scan repos for targets, run a **pluggable action**, write reports, then optionally branch / commit / push.

Reporker does **not** merge, open merge requests, or change default branches.

## Requirements

- `ansible`, `git`, `glab`, `jq`
- SSH keys for GitLab Git operations
- API token file for `glab` discovery (see `glab/README.md`)

## Layout

```
reporker/
├── ansible/
│   ├── ansible.cfg
│   ├── playbooks/run.yml
│   ├── group_vars/all/reporker.yml   # all configuration
│   ├── actions/                      # pluggable actions (per-folder tasks)
│   ├── roles/
│   │   ├── discovery/
│   │   ├── workspace/
│   │   ├── scan/
│   │   ├── action/
│   │   ├── report/
│   │   └── publish/
│   ├── workspace/                    # clones (gitignored except .keep)
│   └── reports/                      # JSON outputs (gitignored except .keep)
├── glab/                             # token + generated repos.txt (see README there)
├── my-notes/                         # design notes (optional)
└── README.md
```

## Configuration

Edit **`ansible/group_vars/all/reporker.yml`**:

- `hamgit.host`, `hamgit.group_id`, `hamgit.token_file`
- `paths.workspace`, `paths.reports`
- `git.branch_name`, `git.commit_message`
- `action.name`, `action.target_patterns`, `action.params`

Actions live under `ansible/actions/<name>/tasks/main.yml`. See `ansible/actions/README.md`.

## Run

From `ansible/`:

```bash
cd ansible
```

Phases (tags): `discovery` → `workspace` → `scan` → `action` → `report` → `publish`

```bash
ansible-playbook -i localhost, playbooks/run.yml --tags discovery
ansible-playbook -i localhost, playbooks/run.yml --tags workspace
ansible-playbook -i localhost, playbooks/run.yml --tags scan,action,report
```

Full pipeline:

```bash
ansible-playbook -i localhost, playbooks/run.yml --tags discovery,workspace,scan,action,report,publish
```

`glab` must be authenticated for your host, for example:

```bash
cat glab/hamgit-token | glab auth login --hostname hamgit.ir --stdin
```

## Reports

Written under `ansible/reports/` (when those phases run), including `repos.json`, `scan.json`, `action.json`, `report.json`, `changed.json`, `publish.json`.

Use a **fresh `git.branch_name` per run** if you publish often, so remote branch names do not collide.
