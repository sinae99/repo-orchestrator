# glab/

Runtime files for GitLab API discovery. See the [main README](../README.md) for setup.

| File | Purpose |
|---|---|
| `token` | Personal access token (`api` scope) — **never commit** |
| `repos.txt` | Generated clone URLs — recreated on every `./reporker clone` |

Create the token file once:

```bash
printf '%s' 'glpat-xxx' > glab/token && chmod 600 glab/token
```
