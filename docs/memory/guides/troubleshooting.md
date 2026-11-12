# Troubleshooting

Find your symptom below. Start with checks that only read files. Do not delete
memory, weaken the destination rule, or paste credentials to get past an error.
The helper does not have a command that automatically repairs every problem.

## First checks

Run from the project folder:

```powershell
python --version
git --version
python tools/memory/memory.py --version
python tools/memory/memory.py status --json
python tools/memory/memory.py check --json
```

**Expected result:** versions print, status describes this checkout, and check
returns `"ok": true`. If something fails, keep the command and error message
for your report. Do not attach whole transcripts or environment dumps.

## Python or Git is not found

**You see:** a message that `python`, `python3`, or `git` is not recognized.

1. Try `python3 --version` if `python` is missing on macOS/Linux.
2. Use your organization's approved installation process if it is unavailable.
3. Reopen the terminal after an approved installation, then repeat the version check.

Do not download and run an installation script supplied by an unknown person.
The memory kit does not install Python, Git, or Copilot.

## The script or repository cannot be found

**You see:** Python cannot open `tools/memory/memory.py`, or Git reports that
the folder is not a repository.

1. Check which folder is open. It should be the initialized project root.
2. Check whether `tools/memory/memory.py` exists there.
3. If running from the kit, put `--repo "<target folder>"` **before** the command.
4. If the target was never initialized, return to [getting started](getting-started.md).

## Memory is not initialized

**You see:** `Repository memory is not initialized.`

The project has no readable `docs/memory/config.json`. Confirm the correct
branch first. If this is a new integration, preview the initializer. If the
file was accidentally removed, ask the maintainer to restore its reviewed
version; do not guess its settings.

## Destination is not approved

**You see:** `A configured Git destination is outside the approved host or transport.`

The helper checks every configured fetch and push destination, including Git
URL rewrite rules. Remotes must use the host in `allowed_git_host` (default `github.com`)
as `https://<host>/owner/repo`, `<user>@<host>:owner/repo`, or
`ssh://<user>@<host>/owner/repo`, where `<user>` is `git_ssh_user` (default
`git`; on GHE.com data residency it is the tenant subdomain).

1. Read `destination_warning` from status.
2. Ask the repository owner to confirm the correct destinations and credentials
   through the normal Git process. Do not share a URL containing credentials.
3. Correct an actual Git setup error under that owner's direction.
4. Rerun `check --json` before creating a checkpoint.

`check --content-only` can inspect files locally, but its output says
`"destination_checked": false`. It does not approve the destination or permit
checkpoint writes. Do not change `allowed_git_host` to bypass this check.

If a fetch URL and a push URL point at different hosts, both are checked and
the mismatch is rejected. Make them use the same approved host.

## Installation conflict

**You see:** `Existing integration file conflicts: ... No files changed.`

The target already has a different helper, skill, or optional hook file.
This can happen when it has an older version or a customized integration.

1. Keep both versions available for comparison.
2. Ask the maintainer to compare the existing file with the kit version.
3. Review an explicit update PR rather than deleting or overwriting the file.
4. Preview initialization again after the versions are reconciled.

There is no `--force` upgrade command. Existing guides and other additive
documents are also preserved, so rerunning init is not a complete upgrade.

## No memory results

**You see:** `No relevant repository memory found` or `"results": []`.

1. Check the task spelling and the current branch.
2. Try fewer keywords, an exact task, or an affected path:

   ```powershell
   python tools/memory/memory.py recall --task ISSUE-123 --json
   python tools/memory/memory.py recall "retry" --path src/payments
   ```

3. Confirm the record was committed and pushed, then brought into this checkout
   using the normal Git workflow. Recall does not fetch other branches.
4. Remember that superseded checkpoints and completed/retired handoffs are
   normally hidden. Use `--include-history` if you need to inspect old evidence.

Recall is keyword/task/path matching. It does not understand every paraphrase,
and an empty query with no task or path does not list recent history.

## Checkpoint input is rejected

| Message | Likely cause | Safe next action |
| --- | --- | --- |
| `Invalid JSON object.` | Broken punctuation, comments, or duplicate names. | Start from the copied template and check the JSON in your editor. |
| `Unknown checkpoint input field.` | Extra names were added to the input. | Use only fields from the template/reference. |
| `Unfinished work requires a concrete next action.` | An active or blocked task has an empty next-action list. | Write what the next person should do. |
| `New checkpoints must be drafts...` | Input claims review acceptance. | Set `review_status` to `draft`; ask a maintainer to review later. |
| `Local Git operation failed...` on a first checkpoint | The target may have no commit yet. | Have the maintainer confirm an approved initial commit exists. |
| `A related commit is not available...` | A commit is missing locally or its ID is incorrect. | Verify the full ID and bring in required history through normal Git operations. |
| `Checkpoint exceeds the configured size limit.` | Too much text was copied. | Summarize it and reference source files; do not raise the limit as the first fix. |

## Sensitive content is rejected

**You see:** `Potential sensitive content rejected (...)`.

Do not put the rejected value in a ticket, screenshot, or another checkpoint.
Remove credentials and unnecessary sensitive details from the input. Use a
short summary or a safe source reference instead. If a real credential was
already exposed or published, follow your organization's incident process
immediately. Do not wait for a documentation or code fix.

The scanner is a safety net, not proof that content is safe. It can miss secrets
or flag harmless text. Have a maintainer review possible false positives; do
not weaken scanning globally to accept one record.

## The checkpoint body does not match

**You see:** `Checkpoint body differs from its metadata; use render after reviewing edits.`

A checkpoint contains JSON at the top and a readable body generated from it.
Someone may have edited only one part. Ask a maintainer to review the intended
facts, correct the JSON, run `render <full-id>`, and rerun `check`. Rendering
replaces the body; it does not decide which claims are true.

## An old or conflicting decision appears

Read the cited current code and decision record. Ask the decision owner to
resolve the disagreement. A new date is not enough to prove a statement is
correct. See [replacing old records](managing-memory.md#replace-an-old-record).

## Startup context is missing

1. Confirm the manual `start --json` command works.
2. Confirm hook installation was applied and reviewed.
3. Check that the client's hook file exists: `.github/hooks/project-memory.json`
   for Copilot CLI and VS Code, `.claude/settings.json` for Claude Code, or
   `.codex/hooks.json` for Codex.
4. Confirm the active client/runtime supports this hook and that workspace
   trust and organization policy permit it. Codex asks you to trust project hooks;
   Claude Code lists active hooks under `/hooks`.
5. Check the client's hook diagnostics without sharing sensitive payloads.

The helper returns an empty JSON object `{}` when it cannot safely provide hook
context. It may be missing configuration, input may be invalid, or the
destination may be unapproved. Manual commands usually give a clearer error.
Do not add duplicate hooks to compensate; use the shared skill manually while
the maintainer investigates. No checkpoint is automatically saved at shutdown.

## Sessions are not captured or pushed

Run `python tools/memory/memory.py sessions status` and read these fields:

| What you see | Likely cause | What to do |
| --- | --- | --- |
| `capture_enabled: false` | `session_capture` is `false`, or you set `AGENT_MEMORY_SESSION_CAPTURE=0`. | Intended in this kit's own repository. Elsewhere, ask the maintainer. |
| `local_sessions: 0` and `last_run: null` | The hooks never ran. | Follow [startup troubleshooting](#startup-context-is-missing). On Windows with Claude Code, install Git for Windows so Git Bash is available. With Codex on Windows, start Codex from the project's root folder. |
| An error containing `outside the agent's data directory` | The agent keeps transcripts somewhere unexpected. | Report the client and version. Set `AGENT_MEMORY_TRANSCRIPT_ROOTS` only after a maintainer confirms the location. |
| An error containing `push` and `network access and credentials` | The background push could not sign in. It never shows a login prompt. | Run `git fetch` once to sign in normally, then `sessions push`. |
| `rejected_pushes` above 0 | The server refused a session ref, for example because push protection found a secret or a ruleset blocks `refs/agent-memory/*`. | Do not retry repeatedly. Report it to the repository owner; the session is retried only after it changes. |
| `unpushed_sessions` above 0 | A changed session waits up to five minutes between pushes. | Wait, or run `sessions push`. |
| `git_destination_compliant: false` | A remote is outside the approved host, has no URL, or has an unusual name. `destination_warning` says which. | See [destination is not approved](#destination-is-not-approved). Nothing is captured or pushed until it is fixed. |
| `destination_warning` mentions `session_repository` | No remote fetches and pushes the repository recorded at installation, for example in a fork-only clone. | Add a remote for the project's own repository. Sessions are never pushed to a fork. |
| An error containing `hard links` or `.jsonl or .json` | The transcript file is not an ordinary session file. | Report the client and version; do not work around it. |

Capture is best effort. A client that crashes or is closed abruptly may skip
its last event; the next session start pushes anything left over. Never send a
transcript, `last-run.json` from another machine, or `.git/agent-memory/`
contents in a report.

## File, link, or permission errors

Memory paths cannot pass through a symbolic link or Windows junction: those
are shortcuts that may point outside the intended folder. Checkpoints also
need a filesystem that supports hard links to publish a complete file safely.
If permissions or storage prevent a write, preserve your input and ask the
maintainer to check the approved folder/filesystem. Do not rerun as an
administrator or change permissions broadly as a first fix.

## GitHub checks are queued, skipped, or failed

Queued means a job has not finished; it is not a pass. Skipped may be expected:
a workflow may be limited to certain branches or events. A job that stays
queued usually means the repository has no runner available to it.

For failures, open the failed job and step. Record the run URL and concise
error, not the entire log. Do not treat a local pass as proof that all CI jobs
passed.

## Report a problem

Use the project's normal issue or internal support process. Include:

- A short description of what you expected and what happened.
- Operating system and whether you used VS Code Copilot, Copilot CLI, or only
  the command line.
- Python, Git, and helper versions.
- The command and safe error text; the task/checkpoint ID when relevant.
- The CI run URL if a job failed.
- What checks you tried and whether anyone else can reproduce it.

Review every attachment. Exclude credentials, complete Git URLs with embedded
credentials, prompts, transcripts, raw tool output, environment dumps, and
unnecessary personal or repository content. Do not claim a resolution until
the affected command works and the relevant validation passes.
