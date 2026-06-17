# Reports

All reports live here. They are gitignored except this README.

**Start here:** `01-summary.txt`

Report filenames are **fixed** — they do not change when you switch actions. The action name lives inside `03-action.json`, not in the filename.

Each `reporker scan` or `reporker action` clears previous numbered artifacts (`0*.json`, `0*.txt`). Discovery cache `repos.json` is kept.

## Run reports (read in order)

| # | File | What |
|---|---|---|
| 01 | `01-summary.txt` | Human summary — start here |
| 02 | `02-breakdown.json` | Pod priority split (priority-class actions only) |
| 03 | `03-action.json` | Action-specific results |
| 04 | `04-scan.json` | Scan matches per repo |
| 05 | `05-changed.json` | Changed files (write actions with changes) |
| 06 | `06-run.json` | Full machine-readable run record |
| 07 | `07-meta.json` | Engine metadata (tasks file, counts) |
| 08 | `08-publish.json` | Publish results (after `reporker publish`) |

Optional slots (02, 03, 05) are omitted from `01-summary.txt` when not produced.

**Rule:** manifests without `priorityClassName` count as **medium** in priority-class actions.

## Discovery cache

`repos.json` — repo list from GitLab API (not numbered; reused across runs).
