# glab/

GitLab auth + discovery cache. See the [main README](../README.md).

| File | What |
|---|---|
| `token` | personal access token (`api` scope) — never commit |
| `repos.txt` | clone URLs — rewritten on every `./reporker clone` |

```bash
printf '%s' 'glpat-xxx' > glab/token && chmod 600 glab/token
```
