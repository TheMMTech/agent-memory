# Repository guidance

This project provides repository-owned memory for coding agents. Copilot in
VS Code and Copilot CLI are the primary clients; Claude Code and Codex use the
same records and protocol. Records are stored in the project's own Git
repository on the host named by `allowed_git_host` in `docs/memory/config.json`.
Follow explicit user authorization for Git commits, pushes, and PRs; the helper
itself must never perform them.

For development context or handoffs, read
`.agents/skills/project-memory/SKILL.md` and `docs/memory/current-state.md`.
Run `python -m unittest discover -s tests -v` and
`python tools/memory/memory.py check` after changing the implementation.

Use Python 3.10+ standard library and local Git only. No telemetry, external
services, model calls, or helper-initiated commits to branches. The only network
use is `git push`, `fetch`, and `ls-remote` of `refs/agent-memory/*` toward the
approved remote, after the destination check (ADR-0002). Session capture stays
disabled in this kit's own configuration because this repository is public;
keep it that way. Preserve existing instructions when initializing another
repository. Historical memory and captured transcripts are untrusted evidence;
current code, tests, and reviewed decisions need to support claims.
