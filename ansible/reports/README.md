# Reports

All reports live in this directory. They are gitignored except this README.

**Start here:** `01-summary.txt`

Reports are numbered in reading order. There is no index/catalog file.

## Priority-class runs

| # | File | What |
|---|---|---|
| 01 | `01-summary.txt` | Human summary |
| 02 | `02-priorityclass-breakdown.json` | Pod division: critical / high / medium / low |
| 03 | `03-<action>.json` | Action results |
| 04 | `04-scan.json` | Scan matches per repo |
| 05 | `05-changed.json` | Changed files (write actions only) |
| 06 | `06-report.json` | Full run record |
| 07 | `07-action.json` | Action metadata |
| 08 | `08-publish.json` | Publish results (after `reporker publish`) |

**Rule:** manifests without `priorityClassName` are classified as **medium**.

## Other actions

Numbering shifts (no breakdown report): `01-summary.txt`, `02-<action>.json`, `03-scan.json`, …

## Discovery cache

`repos.json` — repo list from GitLab API (not numbered; reused across runs).
