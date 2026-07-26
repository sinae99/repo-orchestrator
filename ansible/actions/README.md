# Actions

An **action** is what runs on the files the scan found.

reporker handles discovery, cloning, and scanning. Your action either reports (read) or changes files (write). Write actions can `publish`.

```
scan → action → report → (optional) publish
```

## run

1. Copy a config below into `ansible/group_vars/all.yml`
2. `./reporker clone && ./reporker action`
3. Open `ansible/reports/01-summary.txt`

```bash
./reporker action --dry-run   # preview write actions
./reporker publish            # branch + push per changed repo
```

## copy-paste configs

**Every Dockerfile:**

```yaml
reporker_action:
  name: inventory
  target_patterns:
    - "Dockerfile"
    - "Dockerfile.*"
```

**Find `image: latest`:**

```yaml
reporker_action:
  name: grep
  target_patterns:
    - "*.yaml"
    - "*.yml"
  params:
    pattern: "image:\\s*latest"
```

**Repos with no `.gitlab-ci.yml`:**

```yaml
reporker_action:
  name: missing-file
  target_patterns:
    - ".gitlab-ci.yml"
```

**PriorityClass cleanup:**

```yaml
reporker_action:
  name: priorityclass
  target_patterns:
    - "*.yaml"
    - "*.yml"

git:
  branch_name: "reporker-priorityclass-{{ lookup('pipe', 'date +%Y%m%d') }}"
  commit_message: "chore: drop medium/low requests and add priorityClassName medium where missing"
```

**Ensure a line in requirements.txt:**

```yaml
reporker_action:
  name: line-append
  target_patterns:
    - "requirements.txt*"
  params:
    ensure_line: "# managed by reporker"
    insertafter: EOF
```

**Bump a base image:**

```yaml
reporker_action:
  name: replace
  target_patterns:
    - "Dockerfile"
  params:
    regexp: "^FROM python:3\\.9"
    replace: "FROM python:3.12"
```

**Roll out CODEOWNERS:**

```yaml
reporker_action:
  name: ensure-file
  target_patterns:
    - "CODEOWNERS"
  params:
    path: CODEOWNERS
    content: |
      * @your-team
    overwrite: false
```

## built-in

| Name | | Params |
|---|---|---|
| `inventory` | read | — |
| `grep` | read | `pattern`, `ignore_case` |
| `missing-file` | read | — |
| `noop` | read | — |
| `priorityclass` | write | `drop_requests_for`, `ensure_priority_class`, `missing_priority_class` |
| `line-append` | write | `ensure_line`, `insertafter` |
| `replace` | write | `regexp`, `replace` |
| `ensure-file` | write | `path`, `content` or `src`, `overwrite`, `mode` |

## write your own

```bash
cp -r ansible/actions/_template ansible/actions/my-action
```

Engine vars you get:

| Variable | Meaning |
|---|---|
| `all_targets` | matched files (absolute paths) |
| `targets_by_repo` | `repo → [files]` — includes empty repos |
| `repos_with_targets` | repos with ≥1 match |
| `reporker_action.params` | your `params:` |
| `paths.reports` | report dir |

Contract:

1. **Set `changed_files`** — `[]` for read; absolute paths you changed for write
2. **Write `03-action.json`** via `_shared/tasks/write_action_report.yml`
3. **Respect `--dry-run`** — modules like `lineinfile` / `replace` / `copy` handle check mode; shell needs `when: not ansible_check_mode`
4. **Header** — `# Action: <name> (read|write)`
5. **Example** — add a copy-paste block to `ansible/group_vars/all.yml.example`

```yaml
- name: My action | build report
  ansible.builtin.set_fact:
    _action_report:
      summary:
        total_files: "{{ all_targets | length }}"

- name: My action | write 03-action.json
  ansible.builtin.include_tasks: "{{ playbook_dir }}/../actions/_shared/tasks/write_action_report.yml"

- name: My action | set changed_files
  ansible.builtin.set_fact:
    changed_files: []
```

Or point at any tasks file:

```yaml
reporker_action:
  tasks_file: /abs/path/to/tasks.yml
```

Report slots (don't invent new names):

| File | Who |
|---|---|
| `01-summary.txt` | report phase |
| `02-breakdown.json` | priorityclass |
| `03-action.json` | **your action** |
| `04-scan.json` | scan |
| `05-changed.json` | report |
| `06-run.json` | report |

Helpers: [`_shared/`](_shared/). Template: [`_template/`](_template/).
