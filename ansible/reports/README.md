# Reports

Everything lands here after a scan or action. Gitignored except this file.

**Start with `01-summary.txt`.**

Each run clears numbered artifacts (`0*.json`, `0*.txt`). `repos.json` (discovery cache) stays.

| # | File | What |
|---|---|---|
| 01 | `01-summary.txt` | start here |
| 02 | `02-breakdown.json` | priorityclass only |
| 03 | `03-action.json` | your action's output |
| 04 | `04-scan.json` | matched files per repo |
| 05 | `05-changed.json` | write actions |
| 06 | `06-run.json` | full run record |
| 07 | `07-meta.json` | engine metadata |
| 08 | `08-publish.json` | after `./reporker publish` |

Missing slots are skipped in `01-summary.txt`.

Manifests without `priorityClassName` count as **medium** for priorityclass.

Delete `repos.json` if you want a fresh group fetch instead of the cache.
