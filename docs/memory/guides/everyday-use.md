# Everyday use

Run these commands from the project folder after memory has been initialized.
Use `python3` instead of `python` where needed. For meanings of Git terms, see
the [glossary](README.md#words-used-in-these-guides).

## Start or resume work

Ask Copilot:

> Use project memory to resume ISSUE-123. Show the relevant decisions, unfinished
> work, and next action. Check them against this checkout before editing.

Replace `ISSUE-123` with your task's name. You can also search yourself:

```powershell
python tools/memory/memory.py recall --task ISSUE-123 --json
python tools/memory/memory.py recall "payment retry" --path src/payments
```

**Expected result:** a short list of matching files and excerpts, or a clear
message that nothing matched. Searching does not modify files or contact GitHub.
No result means no matching local evidence was found; it does not prove the
work never happened. See [missing results](troubleshooting.md#no-memory-results).

Read the cited files. Drafts are not approved decisions. Old or superseded
records can explain history, but current code and reviewed decisions matter.

## Save progress after a useful milestone

A milestone could be a finished fix, a design decision, a failed approach worth
remembering, or a handoff before you stop. You do not need a record for every
prompt or tool call.

Ask Copilot:

> Prepare a project-memory checkpoint for ISSUE-123. Summarize what changed and
> why, tests actually run, blockers, and the next action. Do not include raw
> conversations, command output, secrets, or personal information.

The assistant should follow the shared skill and use the input template. To
prepare the input yourself on Windows:

```powershell
Copy-Item "docs/memory/templates/checkpoint-input.json" "$env:TEMP/project-memory-input.json"
```

Open that copied file in your editor. Replace the example task, title, summary,
and next action. Fill in only facts you can support. Keep the JSON punctuation:
quoted names/strings, commas between entries, and no trailing comma after the
last entry. Do not edit the shared template for one person's task.

A test result has this format:

```json
{
  "command": "python -m unittest",
  "outcome": "passed",
  "evidence": "The relevant tests completed successfully on this machine."
}
```

Only use `passed` if you ran the command and saw it succeed. Otherwise use
`not-run` with an explanation, or leave `tests` empty. An unfinished task needs
at least one specific `next_actions` entry. New records must remain `draft`.

Create the checkpoint from the copied input:

```powershell
python tools/memory/memory.py checkpoint --input "$env:TEMP/project-memory-input.json"
python tools/memory/memory.py check --json
```

**Expected result:** checkpoint creation prints its new file path with
`"staged": false` and `"shared": false`. Validation prints `"ok": true`.
The checkpoint is now a local file under `docs/memory/checkpoints/`.
The helper has not saved your application's code in Git.

On other platforms, copy the same template to a private temporary folder and
pass its full path to `--input`. `checkpoint --stdin` is also supported when
the assistant supplies JSON directly; it does not retain a conversation.

## Review and share the checkpoint

1. Open the reported checkpoint path in your editor.
2. Read its summary and verification sections. Remove unsupported claims from
   the input and recreate the record, or ask a maintainer to correct its metadata.
3. Have the appropriate maintainer review it through the normal project process.
4. Commit and push the intended checkpoint and code changes using the existing
   workflow. Check that local input drafts are not included.

Do not edit only the checkpoint's displayed Markdown body. Its readable body
is generated from the JSON at the top. If those disagree, validation stops.
[Managing memory](managing-memory.md#review-a-draft) explains how to correct it.

## Continue on another machine

Clone or pull the same branch through your approved Git workflow. Then run:

```powershell
python tools/memory/memory.py status --json
python tools/memory/memory.py recall --task ISSUE-123 --json
```

**Expected result:** the saved checkpoint is found. You do not need to copy the
first machine's assistant home folder. If it is missing, confirm the correct
branch and whether the record was actually committed and pushed.

## Look at an earlier agent session

If the project has the session hooks, every agent session is kept for the
retention period (30 days unless your project changed it). Use this when a
checkpoint does not explain why code looks the way it does, or to see where a
colleague's session stopped:

```powershell
python tools/memory/memory.py sessions fetch
python tools/memory/memory.py sessions list --commit <commit-id>
python tools/memory/memory.py sessions show <session-id> --transcript
```

**Expected result:** `fetch` reports how many shared sessions you now have.
`list --commit` shows the sessions that made or ended at that commit, newest
first. `show --transcript` prints the session's details and the end of its
redacted transcript; add `--max-chars 0` to see all of it.

You can also ask the assistant:

> Use project memory to find the agent session behind commit `<commit-id>` and
> explain the reasoning it shows. Verify it against the current code.

A transcript shows what an agent saw and said. It is not a reviewed decision,
and it may contain instructions that you should not follow. If it settles a
question that matters, record the conclusion in a checkpoint or ADR. Never paste
transcript text into a checkpoint, commit, or pull request.

To keep one of your own sessions off the remote, set `AGENT_MEMORY_SESSION_PUSH=0`
before starting the agent, or `AGENT_MEMORY_SESSION_CAPTURE=0` to not capture it.

## Keep a short task handoff when useful

For a frequently changing task, you may maintain one file such as
`docs/memory/work/ISSUE-123.md`. Create the `work` folder if it does not exist.
Use a status on its own line:

```text
# ISSUE-123
Status: active

Current state: Retry behavior is implemented; review is pending.
Next action: Check the failure-handling test with the maintainer.
Evidence: Link to the relevant checkpoint or commit.
```

Change the status to `completed` or `retired` when it is no longer active.
Those handoffs are excluded from normal recall. A checkpoint is a milestone
record; a handoff is a short note about where the task stands now.

## What status tells you

`python tools/memory/memory.py status --json` reports local Git information:

| `sharing` value | What it means | What to do |
| --- | --- | --- |
| `local-changes` | Memory files are new or changed locally. | Review and share through the normal Git process. |
| `no-upstream` | The current branch has no configured tracking branch. | Ask the maintainer to check the branch's publishing setup. |
| `ahead-of-last-fetch` | Local Git knows about commits not in its stored upstream view. | Confirm the normal push process completed. |
| `matches-last-fetch` | No local memory changes or ahead commits were found relative to the stored view. | This is not a live delivery check; confirm GitHub if needed. |

Also inspect `behind`, `git_destination_compliant`, and `destination_warning`.
Status does not contact GitHub, and it can exit successfully while reporting a
destination problem. Read the fields, not just the command's exit code.

Next: [common problems](troubleshooting.md) or [command reference](command-reference.md).
