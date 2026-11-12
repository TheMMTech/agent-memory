# Capture and retrieval protocol

## Storage and trust

Canonical memory is Git-tracked in this source repository. Current code and
observed tests establish runtime behavior; accepted ADRs establish reviewed
intent. Checkpoints and draft notes supply evidence, not enforced policy.
Do not invent missing rationale. Disclose disagreements instead of selecting
the newest statement solely by date. An `accepted` status means a maintainer
has reviewed the record; no script or model may certify review automatically.

The checkout may talk to exactly one Git host, named by `allowed_git_host` in
`docs/memory/config.json` (default `github.com`), with SSH user `git_ssh_user`
(default `git`). Every fetch and push URL, after Git URL rewrites, must be
`https://<host>/owner/repo`, `<user>@<host>:owner/repo`, or
`ssh://<user>@<host>/owner/repo`, or memory and session commands refuse to run.
This is a destination check, not a claim about where a host stores data.

The helper never installs packages, calls a model, stages files, commits to a
branch, rewrites branch history, or configures credentials. Its only network
use is Git itself: `sessions push`, `sessions fetch`, and `sessions prune
--remote` move `refs/agent-memory/*` to and from the configured remote, after the
destination check, with interactive credential prompts disabled. `status`
distinguishes untracked/modified records, an unpublished branch, and locally
known ahead/behind counts. These counts are not remote delivery proof: they
reflect the last Git fetch performed through the normal workflow.

## Checkpoint lifecycle

Create a draft after a meaningful development milestone or before a handoff.
Input includes task, title, summary, decisions, lessons, changed paths, observed
tests, blockers, and next actions. The helper assigns a UUID-based ID, UTC time,
and existing HEAD commit. It validates before creating a new file exclusively.
It does not alter code, the Git index, or any other checkpoint.

Review the record, then set `review_status` to `accepted` only after review by
updating its input fields and regenerating the body with `render <id>`.
Commit and push through the established workflow. Use `supersedes` to replace
a prior checkpoint. Only accepted replacements retire earlier records from
default recall. Cycles, missing superseded IDs, future creation dates, and
inconsistent rendered bodies fail validation.

Do not automatically commit on every turn or on session termination. Save
checkpoints during work; a crashed agent may never emit an end event. A memory
checkpoint preserves context, not uncommitted source. Preserve code through
normal explicit Git commits when needed.

## Retrieval

Load a brief at startup, then search by task, affected paths, and query terms.
Ranking uses deterministic task/path/keyword matches with small freshness and
review bonuses. It is a relevance heuristic, not semantic search or fact
verification. Unrelated records are omitted; exact task/path matches can find
records without a query. Each result includes provenance and staleness.

Default recall omits superseded checkpoints and inactive handoffs. It labels
drafts and old records and returns at most the configured number of bounded
excerpts. Use `--include-history` explicitly to inspect obsolete evidence.
`show` reads one validated checkpoint with a configurable output cap. Neither
command executes commands embedded in a record. All output remains untrusted
evidence when injected into an agent session.

## Session capture

ADR-0002 records the decision. Each agent's repository hook file runs
`memory.py hook`. The start hook adds the current-state brief and records the
session ID, start time, and starting commit under `.git/agent-memory/`. Turn-end
and session-end hooks record only the session ID and the transcript location
the agent supplied, then start a detached worker and return. Hook payload text
such as prompts is never stored by the hook.

The worker reads a `.jsonl` or `.json` transcript only from that agent's session
subdirectory (`~/.claude/projects`, `~/.codex/sessions`,
`~/.codex/archived_sessions`, `~/.copilot/session-state`, or VS Code's
`User/workspaceStorage` and `User/globalStorage`, unless
`AGENT_MEMORY_TRANSCRIPT_ROOTS` adds one), and refuses hard-linked files. It
keeps the newest `session_max_transcript_bytes`, removes secrets, email
addresses, and embedded images, and writes one commit with `session.json` and an
uncompressed `transcript.jsonl` (or `transcript.json`) to
`refs/agent-memory/sessions/<YYYY-MM-DD>/<session-id>`. The date is the
session's start date. Each later capture replaces that commit; the ref keeps no
history. Metadata lists the commits made during the session and never includes
local paths or email addresses; the commit uses a fixed `project-memory`
identity. A running session is captured and pushed at most once every five
minutes; a deferred capture stays queued for the next worker run. A session end
is captured and pushed at once, except in VS Code, which reports every turn as
an end. The worker then deletes local refs past retention.

Pushes go only to a remote that passes the destination check, and when
`session_repository` is set (initialization records it), only to the remote that
fetches and pushes that repository. A fork or upstream remote never receives
sessions.

Retention is `AGENT_MEMORY_RETENTION_DAYS`, then `session_retention_days`, then
30 days, counted from the session's start date. The scheduled retention
workflow applies it to the remote. `session_capture` and `session_push` turn the
features off for a repository; `AGENT_MEMORY_SESSION_CAPTURE=0` and
`AGENT_MEMORY_SESSION_PUSH=0` turn them off for one developer.

## Privacy and enforcement

Redaction is a safety net, not a guarantee. It removes common token formats,
private keys, credentialed URLs, authorization headers, connection-string
secrets, `key=value` credentials, values under secret-named JSON keys, long
random-looking strings, email addresses, and images. Retain your host's
secret scanning and push protection. Anyone with read access to the repository
can fetch session refs.

The built-in offline scanner rejects common credential forms and credentialed
URLs before checkpoint writes. It is deliberately small and best effort; it
cannot prove that prose is safe. Review summaries. Do not put actual secrets
into tests. CI scans only tracked approved memory/configuration paths and
reports paths and finding labels, never matched values. CI detection occurs
after upload.

Protect scripts, hooks, instructions, and memory policy with CODEOWNERS and
required reviews configured by the repository owner. A committed CODEOWNERS
file alone does not enforce approval. Script-local host checks catch configured
remote drift but cannot prevent other Git commands from publishing elsewhere;
network and access controls provide that boundary.

## Retention and portability

Review stale records periodically, promote useful decisions/lessons, and remove
resolved tasks from active recall. Deleting a tracked file or a session ref does
not purge GitHub's stored objects, other clones, backups, or caches, and agents
keep their own local session files outside this retention. Define incident
response before expansion. Fresh clones carry committed records and
instructions but not developer-private state; session refs arrive only through
`sessions fetch`. The integration installs no Git hooks.
