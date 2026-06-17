# Reports

Everything lands here after a scan or action run. Gitignored except this file.

**Start with `01-summary.txt`** — it tells you what happened and which numbered file to open next.

Each run clears the old numbered files (`0*.json`, `0*.txt`). `repos.json` (discovery cache) sticks around.

| # | File | What |
|---|---|---|
| 01 | `01-summary.txt` | Start here |
| 02 | `02-breakdown.json` | Pod priority split — priority-class actions only |
| 03 | `03-action.json` | Whatever your action produced |
| 04 | `04-scan.json` | Matched files per repo |
| 05 | `05-changed.json` | Changed files — write actions |
| 06 | `06-run.json` | Full run record |
| 07 | `07-meta.json` | Engine metadata |
| 08 | `08-publish.json` | After `reporker publish` |

Not every slot gets filled every time — `01-summary.txt` skips what's missing.

Manifests without `priorityClassName` count as **medium** in priority-class actions.

`repos.json` is the repo list from GitLab API. Delete it if you want a fresh fetch instead of the cached list.
