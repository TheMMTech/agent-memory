# Contributing

Use a branch and a pull request for changes. Keep the scope small enough to
review, explain the behavior that changes, and include the evidence needed to
judge it. Everyone taking part follows the [code of conduct](CODE_OF_CONDUCT.md).
Report security problems privately as described in [SECURITY.md](SECURITY.md),
never in an issue or pull request. See the [roadmap](ROADMAP.md) for priorities and the
[documentation index](docs/memory/guides/README.md) for user-facing behavior.

## How pull requests are merged

- Fork the repository and open a pull request against `main`. Nobody pushes to
  `main` directly; a branch ruleset enforces this.
- Required checks must pass: the test matrix and CodeQL. Workflows from an
  outside contributor's fork run only after a maintainer approves each run.
- A maintainer reviews every change, and changes to hooks, `tools/`, workflows,
  or agent instructions get extra scrutiny because they run on users' machines.
  The `main` ruleset requires one approving review from someone other than the
  pull request's author, and nobody can merge past it, maintainers included.
- Sign every commit in your pull request. The `main` ruleset requires verified
  signatures and has no bypass, so one unsigned commit blocks the merge. Use an
  SSH or GPG key that you have added to your GitHub account as a signing key
  (GitHub Docs, "Signing commits"); commits you make in GitHub's web editor are
  signed for you. To fix an unsigned commit, re-sign it
  (`git rebase --exec 'git commit --amend --no-edit -S' main`) and force-push
  your branch.
- Pull requests are squash-merged, so `main` has one commit per pull request,
  signed by GitHub. Keep the pull request title in conventional-commit form
  (`fix: ...`, `feat: ...`, `docs: ...`), because it becomes the commit message.

## Before changing something

- Read `AGENTS.md` and the project-memory skill.
- Search relevant memory, then verify its claims against current files/tests.
- Check existing work and the current PR state before creating another branch.
- Never commit real transcripts, credentials, or private project data, including in tests.

The helper must remain dependency-free beyond Python/Git. It must not contact a
model or any service, stage or commit files on a branch, store session data
anywhere but `refs/agent-memory/*`, push anywhere but the approved remote, or
silently weaken the destination rule or redaction. Ordinary user-authorized Git
actions outside the helper are separate. Session capture stays off in this
kit's own configuration because the kit is a public repository.

## Documentation writing rules

Write for someone who can follow a terminal command but does not maintain the
Python implementation. Use short sentences and explain unfamiliar terms.

For a procedure, include prerequisites, where to run it, the command, the
expected result, and a safe next step if that result does not appear. Distinguish
the kit folder from the target project. Label placeholders. Avoid describing
planned features as current commands or local checks as hosted/client proof.

Keep task-focused instructions in `docs/memory/guides/`. Put exact option and
setting details in the command reference. Link to an existing explanation
instead of copying it into multiple guides. Guides are copied into new projects,
so relative links must also work in that installed layout.

## Check a change

From the kit root:

```powershell
python -m unittest discover -s tests -v
python tools/memory/memory.py check --json
git diff --check
```

The test suite uses disposable repositories and synthetic inputs. It includes
offline documentation-link checks. No test proves live Copilot behavior or
enterprise compliance. After staging files, also run `git diff --cached --check`.
Review new files in your editor; unstaged/untracked files may not appear in an
ordinary Git diff. Do not put actual secrets or corporate content in fixtures.

## Keep the history current

- Add user-visible changes to [CHANGELOG.md](CHANGELOG.md) under Unreleased.
- Update the affected guide and any changed command examples.
- Update a roadmap item's status only when its completion criteria are met.
- Add a concise checkpoint or handoff after a meaningful milestone. New
  checkpoint records remain drafts until independently reviewed.
- In the PR, say what was tested, where, and what was not tested. Link relevant
  failures; do not replace them with an unsupported claim that everything passed.

## Release checklist

A release is a deliberate maintainer action, not a side effect of a merged PR.

1. Select the approved commit and inspect its required CI checks. Resolve
   failures or record an explicitly accepted limitation; do not call queued
   jobs passed.
2. Confirm supported Python/OS/client coverage and changes to configuration or
   checkpoint format. State untested combinations.
3. Review privacy, destination, upgrade, and rollback impacts.
4. Set the helper version if behavior has changed. Distinguish helper version
   from checkpoint `schema_version`; do not change the schema needlessly.
5. Move release entries out of Unreleased to the actual version/date. Include
   migration instructions, known issues, approved commit, and validation evidence.
6. Validate documentation links, installed guides, examples, and affected tests.
7. Publish the tag/release only under the user's or repository owner's existing
   authorization. No helper command publishes a release for you.
8. Start a new Unreleased section and update the roadmap/current-state brief.

No release tag or new version is implied by adding these instructions.
