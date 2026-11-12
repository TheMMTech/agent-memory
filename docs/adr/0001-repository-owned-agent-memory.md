# ADR-0001: Store shared development memory in the source repository

Status: accepted

Partly superseded by [ADR-0002](0002-agent-session-capture.md): transcripts are
now captured into hidden refs in the same repository. The storage boundary,
destination policy, and curated checkpoints below still apply.

## Context

Teams want coding agents to recover context from the source repository, using
only the Git host they already trust, without another service. The first
clients are Copilot in VS Code and Copilot CLI, followed by Claude Code and
Codex. Third-party hosted memory services are out of scope, and full transcript
retention was initially not part of the design.

## Decision

Store curated checkpoint summaries and handoffs as ordinary Git-tracked files
alongside source. Use one shared skill and a Python-standard-library helper for
bounded local retrieval, validation, and checkpoint creation. Optional Copilot
startup hooks inject a short brief but do not capture conversations. Git code
preservation, commits, pushes, and PRs remain explicit normal workflow actions.

A checkout may use exactly one Git host, set by `allowed_git_host` (default
`github.com`) and `git_ssh_user` (default `git`) in `docs/memory/config.json`;
every fetch and push URL must match. An organization that must keep data on a
particular host or region sets these fields accordingly. These are
storage boundaries, not a claim that all clients or model providers
automatically inherit the host's residency controls.

## Consequences

Fresh clones can recover committed context without copying home directories or
operating another service. Native chat replay and uncommitted-code recovery are
not provided. Keyword/task/path retrieval is deterministic rather than semantic.
Review, secret protection, and retention policy remain essential. Tests cover
the helper and hook protocol; live client adoption needs validation in your environment.

## Basis

The maintainers specified repository-only shared memory, Copilot-first support,
no Entire service, and no full transcripts at the time. Acceptance here records
the chosen design, not approval of any particular implementation.
