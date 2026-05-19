# Actions (pluggable)

Each action is a small Ansible task file tree included by the `action` role after the **scan** phase.

## Layout

```
ansible/actions/<name>/tasks/main.yml
```

Optionally add `defaults/main.yml` in the same folder if you use a role-style layout (not auto-loaded unless you include_role; for `include_tasks` only `tasks/main.yml` runs).

## Configuration

In `ansible/group_vars/all/reporker.yml`:

```yaml
action:
  name: my-action          # loads ansible/actions/my-action/tasks/main.yml
  target_patterns: []      # globs for scan (ansible.builtin.find)
  params: {}               # your knobs; available as `action.params`
```

Override the path entirely:

```yaml
action:
  tasks_file: "{{ playbook_dir }}/../actions/custom/tasks/main.yml"
  name: custom
  target_patterns: ["**/*.example"]
  params: {}
```

## Variables your tasks receive

| Variable | Description |
|----------|-------------|
| `paths.workspace` | Root directory containing one folder per cloned repo |
| `paths.reports` | Report output directory |
| `targets_by_repo` | Dict: absolute repo dir → list of target file paths |
| `repos_with_targets` | Repo dirs that have at least one target |
| `all_targets` | Flattened list of all target files |
| `action` | Full action dict from group_vars (`name`, `target_patterns`, `params`, …) |
| `git`, `hamgit` | As configured in group_vars |

## What your tasks must set

| Fact | Required |
|------|----------|
| `changed_files` | Yes — list of absolute paths modified by this action (empty list if nothing changed) |

The `action` role aggregates `changed_files` into `changed_targets_by_repo`, `changed_repos`, and `ansible/reports/action.json`.

## Bundled examples

| Name | Purpose |
|------|---------|
| `noop` | Does nothing; safe default for wiring tests |
| `line-append` | Idempotent `lineinfile` using `action.params.ensure_line` |

## Adding a new action

1. Create `ansible/actions/<name>/tasks/main.yml`.
2. Set `action.name: <name>` and `action.target_patterns` in `group_vars/all/reporker.yml`.
3. Implement idempotent tasks and set `changed_files` when you touch files.

Run only your stack while developing:

```bash
cd ansible
ansible-playbook -i localhost, playbooks/run.yml --tags scan,action
```
