# Actions

An **action** is the part that actually runs on matched files. 

reporker handles discovery, cloning, and scanning. Your action either reports on what it found (read) or changes files (write).

```
scan → action → report → (optional) publish
```


## how to run an action

1. Edit `ansible/group_vars/all.yml` — pick an action below, copy the block
2. `./reporker clone && ./reporker action`
3. Read `ansible/reports/01-summary.txt`

If it's a write action and you want to push:

```bash
./reporker action
./reporker publish             # branch + push per changed repo
```

Or `./reporker run` (clone through report, no push) / `./reporker all` (includes publish).

---

## Copy-paste configs

Drop one of these into `ansible/group_vars/all.yml` under `reporker_action:`.

**Every Dockerfile in the group:**

```yaml
reporker_action:
  name: inventory
  target_patterns:
    - "Dockerfile"
    - "Dockerfile.*"
```

**Find every manifest still using `image: latest`:**

```yaml
reporker_action:
  name: grep
  target_patterns:
    - "*.yaml"
    - "*.yml"
  params:
    pattern: "image:\\s*latest"
```

**Which repos have no `.gitlab-ci.yml`:**

```yaml
reporker_action:
  name: missing-file
  target_patterns:
    - ".gitlab-ci.yml"
```

**Drop medium/low requests, then add `priorityClassName: medium` where missing**:

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

**Add a line to all requirements.txt files:**

```yaml
reporker_action:
  name: line-append
  target_patterns:
    - "requirements.txt*"
  params:
    ensure_line: "# managed by reporker"
```

## built in

| Name | | Params |
|---|---|---|
| `inventory` | read | — |
| `grep` | read | `pattern`, `ignore_case` |
| `missing-file` | read | — |
| `priorityclass` | write | `drop_requests_for`, `ensure_priority_class` |
| `line-append` | write | `ensure_line`, `insertafter` |
| `replace` | write | `regexp`, `replace` |
| `ensure-file` | write | `path`, `content`, `overwrite` |
| `noop` | read | — |

---

## Writing your own action

tell your AI agent:

> Read `ansible/actions/README.md`. Build a reporker action named `<name>` that `<goal>`. Copy `ansible/actions/_template`, follow the contract below, add an example to `ansible/group_vars/all.yml.example`.

### What the engine gives you

| Variable | Meaning |
|---|---|
| `all_targets` | Every matched file (absolute paths) |
| `targets_by_repo` | `repo_path → [file, …]` — includes repos with zero matches |
| `repos_with_targets` | Repos that matched at least one file |
| `reporker_action.params` | Your `params:` from config |
| `paths.reports` | Where reports go |

Which files land in `all_targets` comes from config — `target_patterns` (globs) and optional `content_grep`. Or point at any tasks file:

```yaml
reporker_action:
  tasks_file: /abs/path/to/tasks.yml
```

### What your action must do

1. **Set `changed_files`** before finishing — `[]` for read-only; list of absolute paths you actually changed for write actions. Publish uses this.

2. **Write `03-action.json`** to `{{ paths.reports }}/{{ reporker_report.action }}`. Shortcut:

```yaml
- name: My action | build report
  ansible.builtin.set_fact:
    _action_report:
      summary:
        total_files: "{{ all_targets | length }}"

- name: My action | write report
  ansible.builtin.include_tasks: "{{ playbook_dir }}/../actions/_shared/tasks/write_action_report.yml"
```

3. **Respect dry-run** — write actions need to work with `./reporker action --dry-run`. Ansible modules like `lineinfile`, `replace`, `copy` handle check mode. Shell tasks need `when: not ansible_check_mode`.

### Minimal write action

```yaml
- name: My action | edit each target
  ansible.builtin.lineinfile:
    path: "{{ item }}"
    line: "# touched by reporker"
    state: present
  loop: "{{ all_targets }}"
  register: my_results

- name: My action | set changed_files
  ansible.builtin.set_fact:
    changed_files: >-
      {{
        my_results.results
        | selectattr('changed', 'equalto', true)
        | map(attribute='item')
        | list
      }}

- name: My action | write report
  ansible.builtin.set_fact:
    _action_report:
      summary:
        files_changed: "{{ changed_files | length }}"
      changed_files: "{{ changed_files }}"

- name: My action | write 03-action.json
  ansible.builtin.include_tasks: "{{ playbook_dir }}/../actions/_shared/tasks/write_action_report.yml"
```

Shared helpers in [`_shared/`](_shared/) — generic utilities for all actions (`write_action_report.yml`, `clear_reports.yml`). Priority-class logic lives only in [`priorityclass/`](priorityclass/).

Report filenames are fixed — don't invent new ones:

| File | Who writes it |
|---|---|
| `01-summary.txt` | report phase |
| `02-breakdown.json` | priority actions |
| `03-action.json` | **your action** |
| `04-scan.json` | scan phase |
| `05-changed.json` | report phase |
| `06-run.json` | report phase |

Before you're done: `changed_files` set, `03-action.json` written, params validated with `assert` if needed, example added to `all.yml.example`, header comment `# Action: <name> (read|write)`.
