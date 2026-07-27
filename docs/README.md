# recipes, actions, reports

this page is the longer explanation. for “just run it”, see the
[main README](../README.md).

```
GitLab group → clone → scan → action → report → publish
```

## action vs recipe

**action** = the tool. ansible code under `ansible/actions/<name>/` that
reads or edits the files the scan found.

examples: `replace`, `grep`, `rename-file`, `priorityclass`.

**recipe** = a saved job under `recipes/<name>.yml`. it picks:

- which action
- which file patterns
- params
- for writes: branch name + commit message

example: `bump-python` says “use `replace` on Dockerfiles, 3.9 → 3.12”.

```
recipes/<name>.yml              →  what (action + patterns + params)
ansible/group_vars/all.yml      →  where (host, group_id, token) — gitignored
```

most of the time you only need a **new recipe**. new **action** only when
none of the existing tools fit.

```bash
./reporker list                  # see both
./reporker action --recipe bump-python
```

## recipes we have

| Recipe | Uses | |
|---|---|---|
| [`list-dockerfiles`](../recipes/list-dockerfiles.yml) | inventory | read |
| [`find-latest-image`](../recipes/find-latest-image.yml) | grep | read |
| [`missing-gitlab-ci`](../recipes/missing-gitlab-ci.yml) | missing-file | read |
| [`bump-python`](../recipes/bump-python.yml) | replace | write |
| [`add-codeowners`](../recipes/add-codeowners.yml) | ensure-file | write |
| [`fix-priorityclass`](../recipes/fix-priorityclass.yml) | priorityclass | write |
| [`rename-dockerfile`](../recipes/rename-dockerfile.yml) | rename-file | write |

### write a recipe

```yaml
# recipes/my-change.yml
recipe:
  summary: one-line description

reporker_action:
  name: replace
  target_patterns:
    - "Dockerfile"
  params:
    regexp: "^FROM python:3\\.9"
    replace: "FROM python:3.12"

git:
  branch_name: "reporker-my-change-{{ lookup('pipe', 'date +%Y%m%d') }}"
  commit_message: "chore: my change"
```

rules:

1. put the full `reporker_action` block (extra-vars replace the whole dict)
2. no credentials / host / group_id in recipes
3. don't edit `all.yml` to switch tasks — write a recipe
4. name the file after the change (`bump-python.yml`), not the action
5. write actions need `git.branch_name` + `git.commit_message`
6. quote strings that contain `:` (e.g. `summary: "Find image: latest"`)

```bash
./reporker validate replace
./reporker test --recipe my-change
```

## actions we have

| Action | | What | Params |
|---|---|---|---|
| [`inventory`](../ansible/actions/inventory/) | read | list matched files per repo | — |
| [`grep`](../ansible/actions/grep/) | read | matching lines + line numbers | `pattern`, `ignore_case` |
| [`missing-file`](../ansible/actions/missing-file/) | read | repos missing a target file | — |
| [`noop`](../ansible/actions/noop/) | read | wiring / scan-only | — |
| [`replace`](../ansible/actions/replace/) | write | regex find-and-replace | `regexp`, `replace` |
| [`line-append`](../ansible/actions/line-append/) | write | add a line if missing | `ensure_line`, `insertafter` |
| [`ensure-file`](../ansible/actions/ensure-file/) | write | create a file if missing | `path`, `content` or `src`, `overwrite`, `mode` |
| [`rename-file`](../ansible/actions/rename-file/) | write | rename via `git mv` | `from`, `to` |
| [`priorityclass`](../ansible/actions/priorityclass/) | write | k8s priorityClass cleanup | `drop_requests_for`, `ensure_priority_class`, … |

`priorityclass` needs PyYAML (`python3 -c 'import yaml'`).

each action has a `meta.yml` (`mode`, `summary`, `params`). that tells the
engine if it's read or write.

### write an action

```bash
cp -r ansible/actions/_template ansible/actions/my-action
```

then:

1. edit `meta.yml` — `name`, `mode: read|write`, `summary`, `params`
2. edit `tasks/main.yml`
3. write a recipe under `recipes/`
4. `./reporker validate my-action && ./reporker test --recipe <change>`

engine gives you:

| Variable | Meaning |
|---|---|
| `all_targets` | matched files (absolute paths) |
| `targets_by_repo` | `repo → [files]` — includes empty repos |
| `repos_with_targets` | repos with ≥1 match |
| `reporker_action.params` | your `params:` |
| `paths.reports` | report dir |

contract:

1. header: `# Action: <name> (read|write)`
2. set `changed_files` — `[]` for read; paths you changed for write
3. write `03-action.json` via `_shared/tasks/write_action_report.yml`
4. respect `--dry-run` — shell/command need `when: not ansible_check_mode`

optional in `meta.yml`:

- `scan_filter: tasks/scan_filter.yml` — smarter targeting than a glob
- `scan_note: "..."` — shown on the summary scope line

ai agents: follow [`AGENTS.md`](../AGENTS.md).

## reports

after `action`, open **`ansible/reports/01-summary.txt`**.

| # | File | What |
|---|---|---|
| 01 | `01-summary.txt` | start here |
| 02 | `02-breakdown.json` | priorityclass only |
| 03 | `03-action.json` | action results |
| 04 | `04-scan.json` | scan matches |
| 05 | `05-changed.json` | changed files (write) |
| 06 | `06-run.json` | full run record |

more: [`ansible/reports/README.md`](../ansible/reports/README.md)
