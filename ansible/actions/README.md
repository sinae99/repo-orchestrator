# Actions

An action is the part of reporker you write. The pipeline does the boring work — discover repos, clone them, find the files you care about — and then hands those files to your action. Your action decides what to do with them: report on them, or change them.

```
scan (finds files) → action (your logic) → report → publish
```

If you can write a few lines of Ansible, you can write an action. If you can copy-paste, you can still write an action.

## Layout

```
ansible/actions/<name>/tasks/main.yml
```

Pick the action by name in `ansible/group_vars/all.yml`:

```yaml
reporker_action:
  name: <name>
```

You can also point at any tasks file directly, anywhere on disk:

```yaml
reporker_action:
  tasks_file: /abs/path/to/tasks.yml
```

## What your action receives

By the time your tasks run, these variables are already set for you:

| Variable | Type | What it is |
|---|---|---|
| `all_targets` | list | Every matched file across all repos (flat list of absolute paths) |
| `targets_by_repo` | dict | `repo_path → [file, …]`. Includes repos with an empty list, so you can see what is missing too |
| `repos_with_targets` | list | Repo paths that matched at least one file |
| `reporker_action.params` | dict | Whatever you put under `params:` in the config |
| `paths.reports` | string | Where to write your JSON report |

Which files land in `all_targets` is controlled entirely by config, not by your action:

- `target_patterns` — file globs, searched recursively in every repo
- `content_grep` — optional regex; only files whose contents match are kept

So the same action works on Dockerfiles, YAML manifests, `requirements.txt`, or anything else — you just change the patterns.

## The one rule: set `changed_files`

Every action must end by setting `changed_files` — the list of files it modified.

- Read-only action? Set it to `[]`.
- Write action? Set it to the files you actually changed.

This is what the `publish` phase uses to decide which repos to branch and push. If you forget it, nothing gets published.

```yaml
- name: set changed_files (read-only)
  ansible.builtin.set_fact:
    changed_files: []
```

## Writing a report (recommended)

Read-only actions earn their keep by writing a report. The convention is one JSON file per action:

```
ansible/reports/<numbered-report>
```

Use `to_nice_json` so it is human-readable:

```yaml
- name: write my-action.json
  ansible.builtin.copy:
    dest: "{{ paths.reports }}/{{ reporker_report.action }}"
    mode: "0644"
    content: |
      {{
        {
          "action": "my-action",
          "summary": { "files": all_targets | length },
          "files": all_targets
        } | to_nice_json
      }}
```

## Dry run

Write actions should behave under `reporker action --dry-run` (Ansible `--check --diff`). The built-in modules (`lineinfile`, `replace`, `copy`) already support check mode and will show a diff without touching files. If you shell out, guard real changes with `when: not ansible_check_mode`.

## Built-in actions

| Name | Mode | Description |
|---|---|---|
| [`inventory`](inventory/) | read | Lists matched files per repo, with counts and the repos that matched nothing |
| [`grep`](grep/) | read | Records matching lines (with line numbers) per file — compliance sweeps |
| [`priorityclass`](priorityclass/) | read | Manifests grouped by effective priority (missing → medium) + breakdown report |
| [`priorityclass-drop-requests`](priorityclass-drop-requests/) | write | Drop requests from medium/low pods (missing class = medium) |
| [`missing-file`](missing-file/) | read | Repos that do NOT contain a target file — governance audits |
| [`line-append`](line-append/) | write | Idempotently ensures a line exists in each file |
| [`replace`](replace/) | write | Regex find-and-replace across matched files |
| [`ensure-file`](ensure-file/) | write | Creates a standard file in every repo if missing |
| [`noop`](noop/) | read | Does nothing — safe default for wiring/testing |

## Add your own

1. Copy the template:

```bash
cp -r ansible/actions/_template ansible/actions/my-action
```

2. Edit `ansible/actions/my-action/tasks/main.yml`.
3. Point the config at it and pick your patterns:

```yaml
reporker_action:
  name: my-action
  target_patterns: ["*.tf"]
  params:
    foo: bar
```

4. Test it (read-only first, or with `--dry-run`):

```bash
reporker scan        # see what gets matched (ansible/reports/03-scan.json or 04-scan.json)
reporker action      # run your action
```

The [`_template`](_template/) action is a fully commented starting point. The shortest possible real action looks like this:

```yaml
- name: My action | ensure a line in each target
  ansible.builtin.lineinfile:
    path: "{{ item }}"
    line: "# touched by reporker"
    state: present
  loop: "{{ all_targets }}"
  register: my_results

- name: My action | report what changed
  ansible.builtin.set_fact:
    changed_files: >-
      {{
        my_results.results
        | selectattr('changed', 'equalto', true)
        | map(attribute='item')
        | list
      }}
```
