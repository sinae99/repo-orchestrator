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

## What it helps with

Things I've used it for (and things it maps to easily):

- **Inventory audits** — list every `Dockerfile`, `docker-compose.yml`, or Helm chart in a group
- **K8s manifest grep-at-scale** — find manifests with a specific `priorityClassName`, missing resource limits, old API versions, etc.
- **Bulk text changes** — add a line to every `requirements.txt`, pin a base image comment, stamp a managed-by header
- **Pre-migration checks** — before you change something platform-wide, see exactly which repos are affected
- **Compliance sweeps** — search for patterns (`password:`, `image: latest`, deprecated annotations) across the whole group

Read-only actions give you a report and stop. Write actions can open a branch per changed repo.

---

## Quick start

```bash
git clone https://github.com/you/reporker.git && cd reporker

./reporker init
# edit ansible/group_vars/all.yml — host, group_id, action

printf '%s' 'glpat-xxx' > glab/token && chmod 600 glab/token
cat glab/token | glab auth login --hostname gitlab.com --stdin

./reporker clone
./reporker action
```

Reports go to `ansible/reports/`. For audits that's usually enough.

To push changes:

```bash
./reporker publish
```

---

## Commands

| Command | Does |
|---|---|
| `./reporker init` | Create local config from the example |
| `./reporker clone` | Discover repos + clone/update |
| `./reporker scan` | Find target files only |
| `./reporker action` | Scan, run action, write reports |
| `./reporker publish` | Branch, commit, push changed repos |
| `./reporker run` | clone → action, no push |
| `./reporker all` | Full pipeline including publish |

`./reporker --help` for details.

---

## Config

`ansible/group_vars/all.yml` — created by `init`, gitignored:

```yaml
gitlab:
  host: gitlab.com
  group_id: 12345
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

---

## Examples

**Every Dockerfile in the group:**

```yaml
reporker_action:
  name: inventory
  target_patterns: ["Dockerfile", "Dockerfile.*"]
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

Then `./reporker action && ./reporker publish`.

---

## Built-in actions

| Action | | What |
|---|---|---|
| [`inventory`](ansible/actions/inventory/) | read | Matched files per repo |
| [`priorityclass`](ansible/actions/priorityclass/) | read | K8s manifests by priority class |
| [`line-append`](ansible/actions/line-append/) | write | Idempotently adds a line |
| [`noop`](ansible/actions/noop/) | read | Does nothing — useful for wiring |

Need something else? Drop a folder in `ansible/actions/` and point `reporker_action.name` at it. See [`ansible/actions/README.md`](ansible/actions/README.md).

---

## Requirements

- Ansible ≥ 2.14
- [glab](https://gitlab.com/gitlab-org/cli)
- git, jq
- SSH key set up for your GitLab instance (clone/push use SSH; API discovery uses the token)

---

## License

MIT — [LICENSE](LICENSE)
