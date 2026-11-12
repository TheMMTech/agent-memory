# Documentation

Project memory helps a coding assistant pick up work without asking you to
explain the same project history again. It saves short written records in your
Git repository: what changed, why, what was checked, and what to do next.

You do not need to understand the Python code to use these guides. Commands
are examples to copy into a terminal. Text inside `<angle brackets>` is a value
you must replace; do not type the brackets.

## Find the right guide

| I want to... | Start here |
| --- | --- |
| Add memory to an existing project | [Getting started](getting-started.md) |
| Resume work or save progress | [Everyday use](everyday-use.md) |
| Understand an error or missing result | [Troubleshooting](troubleshooting.md) |
| Review records, update the kit, or remove it | [Managing memory](managing-memory.md) |
| Look up a command or setting | [Command reference](command-reference.md) |
| Read the short memory index | [Memory index](../README.md) |

## What it does

- Saves a **checkpoint**: a short record of a development milestone.
- Finds relevant saved records by task name, file path, or keywords.
- Shares committed records through the project's usual Git workflow.
- Gives Copilot, Claude Code, and Codex shared instructions and a startup brief.
- With the session hooks (version 0.2.0), keeps each agent **session**: its
  transcript with secrets removed, stored on a hidden ref in the same repository
  and linked to the commits made during it, for 30 days unless changed.

It does not restore unsaved code, replay a chat, or send anything to a separate
memory service. It never commits to your branches. Only session refs are pushed
automatically, and only to the configured remote. A successful local check is not
proof of policy compliance or live client operation.

## Before you run a command

1. Open the correct project's folder in your terminal.
2. Check that Python and Git are available.
3. Know whether you are working in the **kit** or the **target project**. The
   kit contains the installer; the target project receives memory files.
4. Read the expected result before continuing. Stop and use the troubleshooting
   guide if your result is different.

## Words used in these guides

| Word | Meaning |
| --- | --- |
| Repository, or repo | A project folder whose file history is managed by Git. |
| Clone | A local copy downloaded from GitHub. |
| Branch | A separate line of work, so changes can be reviewed before joining the main version. |
| Commit | A saved Git version of selected files on your machine. |
| Push | Sending your commits to GitHub so others can get them. |
| Pull request, or PR | A request to review and merge a branch's changes. |
| Checkpoint | A readable summary of progress and its supporting evidence. It is not a code backup. |
| Handoff | A short note about the current task and its next action. |
| ADR | An architecture decision record: why a significant design choice was made. |
| Hook | An optional small program the assistant runs at a specific event, such as session start. |
| Session | One conversation with a coding agent. With the hooks installed, its redacted transcript is kept for a limited time. |
| Hidden ref | A named Git pointer outside branches and tags. Session refs live under `refs/agent-memory/` and do not appear in the GitHub web interface. |
| Redaction | Replacing secrets, email addresses, and images with labels such as `[REDACTED:github-token]` before a transcript is stored. |
| Retention | How long sessions are kept before the scheduled workflow deletes them. |
| Draft | A record awaiting review. The assistant cannot declare its own new record accepted. |
| Superseded | Replaced by a newer accepted record, but retained for historical reference. |

## When to ask for assistance

If the safe checks in these guides do not solve the problem, send your project
maintainer the command, the error message, your Python/Git versions, and whether
you used VS Code Copilot or Copilot CLI. Review and remove sensitive details
before sharing. Never send credentials, whole conversations, or a copy of your
environment variables. See the [reporting checklist](troubleshooting.md#report-a-problem).
