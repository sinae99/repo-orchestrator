# Actions

An **action** is the part of reporker you write. The pipeline handles discovery, cloning, and scanning — then runs your action on the matched files. Your action reports on them (read) or changes them (write).

```
scan → action → report → (optional) publish
```

---

## For action authors (humans)

1. **Clone reporker** (or fork it):

```bash
git clone https://github.com/sinae99/repo-orchestrator.git
cd repo-orchestrator
./reporker init
```

2. **Tell your AI agent what to build.** Paste something like:

> Read `ansible/actions/README.md` in this repo. Build a new reporker action named `<my-action>` that `<describe the goal>`. Copy `ansible/actions/_template`, follow the action contract, and wire an example config block in `ansible/group_vars/all.yml.example`.

3. **Test read-only first**, then write with dry-run:

```bash
./reporker clone
./reporker action                    # read-only audit
./reporker action --dry-run          # preview file changes
./reporker action && ./reporker publish
```

---

## For AI agents building actions

Use this section as the source of truth when implementing a new action.

### Layout

```
ansible/actions/<name>/tasks/main.yml
```

Register in config:

```yaml
reporker_action:
  name: <name>
  target_patterns: ["*.yaml"]
  params: {}
```

Or point at any tasks file on disk:

```yaml
reporker_action:
  tasks_file: /abs/path/to/tasks.yml
```

### Inputs (set by the engine before your tasks run)

| Variable | Type | Meaning |
|---|---|---|
| `all_targets` | list | Every matched file (absolute paths) |
| `targets_by_repo` | dict | `repo_path → [file, …]` — includes repos with zero matches |
| `repos_with_targets` | list | Repos that matched at least one file |
| `reporker_action.params` | dict | Your `params:` from config |
| `paths.reports` | string | Report output directory |
| `reporker_report.action` | string | Always `03-action.json` — use this for the dest |

Which files appear in `all_targets` is controlled by config, not your action:

- `target_patterns` — file globs, searched recursively
- `content_grep` — optional regex filter on file contents

### Contract (required)

1. **Set `changed_files`** before finishing:
   - Read-only → `[]`
   - Write → list of absolute paths you actually modified

   Publish uses this to branch and push only changed repos.

2. **Write `03-action.json`** (recommended for read actions, required for write actions):
   - Destination: `{{ paths.reports }}/{{ reporker_report.action }}`
   - Include `"action": "<name>"` and a useful `summary` block
   - Use `to_nice_json` for readable output

   Shortcut — set `_action_report` then include the shared helper:

```yaml
- name: My action | build report
  ansible.builtin.set_fact:
    _action_report:
      summary:
        total_files: "{{ all_targets | length }}"
      files_by_repo: "{{ targets_by_repo }}"

- name: My action | write 03-action.json
  ansible.builtin.include_tasks: "{{ playbook_dir }}/../actions/_shared/tasks/write_action_report.yml"
```

3. **Respect dry-run** — write actions must work with `reporker action --dry-run` (Ansible `--check --diff`). Built-in modules (`lineinfile`, `replace`, `copy`) support check mode. Shell tasks need `when: not ansible_check_mode` for destructive steps.

### Reports (fixed slots — do not invent filenames)

Report names are **the same for every action**. Put the action name inside JSON, not in the filename.

| File | Who writes it | Purpose |
|---|---|---|
| `01-summary.txt` | report phase | Human entry point |
| `02-breakdown.json` | priority actions only | Pod priority split |
| `03-action.json` | **your action** | Action-specific results |
| `04-scan.json` | scan phase | Matched files per repo |
| `05-changed.json` | report phase | Changed files for publish |
| `06-run.json` | report phase | Full run record |
| `07-meta.json` | engine | Action metadata |
| `08-publish.json` | publish phase | Push results |

Each run clears previous numbered artifacts (`0*.json`, `0*.txt`). `repos.json` (discovery cache) is kept.

### Starter template

```bash
cp -r ansible/actions/_template ansible/actions/my-action
```

Edit `ansible/actions/my-action/tasks/main.yml`, then:

```yaml
reporker_action:
  name: my-action
  target_patterns: ["*.tf"]
  params:
    foo: bar
```

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

- name: My action | write 03-action.json
  ansible.builtin.set_fact:
    _action_report:
      summary:
        files_changed: "{{ changed_files | length }}"
      changed_files: "{{ changed_files }}"

- name: My action | write report file
  ansible.builtin.include_tasks: "{{ playbook_dir }}/../actions/_shared/tasks/write_action_report.yml"
```

### Checklist before finishing

- [ ] `changed_files` is set (even if empty)
- [ ] `03-action.json` written via `reporker_report.action`
- [ ] Params validated with `assert` when required
- [ ] Write actions tested with `--dry-run`
- [ ] Example config added to `ansible/group_vars/all.yml.example`
- [ ] Header comment: `# Action: <name> (read|write)`

---

## Built-in actions

| Name | Mode | Description |
|---|---|---|
| [`inventory`](inventory/) | read | Matched files per repo, with counts |
| [`grep`](grep/) | read | Matching lines (with line numbers) per file |
| [`priorityclass`](priorityclass/) | read | Manifests by effective priority + breakdown |
| [`priorityclass-drop-requests`](priorityclass-drop-requests/) | write | Drop requests from medium/low pods |
| [`missing-file`](missing-file/) | read | Repos missing a target file |
| [`line-append`](line-append/) | write | Idempotently ensures a line exists |
| [`replace`](replace/) | write | Regex find-and-replace |
| [`ensure-file`](ensure-file/) | write | Creates a standard file if missing |
| [`noop`](noop/) | read | Does nothing — wiring/testing default |

Shared helpers live in [`_shared/`](_shared/) (`write_action_report.yml`, `priority_breakdown.yml`, `clear_reports.yml`).
