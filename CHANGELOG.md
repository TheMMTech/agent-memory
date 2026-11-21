# Changelog

This file records changes that matter to users and people maintaining the kit.
Read the newest section first. **Unreleased** means a change has not been
published as a tagged release. An entry here does not mean it passed every
client or deployment check; verification limits are listed explicitly.

## [Unreleased]

### Changed

- `tools/maintainer/github_settings.py` checks the maintainers team for the
  account `gh` is logged in as, or for each `--member LOGIN` given, instead of a
  login written into the script.

### Fixed

- The README's `init` examples use the placeholder kit path
  `C:/Work/agent-memory`, matching the getting-started guide, instead of a
  maintainer's local checkout path.
- A redaction test no longer contains a real local user path; it uses a
  placeholder with the same shape.

## [0.3.0] - 2026-11-20

Session capture becomes opt-in, and the public repository gets its governance,
security scanning and review rules. Checkpoint `schema_version` stays 1, so
existing checkpoints need no migration.

### Upgrading from 0.2.0

- Existing installations keep their configuration: `session_capture` and
  `session_push` keep the values already written, and an older configuration
  without these keys keeps the 0.2.0 runtime defaults. Nothing changes until
  you edit the configuration or run `init` again.
- New installations no longer capture sessions. Run `init --sessions`
  instead of `init --hooks` to keep the 0.2.0 behavior, and only in a private
  repository.
- Roll back by reinstalling the helper and guides from tag `v0.2.0` through your
  normal review; see the README's "Roll back" section.

### Added

- Project governance for the public repository: `SECURITY.md` (private
  vulnerability reporting and security@monachino.tech), a code of conduct
  (Contributor Covenant 2.1), `SUPPORT.md`, issue forms, a pull request
  template, and a real `.github/CODEOWNERS` for the maintainers team.
- CodeQL (Python and workflows) and OpenSSF Scorecard workflows, and Dependabot
  version updates for the SHA-pinned GitHub Actions.
- `tools/maintainer/github_settings.py`, which checks or applies this
  repository's GitHub settings (rulesets, secret scanning, Actions policy).
  The initializer does not copy it.

### Changed

- **Session capture is now opt-in.** `init --hooks` writes a new configuration
  with `session_capture` and `session_push` set to `false`, so the hooks only
  add the startup brief. The new `init --sessions` flag installs the hooks with
  both on; use it only in private repositories, because anyone who can read a
  repository can fetch its session refs. Existing configurations, and the
  runtime defaults for older configurations without these keys, are unchanged.
- The README credits the project's deep collaboration with Claude Code and
  explains how to verify the work independently.
- The session retention workflow now has read-only top-level permissions and
  grants `contents: write` to its one job only.
- The `main` branch ruleset now requires one approving review from someone
  other than the pull request's author and has no bypass, so no maintainer can
  merge their own change unreviewed. `CONTRIBUTING.md` says so.
- **Contributors must sign their commits.** The `main` ruleset has always
  required verified signatures, but the old admin bypass let maintainers merge
  unsigned pull requests. Without it, every commit in a pull request must be
  signed with a key registered on the author's GitHub account.
  `CONTRIBUTING.md` explains how, and how to re-sign an unsigned commit.
- The README and getting-started guide warn that session refs in a public
  repository are readable by anyone, and say to turn capture and push off there.

### Known issues

- Every 0.2.0 known issue below still applies. In particular, live hook
  behavior in all four clients, VS Code's transcript location and macOS were
  not validated for this release either.

### Release record

- Commit: the squash merge of the release pull request on `main`, prepared on
  top of `6582e42`; the `v0.3.0` tag points at it.
- Evidence: `python -m unittest discover -s tests -v`,
  `python tools/memory/memory.py check --json` and `git diff --check` on
  Ubuntu 24.04 with Python 3.12, plus the required CI checks on the release pull
  request (test matrix on Ubuntu and Windows with Python 3.10 and 3.14, CodeQL).

## [0.2.0] - 2026-11-12

First public release (MIT).

### Added

- **Curated checkpoints**: repository-owned records in Markdown with structured
  JSON metadata, existing-commit references, stable IDs, and observed
  verification. New records are drafts and cannot mark themselves accepted.
- **Recall**: `status`, `start`, `recall`, `show`, `checkpoint`, `render`, and
  `check` commands using Python's standard library and Git. Search is by task,
  keyword, and file path, with configurable result and context limits,
  draft and staleness labels, and accepted-record replacement handling.
- **Additive initializer**: `init` previews changes (`--apply` performs them),
  preserves existing instructions, refuses to overwrite different helper or
  skill files, and creates an unverified starting brief. It detects the Git
  host and SSH user from the target's `origin` (or only remote), or takes
  `--git-host` and `--ssh-user`, and pins `session_repository` to the detected
  owner/repo. Managed instruction blocks use
  `<!-- project-memory:start -->` and `<!-- project-memory:end -->` markers.
- **Shared instructions**: a `project-memory` skill, Copilot repository
  instructions, and Claude Code and Codex instruction entry points.
- **Hooks** (`init --hooks`) for Copilot CLI and Copilot in VS Code
  (`.github/hooks/project-memory.json`), Claude Code (`.claude/settings.json`),
  and Codex (`.codex/hooks.json`). The start hook adds the current-state brief
  to the agent's context.
- **Session capture on hidden refs** ([ADR-0002](docs/adr/0002-agent-session-capture.md)):
  each turn end queues a capture; a detached worker redacts the transcript,
  stores it on `refs/agent-memory/sessions/<date>/<session-id>` with the commits
  made during the session, and pushes it to the configured remote. Branches,
  the index, and pull requests are untouched. `sessions` commands: `status`,
  `list [--commit]`, `show --transcript`, `capture`, `push`, `fetch`, and
  `prune [--remote] [--dry-run]`.
- **Transcript redaction** for common tokens, private keys, credentialed URLs,
  authorization headers, connection-string secrets, credential assignments,
  secret-named JSON values, random-looking strings, email addresses, and
  images. Rule shapes are adapted from Entire's MIT-licensed CLI with
  attribution. Entire's service and binary are not used.
- **Retention**: `AGENT_MEMORY_RETENTION_DAYS`, then `session_retention_days`,
  then 30 days, applied locally by the worker and remotely by the scheduled
  `agent-session-retention.yml` workflow, which runs on any host that supports
  GitHub Actions.
- **Configurable Git host**: `allowed_git_host` (any lowercase hostname,
  default `github.com`) and `git_ssh_user` (default `git`) in
  `docs/memory/config.json`. Accepted remote forms are
  `https://<host>/owner/repo`, `<user>@<host>:owner/repo`, and
  `ssh://<user>@<host>/owner/repo`. Every fetch and push URL, after
  `insteadOf` rewrites, must match, or memory and session commands refuse with
  "A configured Git destination is outside the approved host or transport."
  Unknown configuration keys are rejected.
- Per-developer switches `AGENT_MEMORY_SESSION_CAPTURE=0` and
  `AGENT_MEMORY_SESSION_PUSH=0`.
- Offline secret-pattern checks, safe path handling, validation of replacement
  chains, and atomic creation of distinct checkpoint files for concurrent
  sessions.
- Plain-language user guides for setup, everyday use, troubleshooting, record
  review, updates, rollback, and command and settings lookup, installed into
  new target projects. A documentation index and glossary, a prioritized
  roadmap, and contribution guidance.
- Offline checks for local documentation links, including links in installed
  guides.
- CI: one GitHub.com job runs the test suite on Linux and Windows with
  Python 3.10 and 3.14.

### Security

- Hook files run repository code on every developer's machine at each agent
  turn. Protect `.github/hooks/`, `.claude/`, `.codex/`, `tools/memory/`, and
  the retention workflow with CODEOWNERS and required review.
- The worker pushes only after the destination check, never prompts for
  credentials, reads transcripts only from each agent's own data directory, and
  stores no local paths. Anyone with repository read access can fetch session
  refs.
- The destination check validates every remote `git remote` lists, including
  one defined without a `url` key, and rejects remote names that look like
  options. Pushes are pinned to the installed `session_repository`.
- Redaction rules are bounded against catastrophic backtracking and cover AWS
  secret keys, PGP private keys, Azure client secrets, Azure DevOps tokens,
  Slack and Teams webhooks, inline images, camelCase secret keys, and
  `\uXXXX`-escaped tokens. Transcripts are stored uncompressed so secret
  scanning can read them. Session commits carry no developer email.
- The transcript allowlist is limited to session subdirectories and refuses
  hard links. The worker lock is owner-checked, and a queued capture survives a
  killed worker. The retention workflow runs only from the default branch and
  keeps the write token away from the helper.
- This repository's own configuration keeps `session_capture` and
  `session_push` off, so its development sessions are not captured. A test pins
  this.

### Known issues

- Not yet verified: that every Git host's rulesets and push protection accept
  pushes to `refs/agent-memory/*`; VS Code's transcript location on each
  operating system; live hook behavior in all four clients.
- Redaction is a safety net, not a guarantee. Deleting a session ref is not a
  guaranteed purge, and agents keep their own local session files.
- Claude Code on Windows needs Git Bash. Codex on Windows must be started from
  the project root, and asks each user to trust project hooks.
- Repository growth is not yet measured (SESS-06). Each capture stores a full
  copy of the transcript; replaced copies stay in `.git` until garbage
  collection. Running sessions are captured at most every five minutes to bound
  this. That Git sends re-pushes as deltas is expected, not verified.
- Native VS Code Copilot and Copilot CLI sessions were not exercised by the
  tests; helper and hook protocol checks are not equivalent to live clients.
- macOS execution was not validated.
- Recall uses keywords, task, and path matching, not semantic search, and reads
  only the current checkout. It does not fetch other branches.
- Native chat replay and recovery of uncommitted code are not provided.
- New records are drafts. Human review and your organization's processing and
  storage policy remain separate requirements.
- There is no automatic upgrade, migration, or purge command.

## How to maintain this file

Before merging a change, add a user-visible entry to **Unreleased** under the
relevant category: Added, Changed, Fixed, Removed, Security, or Known issues.
Explain the behavior and its impact, not just a filename or commit message.
Include migration and rollback instructions for changes that need them.

When publishing a release, move the appropriate entries under its actual
version and date, record the approved commit and test evidence, and leave a new
Unreleased section. Do not invent release dates, tags, or successful tests. See
[contribution guidance](CONTRIBUTING.md#release-checklist).

[Unreleased]: https://github.com/TheMMTech/agent-memory/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/TheMMTech/agent-memory/releases/tag/v0.3.0
[0.2.0]: https://github.com/TheMMTech/agent-memory/releases/tag/v0.2.0
