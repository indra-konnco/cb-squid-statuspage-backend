<!--
Auto-generated helper for AI coding agents. This file is intentionally concise.
Update or expand with concrete examples once repository source files exist.
-->

# Copilot instructions for this repository

Summary
- Purpose: help AI coding agents become productive quickly in this repo.
- Status when generated: repository directory is empty (no source files detected).

Current repo state
- As of 2025-11-28 there are no discoverable files in the workspace root. If you see missing context, open `README.md`, `Makefile`, `Dockerfile`, or other top-level files first.

What to do first (ordered)
- Check for a `README.md` and follow any project-specific setup notes.
- If present, open `Dockerfile`, `docker-compose.yml`, `Makefile`, `package.json`, or `requirements.txt` to learn build/runtime commands.
- Search for service/config folders: `nginx/`, `squid/`, `conf/`, `templates/`, `scripts/`, `src/`.

Key places to look (examples)
- `nginx/` or `conf/` — nginx configuration and upstream definitions.
- `squid/` or `squid.conf` — Squid proxy config and access-control rules.
- `templates/` or `static/` — HTML or template files used to render status pages.
- `Dockerfile`, `docker-compose.yml` — how containers are built and composed.
- `Makefile` — shortcut commands (common targets: `make build`, `make test`, `make run`).

Developer workflows & safe commands
- Before running anything, detect the right tooling: run `ls` and inspect files. Only execute build/test commands that match files present.
- Useful discovery commands (run in repo root):
  - `git status --porcelain` — ensure working tree is clean before edits
  - `rg "nginx|squid|status|health|docker|compose|Makefile|package.json|requirements.txt" || true`
  - `[[ -f Makefile ]] && make help || true`
  - `[[ -f docker-compose.yml ]] && docker-compose config || true`

Project-specific patterns to detect (for AI agents)
- Configuration-first: many status pages are generated from templates + config; search for `.j2`, `.tpl`, `.html` under `templates/`.
- Runtime wiring: look for nginx `location` blocks referencing `status` or `stub_status` and for backend upstream names.
- Health endpoints: search source for `/status`, `/health`, `/metrics`.

What to change and what to avoid
- Preserve existing config and CI files. If you add or update a config, include a short note in the commit explaining why.
- Avoid making assumptions about deployment (cloud provider, CI) unless corresponding CI or infra files exist.

If this file already exists
- Merge: preserve any existing guidance and add missing discovery commands or file paths.

Next steps for a human maintainer
- Add a `README.md` with build/run/test commands so AI agents can perform concrete edits and run tests.
- If you want richer AI assistance, add small example files: `Dockerfile`, `docker-compose.yml`, and one status-page template under `templates/`.

Questions for the repo owner
- Do you want the agent to run automated commands (build/test) as part of PRs? If yes, add a `CI` description in `README.md`.

— end
