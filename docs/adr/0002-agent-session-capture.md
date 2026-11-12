# ADR-0002: Capture agent session transcripts in hidden repository refs

Status: accepted

Supersedes the parts of ADR-0001 that rejected transcript retention and limited
hooks to startup context. ADR-0001's repository-only storage, destination policy,
and curated checkpoints remain in force.

## Context

On November 4, 2026 the maintainers decided:

- Full session transcripts are acceptable when they are stored only in the
  repository's own configured Git host (`allowed_git_host`).
- Entire the company and its hosted service must never receive session data. Its
  open-source CLI is not used either, because a third-party binary would need a
  separate security review.
- Capture must cover Copilot CLI, Copilot in VS Code, Claude Code, and Codex.
- Transcripts live in the same repository as the code they describe.
- Retention defaults to 30 days and can be changed by a repository or
  organization variable.
- Network egress controls, where they exist, are on CI runners and not on developer machines.

Entire's MIT-licensed CLI (`github.com/entireio/cli`, reviewed at commit
`ea461e19e6914701c87ee80653eb96b142dd7f8d`) showed that each agent passes a
transcript location to repository-level hook files. Its design informed this
decision. No Entire code is executed or vendored. A subset of its redaction rule
shapes was reimplemented in Python with attribution.

## Decision

- Each agent's documented repository hook file runs the in-repo, standard-library
  Python helper: `.github/hooks/project-memory.json` (Copilot CLI and VS Code),
  `.claude/settings.json` (Claude Code), and `.codex/hooks.json` (Codex).
- The start hook adds the current-state brief and records the starting commit
  under the local `.git` directory. Turn-end and session-end hooks queue a
  capture job and return immediately. A detached worker does the rest.
- The worker reads the transcript only from the agent's own session
  subdirectory (never its whole configuration folder), removes secrets, email
  addresses, and embedded images, and stores it uncompressed with a small
  metadata file as one commit on
  `refs/agent-memory/sessions/<YYYY-MM-DD>/<session-id>`. Uncompressed text lets
  GitHub secret scanning read it, and Git is expected (not yet verified) to send
  a re-push of a growing transcript as a delta. A running session is captured at
  most once every five minutes; a session end is captured at once. Working
  branches, the index, and pull requests are not
  touched. The metadata links the session to the commits made during it. Session
  commits use a fixed `project-memory` identity, so no developer email address is
  pushed. No Git hooks or commit trailers are installed.
- The worker pushes session refs only after the destination check passes for
  every configured remote, and only to the remote that fetches and pushes the
  repository recorded at installation (`session_repository`), never a fork or
  upstream remote. Credential and SSH prompts are disabled. Pushes are throttled
  per session, except for a session that just ended. A rejected push is recorded
  once and not retried until the capture changes.
- A scheduled workflow on the Git host's CI deletes refs whose start date is
  older than the retention period: `AGENT_MEMORY_RETENTION_DAYS`, then the
  repository's `session_retention_days`, then 30 days. Refs dated in the future
  or named outside the pattern are deleted too. It runs only from the default
  branch, and the helper never receives the write token.
- New installations enable capture and push. This kit's own repository keeps
  both off, so its development sessions are not captured.

## Consequences

- Capture is best effort, suitable for memory and not for audit. Hooks can be
  disabled, Codex asks the user to trust project hooks, VS Code hooks are a
  preview feature, and a crashed client may skip its final event.
- Anyone with read access to the repository can fetch the session refs. They do
  not appear in the GitHub web interface.
- Redaction is a safety net, not a guarantee. Push protection and review remain
  necessary.
- Deleting a ref removes it from the repository but is not a guaranteed purge of
  GitHub's stored objects, other clones, or backups. Agents keep their own local
  copies under `~/.copilot`, `~/.claude`, and `~/.codex`, outside this retention.
- Developer machines need Python 3.10 or later. Claude Code on Windows needs Git
  Bash, which Git for Windows provides.
- Hook files execute repository code on every developer's machine. Protect them
  and `tools/memory/` with CODEOWNERS and required review.

## Not yet verified

- That every Git host accepts pushes to `refs/agent-memory/*` under its
  rulesets, and whether secret-scanning push protection examines refs outside
  branches and tags. The first push in a repository is the test.
- How fast `.git` grows locally and on the remote. Each capture replaces the
  previous copy, which stays as an unreachable object until garbage collection
  (about two weeks by default). The five-minute capture interval bounds this,
  but long, busy sessions still need measuring (SESS-06).

## Review

An independent review of the first implementation found a destination-check
bypass (a remote defined without a `url` key), catastrophic regex backtracking,
missed AWS secret keys, visible console windows on Windows, an unsafe worker
lock, and a broader-than-needed transcript allowlist. All were fixed before the
change was shared, with a regression test for each. A second pass confirmed
the bypass closed against ten variants without mocks, and found smaller gaps
(the pin could record a personal fork, `GIT_SSH` was overridden, camelCase
secret keys were missed, and fetched metadata had no size cap), which were
also fixed. Accepted residual risks: a narrow stale-lock race that is safe
because ref updates are compare-and-swap; a final VS Code turn can wait for
the next hook event; Codex's Windows hook uses a relative path; passwords that
look like lowercase dotted code, and JSON object keys, are not redacted.

Also not yet verified: the exact VS Code transcript location on each operating system, and live hook
  behavior in all four clients.
