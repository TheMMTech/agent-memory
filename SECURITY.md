# Security policy

Agent memory runs repository code from agent hooks on every developer machine
that enables them, and it stores redacted agent transcripts in Git. A flaw in
the helper, the hooks, the redaction rules, or the retention workflow can
therefore expose code execution or secrets. Please report such problems
privately.

## Supported versions

Only the latest release line receives security fixes.

| Version | Supported |
| ------- | --------- |
| 0.2.x   | Yes       |
| < 0.2   | No        |

## Report a vulnerability

Do not open a public issue, pull request, or discussion for a security problem.

Use either channel:

- **Preferred:** GitHub private vulnerability reporting. Open the repository's
  **Security** tab and choose **Report a vulnerability**, or go to
  <https://github.com/TheMMTech/agent-memory/security/advisories/new>.
- **Email:** security@monachino.tech

Please include:

- the affected version or commit, operating system, Python version, and agent
  client (Copilot, Claude Code, or Codex) if relevant;
- the steps to reproduce, with synthetic data only;
- what an attacker gains, and any conditions it depends on.

Never send real credentials, real transcripts, or private project data. If a
real secret was exposed, rotate it first, then follow
[Session retention and deletion](docs/memory/guides/managing-memory.md#session-retention-and-deletion).

## What to expect

This project has one maintainer, so these are targets rather than guarantees:

- acknowledgement within 5 business days;
- an initial assessment within 14 days;
- a fix or a documented mitigation for confirmed issues as soon as practical,
  published as a GitHub security advisory with a patched release;
- credit in the advisory unless you ask to stay anonymous.

Please allow up to 90 days, or until a fix is released, before public disclosure.
If you need a different timeline, say so in the report.

## Scope

In scope:

- `tools/memory/memory.py`, including the destination rule, path handling,
  size limits, and redaction;
- the hook configurations under `.github/hooks/`, `.claude/`, and `.codex/`;
- the GitHub Actions workflows in `.github/workflows/`;
- the project-memory skill and the agent instruction files, where they could
  steer an agent into an unsafe action.

Out of scope:

- behavior of the agent clients themselves (report those to their vendors);
- attacks that need an already compromised machine or Git account;
- redaction misses for secret formats the documentation does not claim to
  detect (these are welcome as ordinary feature requests with synthetic samples).

## Good faith

Research that follows this policy, uses only your own repositories and
synthetic data, and avoids harm to others' data or services is welcome. We will
not pursue or support action against you for it.
