# Getting started

Use this guide to add memory to a project that already uses Git. Allow time
for a maintainer to review the proposed files. The installer does not change
your application's source code or publish anything.

## 1. Check what you need

You need:

- An approved copy of this kit on your machine.
- Python 3.10 or later, and Git.
- An existing target project with permission to edit it. Saving a checkpoint
  also requires at least one existing Git commit.
- Your normal approved Copilot setup if you want to use the assistant.

Open a terminal and run:

```powershell
python --version
git --version
```

**Expected result:** both print a version. Python must be 3.10 or later. On
macOS/Linux, use `python3` in place of `python` if that is how Python is named.
If either command is missing, use your organization's approved software process;
the memory installer does not install it for you.

The PowerShell examples below use these example locations:

- Kit: `C:/Work/agent-memory`
- Target project: `C:/Work/my-project`

Replace them with your actual folders. Keep the quotes around paths with spaces.

## 2. Check the target project

```powershell
cd "C:/Work/my-project"
git status --short
git log -1 --oneline
```

**Expected result:** Git recognizes the project, and the second command prints
an existing commit. `git status --short` may list unfinished changes. Do not
discard them. Work on a normal review branch and tell the maintainer about
existing changes before applying the integration.

The target's configured Git destinations must match one approved host. The
installer detects the host and SSH user from the project's `origin` (or its
only remote) and writes them to `docs/memory/config.json`; without a remote it
uses `github.com` and `git`. To choose them yourself, add
`--git-host <hostname>` and `--ssh-user <user>` to the `init` command.

## 3. Preview the proposed files

Run the installer from the kit folder:

```powershell
cd "C:/Work/agent-memory"
python tools/memory/memory.py --repo "C:/Work/my-project" init
```

**Expected result:** JSON containing `"applied": false` and a list of files
marked `create` or `append`. This is a preview; it has not changed the target.

The installer adds a marked block to existing assistant instructions. It keeps
surrounding text and existing memory documents. A conflicting helper or skill
causes an error before writing files. Do not delete an existing integration to
make an error go away; see [installation conflicts](troubleshooting.md#installation-conflict).

## 4. Apply and check

After reviewing the preview, run:

```powershell
python tools/memory/memory.py --repo "C:/Work/my-project" init --apply
cd "C:/Work/my-project"
python tools/memory/memory.py check --json
git status --short
```

**Expected result:** initialization returns `"applied": true`; validation
returns `"ok": true` and `"destination_checked": true`; Git lists the new or
updated integration files. No files have been staged or committed by the helper.

If a command fails, stop at that step and use [troubleshooting](troubleshooting.md).
An interrupted installation can be partial. Review its diff before rerunning.
The installer is designed to leave an already matching installation unchanged.

## 5. Write a useful starting brief

Open `docs/memory/current-state.md` in the target project. Initially it says the
project has not been verified. With a maintainer or Copilot, replace that with:

- What the project does, in a few sentences.
- Where its main parts are located.
- The build/test commands that have actually worked.
- Important constraints and links to existing decisions.
- Current work that another session should know about.

Check these statements against the project. Write "unknown" when the reason
for an old choice is not documented. Do not copy conversations into this file.

## 6. Review and share the integration

Review `git diff` and the new files in your editor. Use your project's normal
commit and PR process. Stage only the intended files; do not include unrelated
work, local drafts, or credentials.

**Expected result after the approved changes are pushed:** another developer
can clone or pull that branch and see the same memory files. Merely creating
a local checkpoint does not share it.

The initializer does not install the kit's test suite, check workflow,
CODEOWNERS, changelog, or roadmap into the target project. It does copy these
user guides, and with `--hooks` it copies the session retention workflow.

## 7. Try it with Copilot

Start a new Copilot session in the target project. Ask:

> Use project memory to explain this project's current state. Cite the files
> you used and tell me which facts still need checking.

**Expected result:** Copilot reads the project instructions and relevant memory
files. If it does not, explicitly ask it to follow
`.agents/skills/project-memory/SKILL.md`. Assistant behavior is not guaranteed
just because a file exists; verify it in your actual client.

## 8. Add session capture and startup context

The instructions and skill work without hooks. The hooks add two things: a
short brief at the start of every agent session, and capture of each session's
redacted transcript onto hidden refs in the project. Preview and apply from the
kit folder:

```powershell
python tools/memory/memory.py --repo "C:/Work/my-project" init --hooks
python tools/memory/memory.py --repo "C:/Work/my-project" init --hooks --apply
```

**Expected result:** the preview lists `.github/hooks/project-memory.json`
(Copilot CLI and VS Code), `.claude/settings.json` (Claude Code),
`.codex/hooks.json` (Codex), and `.github/workflows/agent-session-retention.yml`.
Existing Claude Code and Codex settings are kept; only project-memory entries
are added. If the preview reports that an existing project-memory hook
"differs", stop and compare it with the [hook behavior](command-reference.md#hook-behavior)
before changing anything.

Also check `session_repository` on the `docs/memory/config.json` line of the
preview. It must be the project's own `owner/repo`, not your personal fork:
sessions are only ever pushed to that repository. If it is wrong or empty, run
the preview from a clone whose `origin` is the project's repository, or edit
the value in `config.json` before you commit it.

Before you share the change:

1. Make sure every developer has Python 3.10 or later. Claude Code on Windows
   also needs Git Bash, which Git for Windows provides.
2. Ask the repository owner to require code-owner review for the hook files and
   `tools/memory/`. They run repository code on every developer's machine.
3. The retention workflow runs on your Git host's CI. Make sure the repository
   may run workflows there, or nothing is deleted. To keep sessions for other
   than 30 days, set the variable `AGENT_MEMORY_RETENTION_DAYS`.
4. Tell developers that Codex asks them to trust the project's hooks the first
   time, and that VS Code hooks depend on workspace trust and organization policy.

**Check it works:** after the change is merged, run one short agent session in
the project, wait a few seconds after it answers, then run:

```powershell
python tools/memory/memory.py sessions status
```

**Expected result:** `local_sessions` is at least 1, `last_run.errors` is empty,
and `unpushed_sessions` is 0. The first successful push is also the first proof
that your Git host accepts session refs for your repository. If something
else appears, see [capture troubleshooting](troubleshooting.md#sessions-are-not-captured-or-pushed)
and [startup troubleshooting](troubleshooting.md#startup-context-is-missing).

Next: [resume work and save your first checkpoint](everyday-use.md).
