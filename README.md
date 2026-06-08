# reporker

I built this because I faced this problem many  times: **something needs to happen across a whole GitLab group**, and doing it repo by repo is crazy.

Maybe I need to add user to every `Dockerfile`. 

Maybe I need every K8s manifest that sets `priorityClassName: low` before a scheduling policy change.

Maybe compliance asks "which services still run `image: latest`?" and nobody wants to click through 80 repos.

*reporker* handles that.

Point it at a group, tell it what files to look for, pick an action. It clones everything, scans, runs your logic, and writes JSON reports. If the action actually changes files, it can branch and push for you.

```
GitLab group → clone → scan → action → report → (optional) publish
```

Works with gitlab.com or self-hosted. One config file, one CLI.

---

## How it helps

Things I've used it for :

- **Inventory audits** — list every `Dockerfile`, `docker-compose.yml`, or any file in a group
- **K8s manifest grep-at-scale** — find manifests with a specific `priorityClassName`, missing resource limits, old API versions, etc.
- **text changes** — add a line to every `requirements.txt`, pin a base image comment.
- **Compliance sweeps** — search for patterns (`password:`, `image: latest`) across the whole group

Read-only actions give you a report and stop. Write actions can open a branch per changed repo.

---

## Quick start

```bash
git clone https://github.com/sinae99/repo-orchestrator.git && cd repo-orchestrator

./reporker init
# edit ansible/group_vars/all.yml — host, group_id, action

printf '%s' 'glpat-xxx' > glab/token && chmod 600 glab/token

./reporker doctor      # confirm everything is wired up
./reporker clone
./reporker action
```

The token file is the only auth step — reporker hands it to `glab` for you, so there is no separate login.

Reports go to `ansible/reports/`. For audits that's usually enough.

To push changes:

```bash
./reporker action --dry-run    # preview first
./reporker publish
```

---

## Commands

| Command | Does |
|---|---|
| `./reporker init` | Create local config from the example |
| `./reporker doctor` | Check tools, config, and token are ready |
| `./reporker clone` | Discover repos + clone/update |
| `./reporker scan` | Find target files only |
| `./reporker action` | Scan, run action, write reports |
| `./reporker publish` | Branch, commit, push changed repos |
| `./reporker run` | clone → action, no push |
| `./reporker all` | Full pipeline including publish |

Flags:

- `--dry-run` — preview a write action without touching files (Ansible `--check --diff`); reports are still written
- `-- <args>` — anything after `--` goes straight to `ansible-playbook`, e.g. `./reporker action -- -e reporker_action.name=grep`

`./reporker --help` for details.

---

## Config

`ansible/group_vars/all.yml` — created by `init`, gitignored:

```yaml
gitlab:
  host: gitlab.com
  group_id: 12345          # change this to your real group ID
  repo_filter: []          # empty = whole group; or ["api", "worker"]

reporker_action:
  name: inventory
  target_patterns:
    - "Dockerfile"
    - "Dockerfile.*"
  content_grep: ""         # optional — only files containing this string
  params: {}
```

- `target_patterns` — file globs, searched recursively in each repo
- `content_grep` — narrows results further (e.g. `priorityClassName`)
- `name` — action to run, lives in `ansible/actions/<name>/`
- `params` — whatever your action needs

The example config (`ansible/group_vars/all.yml.example`) has a ready-to-paste block for every built-in action.

---

## Example Actions

**Every Dockerfile in the group:**

```yaml
reporker_action:
  name: inventory
  target_patterns: ["Dockerfile", "Dockerfile.*"]
```

**Find every manifest still using `image: latest`:**

```yaml
reporker_action:
  name: grep
  target_patterns: ["*.yaml", "*.yml"]
  params:
    pattern: "image:\\s*latest"
```

**Which repos have no `.gitlab-ci.yml`:**

```yaml
reporker_action:
  name: missing-file
  target_patterns: [".gitlab-ci.yml"]
```

**Manifests using low/medium priority class:**

```yaml
reporker_action:
  name: priorityclass
  target_patterns: ["*.yaml", "*.yml"]
  content_grep: priorityClassName
  params:
    priority_classes: [medium, low]
```

**Add a line to all requirements.txt files:**

```yaml
reporker_action:
  name: line-append
  target_patterns: ["requirements.txt*"]
  params:
    ensure_line: "# managed by reporker"
```

**Bump a base image everywhere:**

```yaml
reporker_action:
  name: replace
  target_patterns: ["Dockerfile"]
  params:
    regexp: "^FROM python:3\\.9"
    replace: "FROM python:3.12"
```

**Drop a CODEOWNERS into every repo that lacks one:**

```yaml
reporker_action:
  name: ensure-file
  target_patterns: ["CODEOWNERS"]
  params:
    path: CODEOWNERS
    content: |
      * @your-team
```

Then `./reporker action && ./reporker publish` (or add `--dry-run` to preview first).

---

## Built-in actions

| Action | | What |
|---|---|---|
| [`inventory`](ansible/actions/inventory/) | read | Matched files per repo, with counts |
| [`grep`](ansible/actions/grep/) | read | Matching lines (with line numbers) per file |
| [`priorityclass`](ansible/actions/priorityclass/) | read | K8s manifests by priority class |
| [`missing-file`](ansible/actions/missing-file/) | read | Repos that do NOT have a target file |
| [`line-append`](ansible/actions/line-append/) | write | Idempotently adds a line |
| [`replace`](ansible/actions/replace/) | write | Regex find-and-replace across files |
| [`ensure-file`](ansible/actions/ensure-file/) | write | Creates a standard file in every repo |
| [`noop`](ansible/actions/noop/) | read | Does nothing — useful for wiring |

Do u need a new action?

Copy the template and point `reporker_action.name` at it:

```bash
cp -r ansible/actions/_template ansible/actions/my-action
```

An action gets the matched files handed to it and only has to set `changed_files` at the end. Full guide: [`ansible/actions/README.md`](ansible/actions/README.md).

---

## Requirements

- Ansible ≥ 2.14
- [glab](https://gitlab.com/gitlab-org/cli)
- git, jq
- SSH key set up for your GitLab instance (clone/push use SSH; API discovery uses the token)

Run `./reporker doctor` and it will tell you what's missing.

---

## Troubleshooting

- **`config not found`** — run `./reporker init` first.
- **`group_id is still the example value`** — edit `ansible/group_vars/all.yml` and set your real numeric group ID.
- **`Token file not found`** — `printf '%s' 'glpat-xxx' > glab/token && chmod 600 glab/token` (token needs `api` scope).
- **Clone or push fails** — clone/push use SSH; make sure your SSH key works: `ssh -T git@<your-host>`.
- **GitLab API unreachable** — discovery caches `ansible/reports/repos.json`; delete it to force a fresh fetch, or keep it to re-filter offline.
- **Want to preview a write action** — `./reporker action --dry-run` shows the diff and writes the report without changing files.

---

## License

MIT — [LICENSE](LICENSE)
