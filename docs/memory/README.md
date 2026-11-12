# Repository memory

Read `current-state.md` for essentials. Use the `project-memory` skill for
task-specific retrieval and checkpoint capture. Existing architecture decisions
remain in their established ADR location; the helper also searches `docs/adr/`
and `docs/decisions/` when those directories exist.

For step-by-step instructions, expected results, and common problems, start
with the [user documentation](guides/README.md).

- `work/`: optional current task handoffs with a `Status: active`, `blocked`,
  `completed`, or `retired` line. Completed/retired handoffs are excluded by
  default. Keep task filenames unique and avoid a global mutable task list.
- `checkpoints/YYYY-MM/`: milestone records with JSON frontmatter (valid YAML)
  and a readable Markdown body. The JSON payload is canonical for validation
  and ranking. The body is a rendering of that payload, not a second store.
- `lessons/`: curated lessons; prefer concise evidence and source references.
- `config.json`: repository-visible host and context limits.
- `templates/checkpoint-input.json`: checkpoint input example.
- `schema/checkpoint.schema.json`: interchange contract.

Run `python tools/memory/memory.py status` to check synchronization state,
`recall "<question>"` for relevant evidence, `show <id>` for a checkpoint, and
`check` before committing memory changes. `--json` is available for automation.

Checkpoint references name existing commits, never their own future containing
commit. After squash/rebase, preserve the stable checkpoint ID and task/PR
references and verify surviving commit links; do not silently rewrite history.
See `protocol.md` and the root README for installation and operating details.
