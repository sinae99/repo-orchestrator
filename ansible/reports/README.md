# Reports

Run output lives here (gitignored except this file).

**Start with `01-summary.txt`** — it lists which numbered reports were produced and what to read next.

Each `reporker scan` or `reporker action` clears previous numbered artifacts (`0*.json`, `0*.txt`). Discovery cache `repos.json` is kept between runs.

## Files

| # | File | Contents |
|---|---|---|
| 01 | `01-summary.txt` | Human-readable summary |
| 02 | `02-breakdown.json` | Pod priority split (priority-class actions only) |
| 03 | `03-action.json` | Action-specific results |
| 04 | `04-scan.json` | Scan matches per repo |
| 05 | `05-changed.json` | Changed files (write actions) |
| 06 | `06-run.json` | Full machine-readable run record |
| 07 | `07-meta.json` | Engine metadata |
| 08 | `08-publish.json` | Publish results (after `reporker publish`) |

Slots 02, 03, and 05 are omitted from `01-summary.txt` when not produced.

**Priority-class rule:** manifests without `priorityClassName` count as **medium**.

## Discovery cache

`repos.json` — repo list from the GitLab API. Not numbered; reused across runs. Delete it to force a fresh fetch.
