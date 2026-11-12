# Managing memory

This guide is for a person responsible for keeping project records useful.
It explains review and maintenance without requiring changes to the Python code.

## Assign responsibility

| Responsibility | Suggested owner |
| --- | --- |
| Is the recorded project fact true? | The developer or component maintainer who can verify it. |
| May this information be retained? | The project's data/security owner. |
| Who may change scripts, hooks, or instructions? | Repository/platform maintainers. |
| Who may approve an architectural choice? | The existing design owner or review process. |
| Who maintains clients, model access, and runners? | The platform administrator. |

Use real names or teams in the project's own ownership rules. A sample
CODEOWNERS file does not enforce approval by itself; required review settings
also need to be configured. Initialization does not configure them.

## Review a draft

1. Open the checkpoint and its cited source files or commits.
2. Check the goal, rationale, test evidence, blockers, and next actions.
3. Remove raw conversation, copied output, sensitive data, or unsupported claims.
4. Ask the author to correct uncertain statements; use "unknown" when appropriate.
5. Record review acceptance only when the proper person has actually reviewed it.

To accept or correct a checkpoint, edit its JSON frontmatter. For acceptance,
change only the appropriate field from `"review_status": "draft"` to
`"review_status": "accepted"`. Keep its existing ID and source references.
Then run:

```powershell
python tools/memory/memory.py render <full-checkpoint-id>
python tools/memory/memory.py check --json
```

Replace `<full-checkpoint-id>` with the entire ID, without the brackets.
**Expected result:** the body is regenerated, then validation returns `"ok": true`.
Review the diff and use the normal commit/PR process. The helper does not verify
the identity of a reviewer, so repository review controls still matter.

## Replace an old record

Create a new draft describing the corrected position. In its `supersedes`
list, put the full ID of the earlier checkpoint. Explain why the earlier
position changed, with evidence.

The old checkpoint remains in default recall until the replacement is accepted.
Accepting the replacement removes the old one from normal recall; it does not
delete Git history. Use `--include-history` to inspect that history. The helper
rejects missing IDs and circular replacement chains.

For a design decision, update the project's ADR status and link to the
replacement decision as well. ADRs and checkpoints are different record types.

## Review memory regularly

After completing a task, and at a regular team review:

- Mark completed handoffs `Status: completed`.
- Keep the starting brief short and correct.
- Move durable rationale into the project's existing decision records.
- Check stale records against current code before using them.
- Remove unnecessary repetition from active notes.
- Run `check --json` and fix validation errors before sharing changes.

The default stale threshold is 90 days. It is a warning based on a checkpoint's
creation time, not proof that its content is false. It is also not an automatic
deletion or retention policy; checkpoints are never deleted automatically.

## Session retention and deletion

Captured sessions are deleted automatically. The retention period is the
`AGENT_MEMORY_RETENTION_DAYS` repository or organization variable if it is set,
otherwise `session_retention_days` in [config.json](../config.json), otherwise
30 days. It counts from the day each session started.

- Each developer's background worker deletes expired session refs in their own
  clone after every capture.
- The scheduled `Agent session retention` workflow deletes expired refs on the
  remote every day. It runs on your Git host's CI with a token that has
  `contents: write`. Check its runs after rollout; a queued run
  deletes nothing.
- To check what would be deleted, run `sessions prune --remote --dry-run`.

To remove one session early, for example after a secret was found in it:

```powershell
python tools/memory/memory.py sessions list
git push <remote> --delete refs/agent-memory/sessions/<YYYY-MM-DD>/<session-id>
git update-ref -d refs/agent-memory/sessions/<YYYY-MM-DD>/<session-id>
```

Deleting a ref removes it from the repository, but it is not a guaranteed purge.
GitHub may keep the stored objects for a time, other people may have fetched
the session, and each agent keeps its own local copy under `~/.copilot`,
`~/.claude`, or `~/.codex`. Rotate an exposed secret first, then follow the
approved incident process for a purge request.

## Update an installed copy

The first version has no automatic upgrade command. Rerunning `init` preserves
existing guides/configuration and refuses different owned helper/skill files.
Do not delete those files just to make setup succeed.

1. Read the kit's changelog and identify the approved version/commit.
2. Work on a review branch in the target project.
3. Compare the new helper, skill, hooks, policy, schema, and guides with the
   installed files. Keep project-specific instructions and configuration.
   When the helper, skill, or hook files change, `init` reports conflicts until
   you replace them after review.
4. Apply the reviewed changes explicitly; keep your project's own `config.json`.
5. Run memory validation and the affected workflow in a disposable test project.
6. Review the PR, including rollback steps, before team adoption.

Record the kit commit in the update PR so the installed version can be traced.
The helper's `--version` is useful, but a commit identifies the precise code.

## Remove or roll back the integration

Prefer reverting the integration/update PR through the normal workflow. Preserve
useful project records before removing anything. If setup was never committed,
review the diff and remove only files it created and its marked instruction
blocks. Keep pre-existing project instructions and memory.

To stop startup context and session capture, remove only the reviewed
project-memory entries from `.github/hooks/project-memory.json`,
`.claude/settings.json`, and `.codex/hooks.json`, or set `session_capture` to
`false` to keep the brief but stop capture. Existing sessions stay until
retention deletes them; see [session retention](#session-retention-and-deletion).
There is no daemon, global setting, installed Git hook, or remote memory service
to uninstall. Native assistant history is separate.

Do not recursively delete the memory folder as routine rollback. Deleting a
file at the branch tip does not erase it from Git history, other clones,
backups, or caches. Follow the approved records/incident process for a purge.

## Confirm the wider boundaries

Memory files remain in the source repository, but reading them with an
assistant involves that assistant's processing route. The helper cannot approve
that route, configure regional residency, or control native session logging.
Before wider rollout, confirm approved clients and models, access, retention,
scanning, actual owners, and CI runners against your organization's policy.
