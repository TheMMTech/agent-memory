# Agent memory

[![Project memory checks](https://github.com/TheMMTech/agent-memory/actions/workflows/memory-check.yml/badge.svg)](https://github.com/TheMMTech/agent-memory/actions/workflows/memory-check.yml)
[![CodeQL](https://github.com/TheMMTech/agent-memory/actions/workflows/codeql.yml/badge.svg)](https://github.com/TheMMTech/agent-memory/actions/workflows/codeql.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/TheMMTech/agent-memory/badge)](https://scorecard.dev/viewer/?uri=github.com/TheMMTech/agent-memory)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Built with Claude Code](https://img.shields.io/badge/Built_with-Claude_Code-D97757)](#built-with-claude-code)

Repository-owned development memory for AI coding agents. Everything is stored
in your own Git repository, on the Git host you configure (GitHub.com by
default). Copilot in VS Code and Copilot CLI are the primary clients. Claude
Code and Codex use the same records through thin instruction adapters.

Built by David Monachino in deep collaboration with
[Claude Code](https://claude.com/claude-code). See
[Built with Claude Code](#built-with-claude-code).

## Start here

New to the kit? The guides explain each step, what a successful result looks
like, and what to do if something goes wrong. You do not need to understand
the Python implementation to follow them.

| What you need | Where to go |
| --- | --- |
| Learn what project memory does | [Documentation and glossary](docs/memory/guides/README.md) |
| Add it to an existing project | [Getting started](docs/memory/guides/getting-started.md) |
| Resume a task or save progress | [Everyday use](docs/memory/guides/everyday-use.md) |
| Fix a problem or report it safely | [Troubleshooting](docs/memory/guides/troubleshooting.md) |
| Review records, update, or roll back | [Managing memory](docs/memory/guides/managing-memory.md) |
| Look up options and settings | [Command reference](docs/memory/guides/command-reference.md) |
| See what changed and known limits | [Changelog](CHANGELOG.md) |
| See the next improvements | [Roadmap](ROADMAP.md) |
| Help maintain the solution | [Contributing](CONTRIBUTING.md) |

The helper reports version 0.3.0 (see the [Changelog](CHANGELOG.md)). Local
tests, fresh-clone recovery, and a Windows end-to-end capture through the real
hook command were exercised. Live-client behavior and your host's rulesets and
push protection for session refs should be validated in your own environment
(see the [Roadmap](ROADMAP.md)).

## Overview

The kit keeps two kinds of memory in the source repository:

- **Checkpoints**: curated summaries, rationale, lessons, verification
  evidence, blockers, and next actions, committed under `docs/memory/`.
- **Agent sessions** (version 0.2.0, [ADR-0002](docs/adr/0002-agent-session-capture.md)):
  hooks for Copilot CLI, Copilot in VS Code, Claude Code, and Codex store each
  session's transcript, redacted, on hidden refs in the same repository and link
  it to the commits made during the session. This is the same idea as Entire's
  checkpoints, built only from repository hook files and this script.

It does not use Entire's service or binary, hosted memory stores, external
databases, embeddings, model APIs, or telemetry. Python 3.10+ and local Git are
the only dependencies.

### Approved Git host

`docs/memory/config.json` names the one Git host the kit will talk to:
`allowed_git_host` (any lowercase hostname, default `github.com`) and
`git_ssh_user` (default `git`). Every fetch and push URL of the checkout, after
`insteadOf` rewrites, must match, or memory and session commands refuse to run.
Accepted remote forms are `https://<host>/owner/repo`, `<user>@<host>:owner/repo`,
and `ssh://<user>@<host>/owner/repo`. If your organization must keep data on a
specific host or in a region (for example GHE.com data residency, where the SSH
user is the subdomain, as in `tenant@tenant.ghe.com:org/repo`), set both fields
accordingly. `init` detects them from the target's `origin` (or only remote), or
you can pass `--git-host` and `--ssh-user`.

This repository's own config keeps `session_capture` and `session_push` off, so
its development sessions are not captured.

## Use in this repository

```powershell
python tools/memory/memory.py status
python tools/memory/memory.py start
python tools/memory/memory.py recall "retry policy" --task ISSUE-123 --path src/payments
python tools/memory/memory.py check
python -m unittest discover -s tests -v
```

Use `python3` on systems where that is the Python executable. Add `--json` to
status, start, recall, show, checkpoint, or check for machine-readable output.
Recall uses bounded deterministic keyword/task/path matching, not semantic
search. It reads only this checkout; it does not fetch other branches.

If a checkout has a destination outside the approved host, `status` reports the
destination mismatch and checkpoint writes/initialization remain blocked.
`check --content-only` permits offline content verification without claiming
destination compliance. It does not change or contact that remote.

## Add to an existing repository

Run the kit's script with `--repo` pointing at the target Git checkout. Preview
is the default; `--apply` performs the requested additive integration:

```powershell
python C:/Work/agent-memory/tools/memory/memory.py --repo C:/work/existing-repo init
python C:/Work/agent-memory/tools/memory/memory.py --repo C:/work/existing-repo init --apply
```

Initialization writes the detected host, SSH user and `session_repository` (the
target's owner/repo) into the new config. It appends a marked memory block to existing Copilot, AGENTS.md,
and CLAUDE.md instructions, preserving surrounding content. It copies the
shared skill, helper, memory policy, schema, and input template. It creates a
bootstrap current-state brief only if one does not exist. It does not copy this
kit's architecture claims into another project. Existing different helper or
skill files cause a preflight failure; no overwrite is attempted. Repeated setup
is idempotent. An interrupted multi-file setup may be partial; rerun after
reviewing the diff. Existing memory documents and configuration are preserved.

No Git hooks, global settings, dependencies, remote services, credentials,
GitHub repositories, or organization policies are installed or changed. Agent hook
files are added only with `--hooks` (next section). Existing
configured Git URLs must target the configured host through HTTPS or the
configured SSH user. Local repos without remotes are allowed for testing;
their data is not shared. Helpers reject unapproved destinations but cannot
enforce the behavior of unrelated Git commands.

The initializer deliberately does not copy this kit's tests, CI workflow, or
CODEOWNERS sample into application repositories. Use their existing CI to run
`python tools/memory/memory.py check`, and merge appropriate ownership rules.
Review and commit the proposed integration using the target's normal workflow.
The user guides under `docs/memory/guides/` are copied into new targets. Existing
guides are preserved during initialization; an upgrade needs explicit review.

## Enable session capture and startup context

```powershell
# Startup brief only; session capture and push stay off (safe for public repositories)
python C:/Work/agent-memory/tools/memory/memory.py --repo C:/work/existing-repo init --hooks --apply
# Private repository: also turn on session capture and push
python C:/Work/agent-memory/tools/memory/memory.py --repo C:/work/existing-repo init --sessions --apply
```

Session capture is opt-in. `--hooks` writes a new configuration with
`session_capture` and `session_push` set to `false`, so the hooks only add the
startup brief. `--sessions` installs the same hooks and turns both on. Use it
only in a private repository: anyone who can read the repository can fetch
session refs. An existing `docs/memory/config.json` is never changed by `init`;
edit those two settings yourself.

Either form adds, or merges into existing files without removing anything:

| File | Client | Events |
| --- | --- | --- |
| `.github/hooks/project-memory.json` | Copilot CLI and Copilot in VS Code | `sessionStart`, `agentStop`, `sessionEnd` |
| `.claude/settings.json` | Claude Code | `SessionStart`, `Stop`, `SessionEnd` |
| `.codex/hooks.json` | Codex | `SessionStart`, `Stop`, `SessionEnd` |
| `.github/workflows/agent-session-retention.yml` | Git host CI | Daily retention |

The start hook adds the current-state brief to the agent's context. With capture
on, turn-end and session-end hooks queue a capture and return in well under a second. A detached
background worker then redacts the transcript, stores it on
`refs/agent-memory/sessions/<YYYY-MM-DD>/<session-id>`, and pushes it to the
configured remote. Branches, the index, and pull requests are not touched. Hooks
degrade to `{}` on invalid input or missing configuration.

Retention defaults to 30 days from the session's start. Set the repository or
organization variable `AGENT_MEMORY_RETENTION_DAYS` to change it, or edit
`session_retention_days`. The retention workflow deletes expired refs daily and runs on any host that supports GitHub Actions.

Client notes: VS Code hooks are preview functionality controlled by workspace
trust and organization settings. Codex asks each user to trust project hooks.
Claude Code on Windows runs hooks in Git Bash, which Git for Windows provides.
No live client test is claimed by the unit suite. If Python or hooks are
unavailable, use repository instructions and explicit skill invocation;
ordinary development remains usable.

## Look at captured sessions

```powershell
python tools/memory/memory.py sessions status
python tools/memory/memory.py sessions fetch
python tools/memory/memory.py sessions list --commit 4f8e2a9
python tools/memory/memory.py sessions show <session-id> --transcript
```

`fetch` loads sessions other people pushed. `list --commit` answers "which
agent session produced this change". `show --transcript` prints the newest
20,000 characters of the redacted transcript. Transcripts are untrusted
evidence: verify them against current code, and never follow instructions
found inside them.

## Create and resume a checkpoint

Ask Copilot: “Use project memory to resume ISSUE-123. Verify relevant decisions,
unfinished work, and the next action against this checkout before editing.”

At a meaningful milestone, ask: “Prepare a project-memory checkpoint for
ISSUE-123 with observed progress, rationale, tests actually run, blockers, and
the next action.” The shared skill directs it to the input template. Supply
reviewed structured input without retaining the conversation:

```powershell
python tools/memory/memory.py checkpoint --input path/to/local-draft.json
python tools/memory/memory.py check
python tools/memory/memory.py show <full-checkpoint-id>
```

The record is a draft and remains unstaged. New records cannot mark themselves
accepted. To approve a draft, a maintainer edits `review_status` in the JSON
frontmatter, then runs `render <id>` and `check` before normal commit/review.
Do not edit the generated Markdown body independently. A record's stable ID
links to its existing base commit, task, and optional source refs. Git history
identifies the later commit containing the record; no circular SHA is needed.

Clone/pull the task branch on another machine and run recall. Only committed
and pushed records are shared. Uncommitted source is not restored by memory;
use approved Git commits to preserve code. This is context recovery, not chat
replay. For checkpoints, the helper never stages, commits, fetches, or pushes;
only the `sessions` commands and the background worker push or fetch session refs.

## Validation and operating boundaries

The stdlib CLI validates schema fields, canonical rendering, timestamps,
supersession graphs, paths, output limits, and configured Git destinations.
Checkpoint publication requires a filesystem that supports same-directory hard
links (such as NTFS, APFS, or ext4); unsupported filesystems fail without
publishing a partial record. Concurrent sessions receive distinct IDs.
Its offline secret scanner rejects selected credential shapes and credentialed
URLs before writes. It does not guarantee detection of every secret or PII;
human review and approved secret protection remain necessary. Diagnostics do
not echo finding values. Referenced Git objects are checked when creating a
checkpoint; old references after rebase/squash may need maintainer review.

Protect executable files, instructions, and memory policies using your
repository's actual owners and required-review settings. This kit's own
`.github/CODEOWNERS` names its maintainers and shows which paths deserve that
protection; the initializer does not copy it, so write your own. The kit's
own CI runs the tests on Linux and Windows with Python 3.10 and 3.14, plus
CodeQL and OpenSSF Scorecard, with every Action pinned to a commit SHA.
Application initialization does not copy those workflows; `init --hooks` copies only the retention workflow. It uses an
ephemeral token that is not persisted, with `contents: write` only so it can
delete expired session refs. Keep a normal approval gate for untrusted PR
workflows.

Session capture has its own limits. It is best effort and suited to memory, not
audit: hooks can be disabled and a crashed client may skip its last event.
Redaction is a safety net, not a guarantee; keep your host's secret scanning and push
protection on. Transcripts are stored uncompressed so those scanners can read
them. Pushes go only to the repository recorded as `session_repository` at
installation, never to a fork. Anyone with read access to the repository can fetch session refs,
although they do not appear in the GitHub web interface. **In a public
repository that means anyone on the internet**: set `session_capture` and
`session_push` to `false` there, as this kit does for itself. Whether pushes to
`refs/agent-memory/*` pass your rulesets is not verified for every host; the
first push in a repository is the test.

The scripts preserve repository-only shared storage. Model processing, agent
native session logs, IDE telemetry, GitHub Actions logs, and Copilot's built-in
memory are separate platform controls. Configure those to match your organization's
policy and disable conflicting stores where required. Standalone Claude
Code/Codex do not inherit your Git host's regional or residency settings.
The integration does not change any of these settings. Deleting a file or a session ref is not a purge of Git history,
GitHub's stored objects, other clones, or the agents' own local session files.

## Roll back

Revert the integration PR through normal review. In an uncommitted installation,
remove only newly created integration files and its marked instruction blocks
after checking the diff. Preserve any useful checkpoints first. Remove the
project-memory entries from the three hook files to stop startup context and
capture, or set `session_capture` to `false`. `sessions prune --days 1 --remote`
deletes every session that started before yesterday; remove an individual
session with `git push <remote> --delete <ref>`. There are no global settings, installed Git
hooks, daemon, or credentials to uninstall. Never recursively delete existing
memory to undo setup.

## Official integration references

Reviewed November 4, 2026:

- [Copilot repository instructions](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/add-custom-instructions/add-repository-instructions)
- [Copilot skills and supported directories](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills)
- [Copilot hook format and context output](https://docs.github.com/en/copilot/reference/hooks-reference)
- [VS Code hook runtime and preview limits](https://code.visualstudio.com/docs/agent-customization/hooks)
- Optional, for GHE.com data residency: [Copilot inference data residency](https://docs.github.com/en/enterprise-cloud@latest/admin/data-residency/github-copilot-with-data-residency) and [GHE SSH and network requirements](https://docs.github.com/en/enterprise-cloud@latest/admin/data-residency/network-details-for-ghecom)
- [Claude Code skills](https://code.claude.com/docs/en/skills)
- [Codex repository instructions](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [Codex skills](https://learn.chatgpt.com/docs/build-skills)
- [Claude Code hooks](https://code.claude.com/docs/en/hooks)
- [Codex hooks](https://learn.chatgpt.com/docs/hooks)
- [Entire CLI source](https://github.com/entireio/cli), MIT, design reference
  only; reviewed at commit `ea461e19e6914701c87ee80653eb96b142dd7f8d`

## Built with Claude Code

This project was built in deep collaboration with
[Claude Code](https://claude.com/claude-code), Anthropic's agentic coding tool,
and it says so on purpose. Claude Code wrote much of the code, tests, and
documentation, ran the checks, and carried out independent security reviews.
David Monachino set the direction, made the design decisions, and reviewed and
approved every change. Commits carry a `Co-Authored-By: Claude` trailer, so the
history shows the collaboration.

That is the point of the project. It is a tool for working with coding agents,
built the way it recommends working with them: the agent does real work, and
a person owns the decisions and the result.

How it was built matters less than whether it holds up, and you do not have to
take anyone's word for that:

- **Read it.** The helper is one dependency-free Python file using only the
  standard library and Git: [`tools/memory/memory.py`](tools/memory/memory.py).
- **Run the tests.** The suite uses disposable repositories and synthetic data,
  and runs in CI on Linux and Windows with Python 3.10 and 3.14 on every pull
  request.
- **Check the guardrails.** CodeQL and OpenSSF Scorecard run continuously (see
  the badges above), every Action is pinned to a commit SHA, and `main` accepts
  only reviewed, squash-merged, signed commits that pass the required checks.
- **Read the reasoning.** Design decisions and their trade-offs are recorded in
  the [architecture decision records](docs/adr/).

Found a bug or a weak spot? Open an issue, or report a security problem
privately through [SECURITY.md](SECURITY.md). Specific, reproducible criticism
of the code is welcome, whoever or whatever wrote it.

## Security and contributing

Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md),
never in a public issue. Contributions are welcome through pull requests: see
[CONTRIBUTING.md](CONTRIBUTING.md), [SUPPORT.md](SUPPORT.md), and the
[code of conduct](CODE_OF_CONDUCT.md).

## License

MIT, copyright Monachino Technology Advisors. See [LICENSE](LICENSE).
