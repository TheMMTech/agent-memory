## What changes

<!-- The behavior that changes, for whom, and why. Link the issue if there is one. -->

## How it was checked

<!-- Commands run, on which OS and Python version, and what was NOT tested. -->

- [ ] `python -m unittest discover -s tests -v`
- [ ] `python tools/memory/memory.py check --json`
- [ ] `git diff --check`

## Checklist

- [ ] CHANGELOG.md updated under Unreleased (if user-visible)
- [ ] Affected guides and command examples updated
- [ ] No real transcripts, credentials, or private project data, including in tests
- [ ] No new dependency, network or model call, or change to the destination rule or redaction (or it is explained above)
