# reporker

I built this because I kept hitting the same wall: **something needs to happen across a whole GitLab group**, and doing it repo by repo is not realistic.

We run microservices — one repo per service, sometimes 50–80 repos under one group. When I need to find every manifest still on `image: latest`, or drop resource requests from low-priority pods before a scheduling change, or check which services have no `.gitlab-ci.yml`… clicking through GitLab one repo at a time doesn't work.

So I made *reporker*. Point it at a group, tell it which files to look at, pick an action. It clones everything, scans, runs your logic, writes JSON reports. If the action changes files, it can branch and push for you.

```
GitLab group → clone → scan → action → report → (optional) publish
```

Works on gitlab.com or self-hosted. One config file, one CLI.

---

## What I've used it for

- **Inventory** — list every `Dockerfile`, `docker-compose.yml`, or any file pattern in a group
- **Grep at scale** — find K8s manifests with a specific `priorityClassName`, missing limits, old API versions
- **Text changes** — add a line to every `requirements.txt`, bump a base image, drop in `CODEOWNERS`
- **Compliance sweeps** — search for patterns (`password:`, `image: latest`) before an audit

Read-only actions give you a report and stop. Write actions can open a branch per changed repo.

---

## Get going

```bash
git clone https://github.com/sinae99/repo-orchestrator.git && cd repo-orchestrator

./reporker init
# edit ansible/group_vars/all.yml — host, group_id, action

printf '%s' 'glpat-xxx' > glab/token && chmod 600 glab/token

./reporker check
./reporker clone
./reporker action
```

The token file is the only auth step — reporker hands it to `glab` for you. Clone and push use SSH.

Reports go to `ansible/reports/`. Open **`ansible/reports/01-summary.txt`** first.

To push changes:

```bash
./reporker action --dry-run    # see the diff, don't touch files
./reporker publish
```

You need Ansible (≥ 2.14), [glab](https://gitlab.com/gitlab-org/cli), git, and jq. Run `./reporker check` — it'll tell you what's missing.

---

## Commands

| Command | Does |
|---|---|
| `./reporker init` | Create local config from the example |
| `./reporker check` | Verify tools, config, and token |
| `./reporker clone` | Discover repos + clone/update |
| `./reporker scan` | Find target files only |
| `./reporker action` | Scan, run action, write reports |
| `./reporker publish` | Branch, commit, push changed repos |
| `./reporker run` | clone → action, no push |
| `./reporker all` | Full pipeline including publish |

- `--dry-run` — preview a write action without touching files; reports still get written
- `-- <args>` — pass straight to ansible-playbook, e.g. `./reporker action -- -e reporker_action.name=grep`

`./reporker --help` for the rest.

---

## Config

`ansible/group_vars/all.yml` — created by `init`, gitignored:

```yaml
gitlab:
  host: gitlab.com
  group_id: 12345          # your group ID
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

Copy-paste configs for every built-in action: [`ansible/group_vars/all.yml.example`](ansible/group_vars/all.yml.example) and [`ansible/actions/README.md`](ansible/actions/README.md).

---

## Built-in actions

| Action | | What |
|---|---|---|
| [`inventory`](ansible/actions/inventory/) | read | Matched files per repo |
| [`grep`](ansible/actions/grep/) | read | Matching lines with line numbers |
| [`missing-file`](ansible/actions/missing-file/) | read | Repos that do NOT have a target file |
| [`priorityclass`](ansible/actions/priorityclass/) | read | Classify manifests by priority (missing → medium) |
| [`priorityclass-drop-requests`](ansible/actions/priorityclass-drop-requests/) | write | Drop requests from medium/low pods |
| [`line-append`](ansible/actions/line-append/) | write | Idempotently adds a line |
| [`replace`](ansible/actions/replace/) | write | Regex find-and-replace |
| [`ensure-file`](ansible/actions/ensure-file/) | write | Creates a standard file in every repo |
| [`noop`](ansible/actions/noop/) | read | Does nothing — useful for wiring |

Need a new action? Copy [`ansible/actions/_template`](ansible/actions/_template/) — full guide in [`ansible/actions/README.md`](ansible/actions/README.md).

---

## Reports

After `reporker action`, open **`ansible/reports/01-summary.txt`**. Filenames are fixed for every action — read them in order.

| # | File | What |
|---|---|---|
| 01 | `01-summary.txt` | Start here |
| 02 | `02-breakdown.json` | Pod priority split (priority-class actions only) |
| 03 | `03-action.json` | Action-specific results |
| 04 | `04-scan.json` | Scan matches per repo |
| 05 | `05-changed.json` | Changed files (write actions) |
| 06 | `06-run.json` | Full machine-readable run record |

Manifests without `priorityClassName` count as **medium** in priority-class actions.

More detail: [`ansible/reports/README.md`](ansible/reports/README.md)

---

## When something breaks

- **`config not found`** — run `./reporker init`
- **`group_id is still the example value`** — edit `ansible/group_vars/all.yml`
- **`Token file not found`** — `printf '%s' 'glpat-xxx' > glab/token && chmod 600 glab/token` (needs `api` scope)
- **Clone or push fails** — uses SSH; check `ssh -T git@<your-host>`
- **Stale repo list** — delete `ansible/reports/repos.json` to re-fetch from GitLab
- **Preview before writing** — `./reporker action --dry-run`

---

## License

MIT — [LICENSE](LICENSE)
