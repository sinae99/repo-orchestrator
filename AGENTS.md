# AGENTS.md — instructions for AI agents working in this repo

You are helping a human run **reporker**: scan and change files across every
repo in a GitLab group. The human describes the change; you build (or reuse)
an action + recipe, verify offline, and hand them the commands to run.

**Read this file first. Follow it exactly.**

---

## What reporker is

```
GitLab group → clone → scan → action → report → (optional) publish
```

| Layer | Responsibility |
|---|---|
| Engine (`ansible/roles/`) | Discovery, clone, scan, report, publish — **do not edit** |
| Actions (`ansible/actions/<name>/`) | Pluggable logic on matched files |
| Recipes (`recipes/<name>.yml`) | Named, committed configs: action + patterns + params + git |
| Config (`ansible/group_vars/all.yml`) | Where: host, group_id, token — **do not edit for tasks** |

CLI entry point: `./reporker`. Offline loop needs no token and no network.

---

## Decision tree

1. Restate the request as: **which files**, **across which repos**, **read or write**.
2. Run `./reporker list`.
3. **Existing action fits?** → write only a recipe under `recipes/`.
4. **No fit?** → copy the template, write the action + `meta.yml`, then a recipe.
5. Verify: `./reporker validate <action>` then `./reporker test --recipe <recipe>`.
6. Hand the user the commands below. Do **not** run `clone`, `publish`, or `all`.

---

## Recipe format

```yaml
# recipes/bump-python.yml
recipe:
  summary: Bump Python base image 3.9 → 3.12

reporker_action:
  name: replace                 # must exist under ansible/actions/
  target_patterns:
    - "Dockerfile"
  params:
    regexp: "^FROM python:3\\.9"
    replace: "FROM python:3.12"

# Required for write actions that will publish:
git:
  branch_name: "reporker-bump-python-{{ lookup('pipe', 'date +%Y%m%d') }}"
  commit_message: "chore: bump python base image to 3.12"
```

Rules:

- Carry the **complete** `reporker_action` block (extra-vars replace the dict).
- Never put credentials, host, or `group_id` in a recipe.
- Never edit `ansible/group_vars/all.yml` to switch tasks — write a recipe.
- Name the file after the change (`bump-python.yml`), not the action.
- Quote YAML strings that contain `:` (e.g. `summary: "Find image: latest"`).

Run: `./reporker action --recipe bump-python`

---

## Building a new action

```bash
cp -r ansible/actions/_template ansible/actions/my-action
```

Then edit:

1. `ansible/actions/my-action/meta.yml`
2. `ansible/actions/my-action/tasks/main.yml`
3. `recipes/<change-name>.yml`

### meta.yml

```yaml
---
action:
  name: my-action
  mode: write                 # read | write — drives report mode + change detection
  summary: One-line description.
  params:
    - name: regexp
      required: true
      description: Pattern for ansible.builtin.replace
  # Optional — smarter targeting than a glob:
  # scan_filter: tasks/scan_filter.yml
  # scan_note: "short note shown in 01-summary.txt scope line"
  example_recipe: recipes/my-change.yml
```

`mode: write` is required for any action that edits files. Without it, publish
sees "no changes".

### Contract (`tasks/main.yml`)

1. Header: `# Action: <name> (read|write)`
2. Set `changed_files` — `[]` for read; absolute paths you changed for write
3. Write `03-action.json` via `_shared/tasks/write_action_report.yml`
4. Respect `--dry-run` / check mode
5. Add a recipe example under `recipes/`

Engine variables you receive:

| Variable | Meaning |
|---|---|
| `all_targets` | matched files (absolute paths) |
| `targets_by_repo` | `repo → [files]` — includes empty repos |
| `repos_with_targets` | repos with ≥1 match |
| `reporker_action.params` | your `params:` |
| `paths.reports` | report dir |

Scan matches **hidden files** (e.g. `.gitlab-ci.yml`). Patterns are globs,
not path regexes.

### Check-mode rule (critical)

Modules like `lineinfile` / `replace` / `copy` honor check mode automatically.

**Shell / command / custom scripts do NOT.** Guard them:

```yaml
# CORRECT
- name: My action | mutate via script
  ansible.builtin.command:
    argv: ["python3", "script.py", item]
  loop: "{{ all_targets }}"
  when: not ansible_check_mode

# WRONG — silently edits files under --dry-run / ./reporker test pass 1
- name: My action | mutate via script
  ansible.builtin.shell: "sed -i 's/a/b/' {{ item }}"
  loop: "{{ all_targets }}"
```

`./reporker test` fails the run if fixtures are dirty after `--check`.

### Minimal read action sketch

```yaml
---
# Action: my-action (read)

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

### Minimal write action sketch

```yaml
---
# Action: my-action (write)

- name: My action | edit each target
  ansible.builtin.replace:
    path: "{{ item }}"
    regexp: "{{ reporker_action.params.regexp }}"
    replace: "{{ reporker_action.params.replace }}"
  loop: "{{ all_targets }}"
  register: _results

- name: My action | set changed_files
  ansible.builtin.set_fact:
    changed_files: >-
      {{
        _results.results
        | selectattr('changed', 'defined')
        | selectattr('changed', 'equalto', true)
        | map(attribute='item')
        | list
      }}

- name: My action | build report
  ansible.builtin.set_fact:
    _action_report:
      summary:
        files_scanned: "{{ all_targets | length }}"
        files_changed: "{{ changed_files | length }}"
      changed_files: "{{ changed_files }}"

- name: My action | write 03-action.json
  ansible.builtin.include_tasks: "{{ playbook_dir }}/../actions/_shared/tasks/write_action_report.yml"
```

Helpers: `ansible/actions/_shared/`. Longer human docs: `docs/README.md`.

---

## Mandatory verification

Before handing off, **both** must pass:

```bash
./reporker validate <action-name>
./reporker test --recipe <recipe-name>
```

Read the printed `01-summary.txt` and fixture diffs. Fix until clean.
Do not invent success — if test fails, fix the action/recipe and re-run.

---

## Handoff block (copy verbatim to the user)

```bash
./reporker check
./reporker clone
./reporker action --recipe <recipe-name> --dry-run
./reporker action --recipe <recipe-name>
./reporker publish
```

For read-only recipes, stop after `action` (no publish).

Remind the user: one-time setup is `./reporker init`, edit
`ansible/group_vars/all.yml` (host + group_id), and
`printf '%s' 'glpat-xxx' > glab/token && chmod 600 glab/token`.

---

## Guardrails

**Never:**

- Edit `ansible/roles/**` (engine)
- Edit `ansible/group_vars/all.yml` to switch tasks
- Edit `glab/` or `ansible/workspace/**`
- Run `clone`, `publish`, or `all`
- Commit a token or real host credentials
- Invent new report filenames (use slots 01–08)

**Always:**

- Prefer an existing action + new recipe over a new action
- Set `mode: write` in `meta.yml` for write actions
- Honor check mode
- Verify with `validate` + `test` before handoff

---

## File map

```
reporker                          CLI
AGENTS.md                         this file (agent entry point)
README.md                         how to use (short)
docs/README.md                    recipes, actions, catalogues
recipes/                          committed task configs
ansible/
  actions/<name>/
    meta.yml                      mode, summary, params, optional scan_filter
    tasks/main.yml                the action
  actions/_template/              copy this to start a new action
  actions/_shared/                helpers (write report, detect changes, load meta)
  roles/                          engine — do not edit
  group_vars/all.yml.example      where-config template
  playbooks/run.yml               single playbook, tagged phases
tests/
  fixtures/repos/                 fake repos for offline test
  fixture-config.yml              config for ./reporker test
  validate_action.py              contract linter
```

Reports after a run (start with `01-summary.txt`):

| # | File | What |
|---|---|---|
| 01 | `01-summary.txt` | start here |
| 02 | `02-breakdown.json` | optional (priorityclass) |
| 03 | `03-action.json` | your action's output |
| 04 | `04-scan.json` | scan matches |
| 05 | `05-changed.json` | changed files (write) |
| 06 | `06-run.json` | full run record |
