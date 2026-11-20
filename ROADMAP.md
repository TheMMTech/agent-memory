# Roadmap

This is the improvement plan for the repository-memory kit. It is a planning
document, not a promise of delivery dates or confirmation that a feature works.
The current helper version is 0.3.0. Read [the changelog](CHANGELOG.md) for what
has actually been delivered and [the user guides](docs/memory/guides/README.md)
for how to use the current version.

## Direction

Help a new coding-assistant session recover useful, verified context from the
source repository without adding another service: curated checkpoints for
decisions, and redacted session transcripts on hidden refs for the reasoning
behind each change (ADR-0002). Capture covers Copilot in VS Code, Copilot CLI,
Claude Code, and Codex. Installs are restricted to the one Git host named by
`allowed_git_host` in the repository's config (GitHub.com by default).

## Status and priority

| Label | Meaning |
| --- | --- |
| Delivered | Merged with linked evidence; known limits may remain. |
| In progress | Work is being implemented or reviewed; not yet a completed promise. |
| Planned | Selected next work that has not started. |
| Proposed | An idea needing a decision before implementation. |
| P0 | Needed to trust the basic result or unblock validation. |
| P1 | Needed for a useful team pilot. |
| P2 | Improvement after the basic workflow is proven. |

Owners below are responsibilities, not assignments to named people. Pick an
actual owner when an item starts. Target versions are planning groups, not
published releases.

## Current baseline

| ID | Capability | Status | Evidence and limit |
| --- | --- | --- | --- |
| BASE-01 | Curated checkpoints, local retrieval, additive setup, and shared instructions | Delivered | Local tests and a fresh GitHub clone smoke test. |
| BASE-02 | Optional startup-hook output | Delivered | Helper protocol tested; native client behavior still needs validation. |
| BASE-03 | Configurable single-host destination checks (`allowed_git_host`, `git_ssh_user`) | Delivered | Installer and destination tests; not a compliance certification. |
| BASE-04 | Hosted CI configuration | Delivered | One GitHub.com job runs the tests on Linux and Windows with Python 3.10 and 3.14. |
| SESS-01 | Agent session capture for Copilot CLI, VS Code, Claude Code, and Codex into hidden refs, with redaction, linking, push, fetch, and retention | In progress | [ADR-0002](docs/adr/0002-agent-session-capture.md); independent review findings were fixed; local tests, a Windows end-to-end capture, and a local run of the retention delete logic pass. No live client or hosted push has been verified yet. |

## Make session capture dependable

Suggested target: 0.2.x, before a team pilot.

| ID | Priority | Work | Status | Done when | Owner / dependency |
| --- | --- | --- | --- | --- | --- |
| SESS-02 | P0 | Prove a session push on a hosted repository | Planned | One disposable repository on your Git host receives `refs/agent-memory/*` under real rulesets and push protection, another clone fetches it, and the retention workflow deletes an expired ref. | Platform owner; CI available on the host. |
| SESS-03 | P1 | Verify capture in each live client | Planned | Copilot CLI, VS Code, Claude Code, and Codex each produce a session ref on Windows; VS Code's transcript location is recorded; client versions and failures are noted. | Platform owner; MEM-003. |
| SESS-04 | P1 | Measure redaction against realistic transcripts | Planned | A synthetic but realistic transcript set with known secrets shows no missed canaries and an acceptable false-positive rate; misses become rules. | Security reviewer; SESS-03. |
| SESS-06 | P1 | Measure repository growth from session captures | Planned | A week of realistic heavy use shows local `.git` and remote size growth, confirms re-pushes travel as deltas, and sets the capture interval or a gc recommendation accordingly. Blocks a team pilot. | Maintainer/platform owner; SESS-02. |
| SESS-05 | P2 | Search and summarize sessions | Proposed | `recall` can include session metadata and condensed transcripts within its context budget, without a model or service. | Maintainer; SESS-03. |

## Next: make the first version dependable

Suggested target: a reviewed maintenance release after its checks pass.

| ID | Priority | Work | Status | Done when | Owner / dependency |
| --- | --- | --- | --- | --- | --- |
| MEM-001 | P0 | Confirm Windows short/long temporary-path handling | In progress | The regression test and all supported Windows CI jobs pass on the release commit. | Maintainer. |
| MEM-002 | P0 | Make the support documentation complete and usable | In progress | A new reader can install, retrieve, checkpoint, interpret results, and report an error; local links work in the kit and a new installation. | Documentation owner. |
| MEM-003 | P1 | Verify native Copilot in VS Code and CLI | Planned | Both clients load the skill; an enabled startup hook runs once; a fresh session resumes a seeded task and distinguishes stale/draft evidence. Record client/runtime versions and outcomes. | Copilot platform owner; available clients. |
| MEM-004 | P1 | Complete the portable platform matrix | Planned | Linux and Windows on minimum/current Python pass; macOS is tested; unsupported cases are documented. | Maintainer; available CI runners. |
| MEM-005 | P1 | Establish a reproducible release process | Planned | An approved commit, version, changelog entry, release tag, validation record, installation instructions, and rollback procedure agree. | Release maintainer; green required checks. |

## Then: run a controlled team pilot

Suggested target: 0.3.x, subject to the pilot's findings.

| ID | Priority | Work | Status | Done when | Owner / dependency |
| --- | --- | --- | --- | --- | --- |
| MEM-006 | P1 | Validate one real application repository | Planned | Existing instructions are preserved; data stays within the boundaries your organization approves; real owners are configured; clone/resume works for another developer. | Repository and platform owners; MEM-003. |
| MEM-007 | P1 | Measure recall quality and context use | Planned | A maintained set of realistic tasks checks correct decision/next-action recovery, stale conflicts, irrelevant matches, and output size. Failures become actionable improvements. | Maintainer/component owners; seeded pilot tasks. |
| MEM-008 | P1 | Define review, ownership, and retention practice | Planned | The pilot names real reviewers, checks aging records, resolves conflicts, explains deletion limits, and has an agreed incident path. | Repository/data owners; MEM-006. |
| MEM-009 | P2 | Improve guided checkpoint creation | Proposed | A simpler input experience reduces mistakes while keeping explicit facts, secret checks, draft status, and existing authorization boundaries. | Maintainer; user feedback from MEM-002/006. |

## Later: reduce maintenance effort

| ID | Priority | Work | Status | Done when | Owner / dependency |
| --- | --- | --- | --- | --- | --- |
| MEM-010 | P2 | Add a safe upgrade preview | Proposed | It compares installed and requested versions, preserves local changes, lists conflicts, and supplies rollback steps; it does not silently overwrite files. | Maintainer; MEM-005 and real update cases. |
| MEM-011 | P2 | Add a record health report | Proposed | It identifies stale/broken evidence and inactive tasks without auto-accepting statements, deleting history, or publishing data. | Maintainer/data owner; retention practice. |
| MEM-012 | P2 | Validate Claude Code handoffs | Planned after Copilot | A Claude Code route reads existing records and produces compatible checkpoints; evidence is recorded independently of Copilot tests. | AI platform owner; MEM-006/008. |
| MEM-013 | P2 | Validate Codex handoffs | Planned after Claude | A Codex route reads the same records and produces compatible checkpoints without a second memory corpus. | AI platform owner; MEM-012. |

## Not part of the approved design

- Entire's hosted service or its binary.
- Storing transcripts anywhere but hidden refs in the source repository, or
  without redaction. Screenshots and images are always removed.
- A hosted memory database, vector service, or external MCP service.
- Automatic publication, policy changes, approval claims, or history rewriting.
- Treating a test on one Git host as proof that another host's rulesets, retention, or residency rules are met.

Reconsidering one of these boundaries needs a separate explicit design/policy
decision; it is not an ordinary backlog refinement.

## How to keep the roadmap useful

1. Link a change or issue to its item ID, such as `MEM-003`.
2. Agree on the smallest observable result that would close it.
3. Move it to In progress when work starts, with an actual owner and review link.
4. Mark it Delivered only after merge and the stated evidence exists. Keep any
   remaining client or deployment limits visible.
5. Record user-visible delivery in the changelog and update the relevant guide.

Review this plan after each release or pilot milestone. Date-based commitments
and service-level targets are intentionally not invented here.
