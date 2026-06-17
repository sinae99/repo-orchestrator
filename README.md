# reporker

**Bulk scan and modify files across every repo in a GitLab group.**

Microservice teams often split code across dozens or hundreds of repositories—one service per repo, shared GitLab groups, independent deploy pipelines. That scale makes group-wide tasks painful: auditing manifests, rolling out a config standard, or answering “which services still use X?” by hand does not scale.

**reporker** automates that. Point it at a GitLab group, define which files matter, pick an action. It discovers repos, clones them, scans, runs your logic, and writes structured reports. Write actions can branch and push changes for you.

```
GitLab group → discover → clone → scan → action → report → (optional) publish
```

Works with gitlab.com or self-hosted GitLab. One config file, one CLI.

---

## Use cases

| Scenario | Example |
|---|---|
| **Fleet inventory** | List every `Dockerfile`, `docker-compose.yml`, or Helm chart in a group |
| **Cross-repo search** | Find K8s manifests with `image: latest`, missing limits, or deprecated API versions |
| **Policy rollout** | Add a line to every `requirements.txt`, bump a base image, drop in `CODEOWNERS` |
| **Compliance sweeps** | Search for sensitive patterns across all services before an audit |
| **Scheduling prep** | Classify pods by `priorityClassName` and adjust resource requests group-wide |

Read-only actions produce reports. Write actions can open a branch per changed repo.

---

## Quick start

```bash
git clone https://github.com/sinae99/repo-orchestrator.git && cd repo-orchestrator

./reporker init
# Edit ansible/group_vars/all.yml — set gitlab.host, gitlab.group_id, and reporker_action

printf '%s' 'glpat-xxx' > glab/token && chmod 600 glab/token

./reporker check
./reporker clone
./reporker action
```

Open **`ansible/reports/01-summary.txt`** first—it tells you what ran and which report to read next.

To apply changes across repos:

```bash
./reporker action --dry-run    # preview without writing files
./reporker publish             # branch, commit, push changed repos
```

Token setup is the only auth step. reporker passes `glab/token` to the GitLab CLI for API discovery; clone and push use SSH.

---

## Commands

| Command | Description |
|---|---|
| `./reporker init` | Create local config from the example |
| `./reporker check` | Verify tools, config, and token |
| `./reporker clone` | Discover repos and clone/update |
| `./reporker scan` | Find target files only |
| `./reporker action` | Scan, run action, write reports |
| `./reporker publish` | Branch, commit, push changed repos |
| `./reporker run` | `clone` → `action` (no push) |
| `./reporker all` | Full pipeline including publish |

**Flags**

- `--dry-run` — preview write actions (`ansible --check --diff`); reports are still written
- `-- <args>` — pass through to `ansible-playbook`, e.g. `./reporker action -- -e reporker_action.name=grep`

Run `./reporker --help` for details.

---

## Configuration

After `./reporker init`, edit `ansible/group_vars/all.yml` (gitignored):

```yaml
gitlab:
  host: gitlab.com
  group_id: 12345          # your GitLab group ID
  repo_filter: []          # empty = all repos; or ["api", "worker"]

reporker_action:
  name: inventory
  target_patterns:
    - "Dockerfile"
    - "Dockerfile.*"
  content_grep: ""         # optional — filter by file content
  params: {}
```

| Key | Purpose |
|---|---|
| `target_patterns` | File globs, searched recursively in each repo |
| `content_grep` | Optional regex — only files containing this string |
| `name` | Built-in action under `ansible/actions/<name>/` |
| `params` | Action-specific options |

**Ready-to-use configs** for every built-in action: [`ansible/group_vars/all.yml.example`](ansible/group_vars/all.yml.example) and the [Actions guide](ansible/actions/README.md).

---

## Built-in actions

| Action | Mode | Description |
|---|---|---|
| [`inventory`](ansible/actions/inventory/) | read | Matched files per repo |
| [`grep`](ansible/actions/grep/) | read | Matching lines with line numbers |
| [`missing-file`](ansible/actions/missing-file/) | read | Repos missing a required file |
| [`priorityclass`](ansible/actions/priorityclass/) | read | Classify manifests by priority tier |
| [`priorityclass-drop-requests`](ansible/actions/priorityclass-drop-requests/) | write | Drop requests from medium/low pods |
| [`line-append`](ansible/actions/line-append/) | write | Idempotently add a line |
| [`replace`](ansible/actions/replace/) | write | Regex find-and-replace |
| [`ensure-file`](ansible/actions/ensure-file/) | write | Create a standard file if missing |
| [`noop`](ansible/actions/noop/) | read | No-op — useful for wiring tests |

Copy-paste recipes and workflow details: **[ansible/actions/README.md](ansible/actions/README.md)**

Custom actions: copy [`ansible/actions/_template`](ansible/actions/_template/) and follow the contract in the actions guide.

---

## Requirements

- Ansible ≥ 2.14
- [glab](https://gitlab.com/gitlab-org/cli) — GitLab CLI
- git, jq
- SSH key configured for your GitLab instance (clone/push); token needs `api` scope (discovery)

Run `./reporker check` to see what is missing.

---

## Reports

Output directory: `ansible/reports/` — start with **`01-summary.txt`**.

| # | File | Contents |
|---|---|---|
| 01 | `01-summary.txt` | Human-readable summary |
| 02 | `02-breakdown.json` | Priority breakdown (priority-class actions) |
| 03 | `03-action.json` | Action-specific results |
| 04 | `04-scan.json` | Scan matches per repo |
| 05 | `05-changed.json` | Changed files (write actions) |
| 06 | `06-run.json` | Full machine-readable record |

Details: [`ansible/reports/README.md`](ansible/reports/README.md)

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `config not found` | Run `./reporker init` |
| `group_id is still the example value` | Set your numeric group ID in `ansible/group_vars/all.yml` |
| `Token file not found` | `printf '%s' 'glpat-xxx' > glab/token && chmod 600 glab/token` |
| Clone or push fails | Clone/push use SSH — verify with `ssh -T git@<your-host>` |
| Stale repo list | Delete `ansible/reports/repos.json` to refresh from the API |
| Preview before writing | `./reporker action --dry-run` |

---

## License

MIT — see [LICENSE](LICENSE).
