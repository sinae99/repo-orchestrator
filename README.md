# reporker

Bulk operations across every repository in a GitLab group — find files, run checks, apply changes, and optionally push branches.

**The problem:** You need to audit or update something in dozens of repos — every `Dockerfile`, every manifest with `priorityClassName: low`, every `requirements.txt` missing a pin. Doing that by hand does not scale.

**The answer:** Point reporker at a GitLab group, define what to look for, pick an action. It clones the repos, scans for matches, runs your logic, and writes JSON reports. Write actions can open a branch and push.

```
GitLab group → clone → scan → action → report → (optional) publish
```

---

## Quick start

```bash
git clone https://github.com/you/reporker.git && cd reporker

./reporker init
# edit ansible/group_vars/all.yml — set gitlab.host, gitlab.group_id, reporker_action

printf '%s' 'glpat-xxx' > glab/token && chmod 600 glab/token
cat glab/token | glab auth login --hostname gitlab.com --stdin

./reporker clone      # fetch all repos in the group
./reporker action      # scan + run action + write reports
```

Reports land in `ansible/reports/`. For read-only audits, stop there. To push changes:

```bash
./reporker publish
```

---

## Commands

| Command | What it does |
|---|---|
| `./reporker init` | Create local config from the example |
| `./reporker clone` | Discover repos via GitLab API and clone/update them |
| `./reporker scan` | Find target files only (`scan.json`) |
| `./reporker action` | Scan, run your action, write reports |
| `./reporker publish` | Branch, commit, and push repos that changed |
| `./reporker run` | Full audit/modify flow without push |
| `./reporker all` | Everything including publish |

Run `./reporker --help` for the full list.

---

## Configuration

Copy and edit `ansible/group_vars/all.yml` (created by `reporker init`, gitignored):

```yaml
gitlab:
  host: gitlab.com
  group_id: 12345
  repo_filter: []          # [] = whole group; ["api", "worker"] = subset

reporker_action:
  name: inventory
  target_patterns:
    - "Dockerfile"
    - "Dockerfile.*"
  content_grep: ""         # optional: only files containing this string
  params: {}
```

| Key | Purpose |
|---|---|
| `target_patterns` | File globs to search (recursive) |
| `content_grep` | Narrow matches to files containing this text |
| `name` | Action to run — folder under `ansible/actions/` |
| `params` | Passed to your action as `reporker_action.params` |

---

## Examples

**Find every Dockerfile** (read-only):

```yaml
reporker_action:
  name: inventory
  target_patterns: ["Dockerfile", "Dockerfile.*"]
```

**Find K8s manifests with low/medium priority class:**

```yaml
reporker_action:
  name: priorityclass
  target_patterns: ["*.yaml", "*.yml"]
  content_grep: priorityClassName
  params:
    priority_classes: [medium, low]
```

**Append a line to every `requirements.txt`:**

```yaml
reporker_action:
  name: line-append
  target_patterns: ["requirements.txt*"]
  params:
    ensure_line: "# managed by reporker"
```

Then: `./reporker action && ./reporker publish`

---

## Built-in actions

| Action | Mode | Output |
|---|---|---|
| [`inventory`](ansible/actions/inventory/) | read-only | List of matched files per repo |
| [`priorityclass`](ansible/actions/priorityclass/) | read-only | Manifests by priority class |
| [`line-append`](ansible/actions/line-append/) | write | Idempotently adds a line |
| [`noop`](ansible/actions/noop/) | read-only | Does nothing (for testing) |

See [`ansible/actions/README.md`](ansible/actions/README.md) to add your own.

---

## Requirements

- Ansible ≥ 2.14
- [glab](https://gitlab.com/gitlab-org/cli) (GitLab CLI)
- git, jq
- SSH key configured for your GitLab instance (clone/push)

---

## License

MIT — see [LICENSE](LICENSE).
