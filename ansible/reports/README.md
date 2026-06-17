# Reports

Every reporker run writes output to this directory. **Start with `summary.txt`** — a one-glance sheet: what was found, what was done, what to do next, and which file to open for details.

## Reading order

| Order | File | When it exists | What it is |
|------:|------|----------------|------------|
| 1 | `summary.txt` | always | Human-readable run summary — **read this first** |
| 2 | `<action>.json` | after `reporker action` | Your action's findings (e.g. `inventory.json`, `grep.json`) |
| 3 | `scan.json` | after `reporker scan` or `action` | Which files matched your patterns in each repo |
| 4 | `changed.json` | write actions that modified files | Repos and files to publish |
| 5 | `report.json` | after `reporker action` | Full machine-readable run record |
| 6 | `index.json` | after `reporker action` | Catalog of all reports with reading order |
| — | `publish.json` | after `reporker publish` | Branch and push results |

## Usually skip

| File | What it is |
|------|------------|
| `repos.json` | Discovery cache — raw repo list from the GitLab API |
| `action.json` | Action metadata — file counts and changed-file map |

## By command

```
reporker scan     → summary.txt, scan.json
reporker action   → summary.txt, scan.json, <action>.json, report.json, index.json
                    (+ changed.json if files were modified)
reporker publish  → publish.json
```

All report files are gitignored except this README.
