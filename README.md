# reporker

i kept needing the same thing across a whole GitLab group — find every `image: latest`, drop some namespace junk, check who has no `.gitlab-ci.yml`. doing that repo by repo with 50–80 services is a joke.

**reporker** points at a group, takes file patterns + an action, then clones, scans, runs your logic, and writes reports. write actions can branch and push.

```
GitLab group → clone → scan → action → report → publish
```

needs: Ansible ≥ 2.14, `glab`, `git`, `jq`.

## start

```bash
git clone https://github.com/sinae99/repo-orchestrator.git && cd repo-orchestrator

./reporker init
# edit ansible/group_vars/all.yml — host, group_id, action

printf '%s' 'glpat-xxx' > glab/token && chmod 600 glab/token

./reporker check
./reporker clone
./reporker action
```

reports land in `ansible/reports/` — start with `01-summary.txt`.

```bash
./reporker action --dry-run   # preview a write action
./reporker publish            # branch + push changed repos
```

## cli

| Command | Does |
|---|---|
| `./reporker init` | config from example |
| `./reporker check` | tools, config, token |
| `./reporker clone` | discover + clone/update |
| `./reporker scan` | find target files |
| `./reporker action` | scan → action → reports |
| `./reporker publish` | branch, commit, push |
| `./reporker run` | clone → action (no push) |
| `./reporker all` | full pipeline + publish |



ansible-playbook:

```bash
./reporker action -- -e reporker_action.name=grep
```

## conf

`ansible/group_vars/all.yml` — from `init`, gitignored:

```yaml
gitlab:
  host: gitlab.com
  group_id: 12345
  repo_filter: []          # empty = whole group

reporker_action:
  name: inventory
  target_patterns:
    - "Dockerfile"
    - "Dockerfile.*"
  content_grep: ""         # optional content filter
  params: {}
```

copy-paste configs for every built-in: [`all.yml.example`](ansible/group_vars/all.yml.example) · [`actions README`](ansible/actions/README.md)

## actions

| Action | | What |
|---|---|---|
| [`inventory`](ansible/actions/inventory/) | read | matched files per repo |
| [`grep`](ansible/actions/grep/) | read | matching lines + line numbers |
| [`missing-file`](ansible/actions/missing-file/) | read | repos missing a target file |
| [`priorityclass`](ansible/actions/priorityclass/) | write | drop medium/low requests, add `priorityClassName: medium` |
| [`line-append`](ansible/actions/line-append/) | write | idempotent line add |
| [`replace`](ansible/actions/replace/) | write | regex find-and-replace |
| [`ensure-file`](ansible/actions/ensure-file/) | write | create a standard file if missing |

`noop` for wiring tests. new action → copy [`_template`](ansible/actions/_template/). full guide: [`ansible/actions/README.md`](ansible/actions/README.md)

`priorityclass` needs PyYAML (`python3 -c 'import yaml'`).

## reports

after `action`, open **`ansible/reports/01-summary.txt`**. fixed names, every run:

| # | File | What |
|---|---|---|
| 01 | `01-summary.txt` | start here |
| 02 | `02-breakdown.json` | priority-class split (when used) |
| 03 | `03-action.json` | action results |
| 04 | `04-scan.json` | scan matches |
| 05 | `05-changed.json` | changed files (write) |
| 06 | `06-run.json` | full run record |

more: [`ansible/reports/README.md`](ansible/reports/README.md)

