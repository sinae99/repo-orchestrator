# Actions

An action runs after the scan phase. reporker finds target files; your action decides what to do with them.

## Layout

```
ansible/actions/<name>/tasks/main.yml
```

Set `reporker_action.name: <name>` in `ansible/group_vars/all.yml`.

## Variables your tasks receive

| Variable | Description |
|---|---|
| `all_targets` | Every matched file (flat list) |
| `targets_by_repo` | `repo_path → [file, …]` |
| `repos_with_targets` | Repos that have at least one match |
| `reporker_action.params` | Your custom params from config |

## Required output

Set `changed_files` before finishing — list of absolute paths you modified. Use `[]` for read-only actions.

```yaml
- ansible.builtin.set_fact:
    changed_files: []
```

## Built-in actions

| Name | Mode | Description |
|---|---|---|
| [`inventory`](inventory/) | read-only | Lists matched files per repo |
| [`priorityclass`](priorityclass/) | read-only | K8s manifests by priority class |
| [`line-append`](line-append/) | write | Idempotently appends a line |
| [`noop`](noop/) | read-only | Safe default for testing |

## Add your own

1. Create `ansible/actions/<name>/tasks/main.yml`
2. Set `reporker_action.name` and `target_patterns` in config
3. Test with `./reporker action`

```yaml
# ansible/actions/my-action/tasks/main.yml
- name: My action | touch each target
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
