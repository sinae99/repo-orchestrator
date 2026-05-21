# reporker

> Clone, scan, act, report — across every repo in your GitLab group.

Point it at a GitLab group, choose an action, and reporker handles the rest.

---

## How?

```
GitLab API → discovery → workspace → scan → action → report → publish
```

| Phase | Tool | What happens |
|---|---|---|
| `discovery` | glab | Get all repos in the group via the GitLab API |
| `workspace` | git | Clone repos |
| `scan` | Ansible | Find target files in every repo |
| `action` | Ansible | Run pluggable task on every matched file |
| `report` | Ansible | Write JSON reports to `ansible/reports/` |
| `publish` | git | Branch → commit → push for every changed repo |

Run only the phases you need — tag them independently or chain them together.

---

## Requirements

- `ansible` ≥ 2.14
- [`glab`](https://gitlab.com/gitlab-org/cli) (GitLab CLI)
- `git`
- `jq`
- SSH key already configured for your GitLab instance

---

## start

```bash
# 1. Clone reporker repo
git clone <this-repo> reporker && cd reporker

# 2. Store your GitLab personal access token (needs api scope — never committed)
printf '%s' 'glpat-xxxxxxxxxxxx' > glab/token
chmod 600 glab/token

# 3. Authenticate the glab CLI
cat glab/token | glab auth login --hostname gitlab.com --stdin

# 4. Set your host, group ID, and action
vim ansible/group_vars/all/reporker.yml

# 5. Run
cd ansible
ansible-playbook -i localhost, playbooks/run.yml \
  --tags discovery,workspace,scan,action,report
```

---

## Config

All settings are in **`ansible/group_vars/all/reporker.yml`**.

```yaml
gitlab:
  host: gitlab.com           # your GitLab hostname
  group_id: 12345            # numeric group ID
  token_file: "{{ playbook_dir }}/../../glab/token"
  repo_filter: []            # [] = whole group; ["api", "worker"] = only these repos

paths:
  workspace: "{{ playbook_dir }}/../workspace"
  reports:   "{{ playbook_dir }}/../reports"

git:
  branch_name:    "reporker-{{ lookup('pipe', 'date +%Y%m%d') }}"
  commit_message: "chore: reporker automated change"

action:
  name: noop
  # for example :
  target_patterns:
    - "*.yaml"
  params: {}
```

**`repo_filter`** limits which repos inside the group are cloned and scanned. Leave it empty to process the entire group.

---

## Phases

```bash
cd ansible

# Discover + clone only
ansible-playbook -i localhost, playbooks/run.yml --tags discovery,workspace

# Re-run scan/action/report against an already-cloned workspace
ansible-playbook -i localhost, playbooks/run.yml --tags scan,action,report

# Full
ansible-playbook -i localhost, playbooks/run.yml \
  --tags discovery,workspace,scan,action,report,publish
```



## Sample actions

| Action | Mode | Description |
|---|---|---|
| [`noop`](ansible/actions/noop/) | read-only | touches nothing |
| [`line-append`](ansible/actions/line-append/) | write | Idempotently appends a line to every matched file |
| [`priorityclass`](ansible/actions/priorityclass/) | read-only | Finds K8s manifests using `priorityClassName: medium` or `low` |

---

## Writing your own action

1. Create `ansible/actions/<name>/tasks/main.yml`
2. Set `action.name: <name>` in config

Your tasks receive:

| Variable | Description |
|---|---|
| `all_targets` | List of every matched file |
| `targets_by_repo` | Dict: `repo_path → [file, …]` |
| `repos_with_targets` | Repo paths that have at least one match |
| `action.params` | Your custom params from config |

Your tasks **must** set `changed_files` before finishing:

```yaml
- ansible.builtin.set_fact:
    changed_files: []   # absolute paths you modified; [] for read-only actions
```

See [`ansible/actions/README.md`](ansible/actions/README.md) for the full doc.

---

## Reports

Written to `ansible/reports/` after each run:

| File | Contents |
|---|---|
| `repos.json` | Raw GitLab API response |
| `scan.json` | Matched files per repo |
| `action.json` | Changed files summary |
| `report.json` | Full pipeline summary |
| `publish.json` | Branch / push results |

---

## License

MIT — see [LICENSE](LICENSE).
