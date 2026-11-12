# Current state

This repository contains a repository-owned agent memory integration, helper
version 0.2.0. It has two parts: curated checkpoints under `docs/memory/`, and
agent session capture (ADR-0002) that stores redacted transcripts on
`refs/agent-memory/sessions/<date>/<session-id>` in the same repository.
Copilot in VS Code, Copilot CLI, Claude Code, and Codex are covered.

## Verified implementation constraints

- Persistent shared memory belongs in the source repository. Every fetch and
  push URL must be on `allowed_git_host` (HTTPS, or SSH as `git_ssh_user`);
  `init` detects both from the target's origin or takes `--git-host`.
- This kit's own configuration keeps `session_capture` and `session_push` off,
  because this repository is public. A test pins this. New installations
  default both to on.
- Python 3.10+ standard library and Git are the only helper dependencies. No
  external service or binary, no model calls, no telemetry.
- The helper never commits to a branch. Its only network use is Git push,
  fetch, and ls-remote of `refs/agent-memory/*` toward the approved remote,
  after the destination check, with credential prompts disabled.
- Hooks queue work and return; a detached worker captures, pushes (throttled
  per session), and prunes. Retention is `AGENT_MEMORY_RETENTION_DAYS`, then
  `session_retention_days`, then 30 days.
- Not yet verified: live hook behavior in all four clients, VS Code's
  transcript location, and the retention workflow on GitHub Enterprise hosts.

## Development

Run `python -m unittest discover -s tests -v` and
`python tools/memory/memory.py check`.

This file describes this kit. Initialization into another repository creates a
different bootstrap brief that explicitly leaves its architecture and rationale
unknown until a maintainer verifies them.
