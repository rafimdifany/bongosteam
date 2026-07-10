# GitHub Repo Setup Plan

## Objective
Initialize git, create polished README + .gitignore, create GitHub repo on rafimdifany account, push everything.

## Steps
1. Create `.gitignore` — Python/PyQt/pytest/build artifacts
2. Rewrite `README.md` — polished profile-ready with badges, architecture diagram, test stats
3. `git init` + `git add .` + `git commit -m "chore: initial commit"`
4. Create GitHub repo via `gh` CLI with token from `$PERSONAL_GITHUB_TOKEN`
5. `git push origin main`

## Context
- Token: `$PERSONAL_GITHUB_TOKEN` from `.zshrc` (40 chars)
- Repo owner: rafimdifany (email: rafimdifany@gmail.com)
- Working dir: `/Users/rafimdifany/Documents/project/bongo-steam`
- Not a git repo yet — needs init
- Current README.md exists but needs replacement with polished version
- All project files ready: 175 tests, 12 tasks complete, build spec + assets
