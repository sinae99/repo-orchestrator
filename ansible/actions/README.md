# Actions

An action is the pluggable step that runs after the scan phase. reporker finds the target files; your action decides what to do with them.

## Layout

```
ansible/actions/
└── <name>/
    └── tasks/
        └── main.yml
```

## Activating an action

In `ansible/group_vars/all/reporker.yml`:

```yaml
action:
  name: my-action            # loads ansible/actions/my-action/tasks/main.yml
  target_patterns:
    - "Dockerfile*"          # globs for ansible.builtin.find (recurse=true)
  params:                    # arbitrary dict — available as action.params in tasks
    my_key: my_value
```

## Variables your tasks receive

| Variable | Type | Description |
|---|---|---|
| `all_targets` | list | Flat list of every file matched by `action.target_patterns` |
| `targets_by_repo` | dict | `repo_path → [file, …]` |
| `repos_with_targets` | list | Repo dirs that have at least one matched file |
| `action` | dict | The full action block from config (`name`, `target_patterns`, `params`) |
| `paths` | dict | `workspace` and `reports` paths |
| `git` | dict | Branch name and commit message |
| `gitlab` | dict | Host, group ID, and repo filter |

## What your tasks must set

| Fact | Required | Description |
|---|---|---|
| `changed_files` | **yes** | List of absolute paths modified by this action. Set to `[]` for read-only actions. |

The `action` role aggregates `changed_files` into `changed_targets_by_repo`, `changed_repos`, and `ansible/reports/action.json`. The `publish` role then uses `changed_repos` to branch/commit/push.

## Bundled actions

| Name | Mode | Description |
|---|---|---|
| [`noop`](noop/) | read-only | Does nothing — safe default for wiring and dry runs |
| [`line-append`](line-append/) | write | Idempotent `lineinfile` using `action.params.ensure_line` |
| [`priorityclass`](priorityclass/) | read-only | Finds K8s manifests with `priorityClassName: medium` or `low` |

## Adding a new action

1. Create `ansible/actions/<name>/tasks/main.yml`.
2. Set `action.name: <name>` and `action.target_patterns` in config.
3. Implement idempotent tasks; set `changed_files` when done.

```yaml
# ansible/actions/my-action/tasks/main.yml

- name: My action | do something to each target
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
```

Develop iteratively with just the scan and action phases:

```bash
cd ansible
ansible-playbook -i localhost, playbooks/run.yml --tags scan,action
```
