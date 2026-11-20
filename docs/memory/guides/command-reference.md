# Command reference

Commands below start with `python tools/memory/memory.py`. Run them from the
initialized project root. Use `python3` where needed.

For another checkout, put the global option before the command:

```powershell
python tools/memory/memory.py --repo "C:/Work/my-project" status --json
```

`--version` prints the helper version. `--help` or `<command> --help` lists
available options. There are no automatic install, upgrade, repair, or purge
commands, and nothing commits to a branch. Only the `sessions` commands use the
network, and only for `refs/agent-memory/*` on the approved remote.

## Commands and effects

| Command | Purpose | Changes files? |
| --- | --- | --- |
| `status [--json]` | Describe local branch, memory, and destination state. | No. |
| `check [--json] [--content-only]` | Validate records and scan selected memory/instruction files. | No. |
| `start [--task TASK] [--json]` | Print a small starting brief and optional task evidence. | No. |
| `recall [QUERY] [--task TASK] [--path PATH] [--limit N] [--include-history] [--json]` | Find relevant records in this checkout. | No. |
| `show ID [--json]` | Read one checkpoint using its full ID. | No. |
| `checkpoint --input FILE` or `checkpoint --stdin` | Create a new draft after validation. | Creates one unstaged checkpoint. |
| `render ID [--json]` | Regenerate a reviewed checkpoint's body from its metadata. | Replaces that checkpoint's displayed body. |
| `init [--hooks \| --sessions] [--git-host HOST] [--ssh-user USER] [--json]` | Preview adding the integration to the target. | No. |
| `init --apply [--hooks \| --sessions] [--git-host HOST] [--ssh-user USER] [--json]` | Apply the additive integration. `--git-host` and `--ssh-user` set the approved host and SSH user; without them `init` detects both from the target's `origin` (or only remote), else uses `github.com` and `git`. `--hooks` adds or merges the three agent hook files and the retention workflow, and writes a new configuration with session capture and push off (startup brief only). `--sessions` does the same with capture and push on; use it only in a private repository. An existing configuration is never changed. | Creates files, appends instruction blocks, and merges hook entries. |
| `hook [--agent AGENT] EVENT` | Entry point for agent hook files. `AGENT` is `copilot` (default), `claude-code`, or `codex`. | Writes small state files under `.git/agent-memory/` and starts the background worker. |
| `sessions status` | Show capture and push settings, local and fetched session counts, unpushed sessions, and the last worker result. | No. |
| `sessions list [--commit SHA] [--limit N]` | List sessions, newest first. `--commit` keeps sessions that made or ended at that commit. | No. |
| `sessions show ID [--transcript] [--max-chars N] [--json]` | Show a session's metadata and, with `--transcript`, its newest N characters (default 20,000; `0` for all). | No. |
| `sessions capture --agent AGENT --session-id ID [--transcript FILE]` | Capture one session now. Copilot CLI's transcript is found from its ID. | Writes one session ref. |
| `sessions push` | Push changed session refs now, ignoring the five-minute interval. | Updates remote session refs. |
| `sessions fetch` | Load sessions others pushed into `refs/agent-memory/remote/sessions/`. | Updates local fetched refs. |
| `sessions prune [--days N] [--remote] [--dry-run]` | Delete session refs that started more than N days ago, or are dated in the future, locally and with `--remote` on the remote. | Deletes refs. |
| `sessions expired --ls-remote-file FILE [--days N]` | Print the expired refs in saved `git ls-remote` output, one per line. Used by the retention workflow. | No. |

`--json` is also accepted for checkpoint creation. Some commands, including
status, check, init, and checkpoint creation, already print JSON. A JSON object
is structured text that tools can read; its fields still need interpretation.

## Useful examples

```powershell
python tools/memory/memory.py recall "retry policy" --task ISSUE-123 --path src/payments --json
python tools/memory/memory.py recall --task ISSUE-123 --include-history
python tools/memory/memory.py start --task ISSUE-123 --json
```

`--path` can be repeated. `--limit` accepts 1–20, but the configured maximum
still applies; the default configuration returns at most five results. No
query/task/path means there is no search target and usually no result.

`show` and `render` require a full checkpoint ID, not a shortened prefix or a
commit SHA. `show --json` returns complete metadata, which can be larger than
a normal excerpt. Normal recall is bounded, and results may be shortened with
a message telling you to inspect the source file.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | The command completed. Read its output: empty search results or a destination warning in status are still possible. |
| `1` | The helper could not complete the operation. Read the safe error text. |
| `2` | The command line was invalid, such as a missing or unknown option. |

The hook adapter deliberately returns `{}` and success for handled input or
configuration failures, so development can continue without injected context.
This does not indicate that memory is configured correctly.

## Checkpoint input fields

Start from the [input template](../templates/checkpoint-input.json). Do not add
generated fields such as `id`, `created_at`, `base_commit`, or `schema_version`
to creation input; the helper sets them. It does not accept unknown input fields.

| Field | What to write |
| --- | --- |
| `task` | A stable task name, such as `ISSUE-123`. Required. |
| `title` | A short milestone title. Required. |
| `summary` | Verified progress and rationale. Required. |
| `agent`, `surface` | Assistant and client names; defaults are `github-copilot` and `unspecified`. |
| `status` | `in-progress`, `blocked`, `completed`, or `retired`; default is `in-progress`. |
| `review_status` | `draft` when creating a record. Acceptance is a later review action. |
| `components` | List of relevant project parts. |
| `related_paths` | List of repository-relative paths using `/`; no `..`, drive letters, or `.git/` paths. |
| `related_commits` | Full commit IDs available locally. |
| `source_refs` | Safe references to supporting files, issues, or decisions. |
| `decisions`, `lessons` | Lists of concise supported statements. |
| `tests` | List of objects containing `command`, `outcome`, and `evidence`. Outcomes are `passed`, `failed`, or `not-run`. |
| `blockers` | What prevents progress. |
| `next_actions` | Specific next steps; at least one is needed for unfinished work. |
| `supersedes` | Full IDs of existing checkpoints this one replaces after acceptance. |

Lists default to empty and may contain up to 50 entries each. Keep summaries
short. The [checkpoint schema](../schema/checkpoint.schema.json) documents the
stored format; the helper also checks relationships and safe rendering.

## Settings

Shared settings are in [config.json](../config.json). Ask the maintainer before
changing limits or destination policy. Unsupported settings are rejected; there
is no personal override file or setting to disable secret checks.

| Setting | Default | Allowed range or rule |
| --- | --- | --- |
| `schema_version` | `1` | Exactly integer `1`. |
| `allowed_git_host` | `github.com` | Any lowercase hostname. Every fetch and push URL must use it, as `https://<host>/owner/repo`, `<user>@<host>:owner/repo`, or `ssh://<user>@<host>/owner/repo`. Set it to your host if data must stay in a region (for example GHE.com data residency). |
| `git_ssh_user` | `git` | SSH user for the allowed host. On GHE.com data residency it is the tenant subdomain, as in `tenant@tenant.ghe.com:org/repo`. |
| `max_record_bytes` | `32768` | 1,024–262,144 bytes for one stored checkpoint, including its rendered body. |
| `max_recall_chars` | `16000` | 256–64,000 characters for bounded recall output. |
| `max_start_chars` | `6000` | 256–16,000 characters for the injected context text. |
| `max_results` | `5` | 1–20 search results. |
| `stale_after_days` | `90` | 1–3,650 days before a checkpoint is labeled stale. No deletion occurs. |
| `session_capture` | `false` from `init`, `true` from `init --sessions` | Capture agent sessions from the hooks. Never turn on in a public repository. |
| `session_push` | `false` from `init`, `true` from `init --sessions` | Push session refs to the configured remote. Never turn on in a public repository. |
| `session_retention_days` | `30` | 1–3,650 days, counted from each session's start date. |
| `session_max_transcript_bytes` | `50331648` (48 MiB) | 1–95 MiB. Larger transcripts keep their newest whole lines and are marked truncated. |
| `session_redact_emails` | `true` | Replace email addresses in transcripts. |
| `session_repository` | Recorded by `init` | `owner/repo` that receives session refs. Only a remote that fetches and pushes this repository is used, so a fork or upstream remote never receives sessions. Absent when `init` found no single approved remote. |

The session settings are optional, so a configuration written by version 0.1
stays valid and uses the defaults above.

Limits use characters or bytes, not model tokens. JSON formatting and client
behavior can add overhead. Keep essential context small even when a higher
limit is available.

## Environment variables

| Variable | Effect |
| --- | --- |
| `AGENT_MEMORY_RETENTION_DAYS` | Retention in days. Overrides `session_retention_days`; `--days` overrides both. Set it as a repository or organization variable for the retention workflow. |
| `AGENT_MEMORY_SESSION_CAPTURE=0` | Turn capture off for your own sessions. |
| `AGENT_MEMORY_SESSION_PUSH=0` | Keep your captured sessions on your machine. |
| `AGENT_MEMORY_TRANSCRIPT_ROOTS` | Extra directories, separated by `;` on Windows or `:` elsewhere, where transcripts may be read. Use only when an agent stores sessions in an unusual place. |
| `CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `COPILOT_HOME` | The agents' own settings for where they keep sessions; the helper follows them. |

## Hook behavior

Input is JSON on standard input. Start events print the current-state brief:
Copilot as `additionalContext`, Claude Code and Codex inside
`hookSpecificOutput`. Turn-end and session-end events record the session ID and
the transcript location the agent supplied, start the background worker, and
print `{}`. Prompts and other payload text are not stored by the hook.

| Client | Start | Capture |
| --- | --- | --- |
| Copilot CLI | `sessionStart` | `agentStop` (each turn), `sessionEnd` |
| Copilot in VS Code | The same `sessionStart` entry | The same `agentStop` and `sessionEnd` entries. VS Code maps its own events onto this shared file; hooks are a preview feature there. |
| Claude Code | `SessionStart` | `Stop` (each turn), `SessionEnd` |
| Codex | `SessionStart` | `Stop` (each turn), `SessionEnd` |

The worker writes its last result to `.git/agent-memory/last-run.json`, which
`sessions status` shows. A running session is captured and pushed at most once
every five minutes (`last_run.deferred` counts waiting captures, which stay
queued); a session end in Copilot CLI, Claude Code, or Codex is captured and
pushed at once. VS Code reports every turn as an end, so it uses the interval
too. A rejected push is retried only when the session changes.

## Session storage

Each session is one commit on `refs/agent-memory/sessions/<YYYY-MM-DD>/<id>`,
replaced at each capture. It holds `session.json` (agent, client, developer's
Git user name, branch, start and capture times, starting and ending commit,
commits made during the session, redaction counts) and the redacted transcript
as uncompressed `transcript.jsonl` or `transcript.json`. No local paths or email
addresses are stored; the commit itself uses the identity
`project-memory <project-memory@invalid>`. Fetched sessions are kept separately
under `refs/agent-memory/remote/sessions/`.

## Checks are useful, but limited

`check` validates all checkpoint records and scans selected memory/instruction
files. It is not a full repository security audit, PII detector, or live network
check. `--content-only` skips destination validation and says so explicitly.
None of these commands executes text found inside a memory record.
