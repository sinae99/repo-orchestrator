# glab/

Stuff reporker needs to talk to GitLab. See the [main README](../README.md).

| File | What |
|---|---|
| `token` | Your personal access token (`api` scope) — don't commit this |
| `repos.txt` | Clone URLs — regenerated every `./reporker clone` |

One-time setup:

```bash
printf '%s' 'glpat-xxx' > glab/token && chmod 600 glab/token
```
