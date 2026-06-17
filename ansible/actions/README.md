# Actions

An **action** is the work reporker performs on scanned files—audit (read) or modify (write). The engine handles discovery, cloning, and scanning; you pick or write an action and configure it in `ansible/group_vars/all.yml`.

```
scan → action → report → (optional) publish
```

---

## Run a built-in action

### 1. Choose an action

Pick a recipe below and copy its `reporker_action` block into `ansible/group_vars/all.yml`. Every recipe assumes you have already run `./reporker init`.

### 2. Clone and run

```bash
./reporker clone
./reporker action
```

Reports land in `ansible/reports/`. Start with **`01-summary.txt`**.

### 3. Publish (write actions only)

```bash
./reporker action --dry-run          # preview diffs, no file changes
./reporker action                      # apply changes locally
./reporker publish                     # branch, commit, push per changed repo
```

Or run the full pipeline: `./reporker run` (no push) or `./reporker all` (with push).

---

## Recipes

Copy one block into `ansible/group_vars/all.yml` under `reporker_action:`.

### inventory — list matched files per repo

```yaml
reporker_action:
  name: inventory
  target_patterns:
    - "Dockerfile"
    - "Dockerfile.*"
```

### grep — search file contents group-wide

```yaml
reporker_action:
  name: grep
  target_patterns:
    - "*.yaml"
    - "*.yml"
  params:
    pattern: "image:\\s*latest"
    ignore_case: false
```

Use `content_grep` at the top level to narrow targets before grep runs:

```yaml
reporker_action:
  name: grep
  target_patterns: ["*.yaml", "*.yml"]
  content_grep: "priorityClassName"
  params:
    pattern: "priorityClassName:\\s*low"
```

### missing-file — repos without a required file

```yaml
reporker_action:
  name: missing-file
  target_patterns:
    - ".gitlab-ci.yml"
```

Reports repos that **do not** contain the target file.

### priorityclass — classify K8s manifests by priority tier

Manifests without `priorityClassName` are treated as **medium**.

```yaml
reporker_action:
  name: priorityclass
  target_patterns:
    - "*.yaml"
    - "*.yml"
  params:
    priority_classes:
      - critical
      - high
      - medium
      - low
```

Produces `02-breakdown.json` with pod counts per tier.

### priorityclass-drop-requests — remove requests from medium/low pods

Keeps limits; drops `requests` for pods in the listed tiers (missing class = medium).

```yaml
reporker_action:
  name: priorityclass-drop-requests
  target_patterns:
    - "*.yaml"
    - "*.yml"
  params:
    priority_classes:
      - medium
      - low

git:
  branch_name: "reporker-drop-requests-{{ lookup('pipe', 'date +%Y%m%d') }}"
  commit_message: "chore: remove resource requests from medium/low priority pods"
```

### line-append — ensure a line exists in every matched file

```yaml
reporker_action:
  name: line-append
  target_patterns:
    - "requirements.txt*"
  params:
    ensure_line: "# managed by reporker"
    insertafter: EOF
```

### replace — regex find-and-replace

```yaml
reporker_action:
  name: replace
  target_patterns:
    - "Dockerfile"
  params:
    regexp: "^FROM python:3\\.9"
    replace: "FROM python:3.12"
```

### ensure-file — create a standard file in every repo

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

### noop — wiring test (does nothing)

```yaml
reporker_action:
  name: noop
  target_patterns:
    - "README.md"
```

---

## Action reference

| Name | Mode | Params |
|---|---|---|
| `inventory` | read | — |
| `grep` | read | `pattern` (required), `ignore_case` |
| `missing-file` | read | — |
| `priorityclass` | read | `priority_classes` |
| `priorityclass-drop-requests` | write | `priority_classes` |
| `line-append` | write | `ensure_line`, `insertafter` |
| `replace` | write | `regexp`, `replace` |
| `ensure-file` | write | `path`, `content`, `overwrite` |
| `noop` | read | — |

**Override on the CLI** without editing config:

```bash
./reporker action -- -e reporker_action.name=grep -e 'reporker_action.params={pattern: "image: latest"}'
```

More examples: [`ansible/group_vars/all.yml.example`](../group_vars/all.yml.example)

---

## Write a custom action

```bash
cp -r ansible/actions/_template ansible/actions/my-action
```

Edit `ansible/actions/my-action/tasks/main.yml`, set `reporker_action.name: my-action`, add an example block to `all.yml.example`, then test:

```bash
./reporker clone
./reporker action              # read-only first
./reporker action --dry-run    # preview writes
```

### Contract

Every action must:

1. **Set `changed_files`** before finishing — `[]` for read-only; absolute paths of modified files for write actions. Publish uses this to know which repos to push.

2. **Write `03-action.json`** — destination `{{ paths.reports }}/{{ reporker_report.action }}`. Include `"action": "<name>"` and a useful `summary`. Shortcut:

```yaml
- name: My action | build report
  ansible.builtin.set_fact:
    _action_report:
      summary:
        total_files: "{{ all_targets | length }}"

- name: My action | write report
  ansible.builtin.include_tasks: "{{ playbook_dir }}/../actions/_shared/tasks/write_action_report.yml"
```

3. **Respect dry-run** — write actions must work with `./reporker action --dry-run`. Built-in modules (`lineinfile`, `replace`, `copy`) support check mode. Shell tasks need `when: not ansible_check_mode` for destructive steps.

### Inputs (provided by the engine)

| Variable | Meaning |
|---|---|
| `all_targets` | Every matched file (absolute paths) |
| `targets_by_repo` | `repo_path → [file, …]` — includes repos with zero matches |
| `repos_with_targets` | Repos that matched at least one file |
| `reporker_action.params` | Your `params:` from config |
| `paths.reports` | Report output directory |

Which files appear in `all_targets` is controlled by config:

- `target_patterns` — file globs, recursive search
- `content_grep` — optional regex filter on contents

Or point at any tasks file:

```yaml
reporker_action:
  tasks_file: /abs/path/to/tasks.yml
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

- name: My action | write report
  ansible.builtin.set_fact:
    _action_report:
      summary:
        files_changed: "{{ changed_files | length }}"
      changed_files: "{{ changed_files }}"

- name: My action | write 03-action.json
  ansible.builtin.include_tasks: "{{ playbook_dir }}/../actions/_shared/tasks/write_action_report.yml"
```

Shared helpers: [`_shared/`](_shared/) (`write_action_report.yml`, `priority_breakdown.yml`, `clear_reports.yml`).

---

## For AI agents

When building a new action, use this checklist:

- [ ] Copy `_template` to `ansible/actions/<name>/`
- [ ] Set `changed_files` (even if empty)
- [ ] Write `03-action.json` via `reporker_report.action`
- [ ] Validate required params with `assert`
- [ ] Test write actions with `--dry-run`
- [ ] Add example config to `ansible/group_vars/all.yml.example`
- [ ] Header comment: `# Action: <name> (read|write)`

**Report slots** (fixed filenames — do not invent new ones):

| File | Writer | Purpose |
|---|---|---|
| `01-summary.txt` | report phase | Human entry point |
| `02-breakdown.json` | priority actions | Pod priority split |
| `03-action.json` | **your action** | Action results |
| `04-scan.json` | scan phase | Matched files per repo |
| `05-changed.json` | report phase | Changed files for publish |
| `06-run.json` | report phase | Full run record |

Prompt template for an AI agent:

> Read `ansible/actions/README.md`. Build a reporker action named `<name>` that `<goal>`. Copy `ansible/actions/_template`, follow the contract, and add an example config block to `ansible/group_vars/all.yml.example`.
