# reporker + AI

i kept needing the same thing across a whole GitLab group — find every
`image: latest`, check who has no `.something`.
doing that repo by repo with 50–80 services is not possible.

**reporker** points at a group, takes file patterns + an action, then clones,
scans, runs your logic, and writes reports. write actions can branch and push.

```
GitLab group → clone → scan → action → report → publish
```

needs: Ansible ≥ 2.14, `glab`, `git`, `jq`, python3.

## layout

```
reporker          CLI — start here
README.md         how to use
docs/             recipes, actions, reports (longer)
AGENTS.md         for ai agents
recipes/          saved jobs (what to run)
ansible/actions/  tools (replace, grep, …)
ansible/          engine + your local config
glab/             token + clone list (local only)
```

## start

```bash
git clone https://github.com/sinae99/reporker.git && cd reporker

./reporker init
# edit ansible/group_vars/all.yml — host, group_id

printf '%s' 'glpat-xxx' > glab/token && chmod 600 glab/token

./reporker check
./reporker list
./reporker clone
./reporker publish
```

reports land in `ansible/reports/` — start with `01-summary.txt`.

```bash
./reporker action --recipe bump-python --dry-run   # preview
./reporker publish                                  # branch + push
```


## using it with an ai

open this repo in cursor / claude / whatever. tell it what you want.
it reads [`AGENTS.md`](AGENTS.md), builds or reuses a recipe (and an action
if needed), runs `./reporker validate` + `./reporker test` offline.
then you run the commands it hands you.

## cli

| Command | Does |
|---|---|
| `./reporker init` | config from example |
| `./reporker check` | tools, config, token |
| `./reporker list` | actions + recipes |
| `./reporker validate [action]` | lint an action |
| `./reporker test [--recipe N]` | offline test on fake repos |
| `./reporker clone` | discover + clone/update |
| `./reporker scan` | find target files |
| `./reporker action` | scan → action → reports |
| `./reporker publish` | branch, commit, push |
| `./reporker run` | clone → action (no push) |
| `./reporker all` | full pipeline + publish |

flags: `--recipe <name>`, `--dry-run`, `-- <ansible args…>`

## more

what is a recipe, what is an action, full lists, how to add your own →
[`docs/README.md`](docs/README.md)
