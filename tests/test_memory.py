"""Behavioral tests use disposable Git repositories and synthetic data only."""

import concurrent.futures
import contextlib
import datetime as dt
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("project_memory", KIT / "tools/memory/memory.py")
memory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(memory)


def run_git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                            text=True, encoding="utf-8", check=True)
    return result.stdout.strip()


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="project-memory-test-")
        self.addCleanup(self.temp.cleanup)
        # Git and safe_path return canonical long paths. Windows CI's TEMP can
        # use an 8.3 alias; fixture comparisons must use the same path spelling.
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / "existing repo"
        self.root.mkdir()
        run_git(self.root, "init", "--initial-branch=main")
        run_git(self.root, "config", "user.name", "Memory Test")
        run_git(self.root, "config", "user.email", "memory-test@example.invalid")
        run_git(self.root, "-c", "core.hooksPath=", "-c", "commit.gpgSign=false", "commit", "--allow-empty", "-m", "Initial code state")
        memory.initialize(self.root, KIT, True, False)
        self.cfg = memory.config(self.root)

    def data(self, **changes):
        value = {"task": "ISSUE-123", "title": "Payment retry handoff",
                 "summary": "Retries require an idempotency key to avoid duplicate charges.",
                 "related_paths": ["src/payments/retry.py"], "components": ["payments"],
                 "decisions": ["Retry transient failures only; permanent errors are not retried."],
                 "next_actions": ["Add the transient failure regression case."],
                 "tests": [{"command": "python -m unittest", "outcome": "passed",
                            "evidence": "The seeded unit case passed locally."}]}
        value.update(changes)
        return value

    def checkpoint(self, **changes):
        return memory.make_checkpoint(self.root, self.cfg, self.data(**changes))

    def edit(self, path, **changes):
        value = memory.parse_record(memory.read_text(path))
        value.update(changes)
        path.write_text(memory.render_record(value), encoding="utf-8")
        return value

    def test_init_preserves_existing_instructions_and_is_idempotent(self):
        target = self.base / "another repo"
        target.mkdir()
        run_git(target, "init")
        (target / ".github").mkdir()
        original = "# Existing instructions\n\nBuild with the existing toolchain.\n"
        instructions = target / ".github/copilot-instructions.md"
        instructions.write_text(original, encoding="utf-8")
        memory.initialize(target, KIT, True, True)
        once = instructions.read_text(encoding="utf-8")
        self.assertTrue(once.startswith(original))
        self.assertEqual([], memory.initialize(target, KIT, True, True))
        self.assertEqual(once, instructions.read_text(encoding="utf-8"))
        self.assertNotIn("contains the first version", (target / "docs/memory/current-state.md").read_text())

    def test_installed_guides_are_complete_linked_and_preserved(self):
        from test_documentation import local_link_errors
        guides = self.root / "docs/memory/guides"
        pages = sorted(guides.glob("*.md"))
        self.assertEqual(6, len(pages))
        self.assertEqual([], local_link_errors(self.root, pages))
        customized = guides / "getting-started.md"
        customized.write_text("# Local onboarding\n\nKeep our project-specific steps.\n", encoding="utf-8")
        memory.initialize(self.root, KIT, True, False)
        self.assertIn("Keep our project-specific steps.", customized.read_text())

    def test_preview_does_not_change_files(self):
        hook = self.root / ".github/hooks/project-memory.json"
        changes = memory.initialize(self.root, KIT, False, True)
        self.assertTrue(any(item["path"] == ".github/hooks/project-memory.json" for item in changes))
        self.assertFalse(hook.exists())

    def test_conflict_preflight_makes_no_partial_writes(self):
        target = self.base / "conflict"
        target.mkdir()
        run_git(target, "init")
        existing = target / ".agents/skills/project-memory/SKILL.md"
        existing.parent.mkdir(parents=True)
        existing.write_text("Existing team workflow", encoding="utf-8")
        with self.assertRaises(memory.MemoryError):
            memory.initialize(target, KIT, True, False)
        self.assertFalse((target / "tools").exists())
        self.assertEqual("Existing team workflow", existing.read_text())

    def test_checkpoint_records_existing_head_and_leaves_index_unchanged(self):
        before = run_git(self.root, "write-tree")
        path = self.checkpoint()
        value = memory.parse_record(memory.read_text(path))
        self.assertEqual(run_git(self.root, "rev-parse", "HEAD"), value["base_commit"])
        self.assertEqual("draft", value["review_status"])
        self.assertEqual(before, run_git(self.root, "write-tree"))
        self.assertTrue(path.is_file())

    def test_fresh_clone_recovers_task_without_private_state(self):
        self.checkpoint()
        run_git(self.root, "add", ".")
        run_git(self.root, "-c", "core.hooksPath=", "-c", "commit.gpgSign=false", "commit", "-m", "Preserve task context")
        clone = self.base / "fresh clone"
        run_git(self.root, "clone", "--no-local", str(self.root), str(clone))
        # Clone from disk is test transport only; remove that non-tenant remote.
        run_git(clone, "remote", "remove", "origin")
        hits = memory.recall(clone, memory.config(clone), task="ISSUE-123")
        self.assertEqual(1, len(hits))
        self.assertIn("idempotency", hits[0]["excerpt"])
        self.assertFalse((clone / ".git/agent-memory").exists())

    def test_exact_task_beats_unrelated_keyword_match(self):
        self.checkpoint(task="ISSUE-999", title="Retry discussion")
        self.checkpoint(task="ISSUE-123", title="Actual active task")
        hits = memory.recall(self.root, self.cfg, "retry", task="ISSUE-123")
        self.assertEqual("ISSUE-123", hits[0]["task"])

    def test_path_only_retrieval(self):
        self.checkpoint()
        self.assertEqual(1, len(memory.recall(self.root, self.cfg, paths=["src/payments"])))
        self.assertEqual([], memory.recall(self.root, self.cfg, paths=["src/inventory"]))

    def test_no_match_is_not_replaced_by_random_history(self):
        self.checkpoint()
        self.assertEqual([], memory.recall(self.root, self.cfg, "unrelated-catalog-feature"))

    def test_accepted_replacement_suppresses_old_record_but_draft_does_not(self):
        old = self.checkpoint()
        old_id = memory.parse_record(memory.read_text(old))["id"]
        new = self.checkpoint(supersedes=[old_id], summary="Use the revised payment retry policy.")
        self.assertEqual(2, len(memory.recall(self.root, self.cfg, task="ISSUE-123")))
        self.edit(new, review_status="accepted")
        self.assertEqual(1, len(memory.recall(self.root, self.cfg, task="ISSUE-123")))
        self.assertEqual(2, len(memory.recall(self.root, self.cfg, task="ISSUE-123", history=True)))

    def test_cyclic_supersession_is_rejected(self):
        first = self.checkpoint()
        second = self.checkpoint()
        first_id = memory.parse_record(memory.read_text(first))["id"]
        second_id = memory.parse_record(memory.read_text(second))["id"]
        self.edit(first, supersedes=[second_id])
        self.edit(second, supersedes=[first_id])
        with self.assertRaisesRegex(memory.MemoryError, "cycle"):
            memory.records(self.root, self.cfg)

    def test_unknown_supersession_is_rejected_before_write(self):
        with self.assertRaisesRegex(memory.MemoryError, "unknown"):
            self.checkpoint(supersedes=["mem-20261104T000000Z-" + "a" * 32])
        self.assertFalse((self.root / "docs/memory/checkpoints").exists())

    def test_inactive_handoff_excluded_from_default_recall(self):
        handoff = self.root / "docs/memory/work/ISSUE-123.md"
        handoff.parent.mkdir()
        handoff.write_text("# ISSUE-123\nStatus: completed\nLegacy payment handoff.\n", encoding="utf-8")
        self.assertEqual([], memory.recall(self.root, self.cfg, task="ISSUE-123"))
        self.assertEqual(1, len(memory.recall(self.root, self.cfg, task="ISSUE-123", history=True)))

    def test_context_budgets_are_bounded(self):
        for number in range(6):
            self.checkpoint(task=f"ISSUE-{number}", summary="payment " * 900)
        self.cfg["max_recall_chars"] = 1200
        hits = memory.recall(self.root, self.cfg, "payment")
        envelope = {"results": hits, "note": "Historical evidence; verify against current code."}
        self.assertLessEqual(len(json.dumps(envelope, ensure_ascii=False, indent=2)), 1200)
        (self.root / "docs/memory/current-state.md").write_text("Project facts. " * 1000, encoding="utf-8")
        self.cfg["max_start_chars"] = 700
        self.assertLessEqual(len(memory.bootstrap(self.root, self.cfg)), 700)

    def test_secret_canaries_rejected_without_echo_or_file(self):
        canaries = ["ghp_" + "A1b2" * 10, "password=" + "synthetic9" * 3,
                    "https://someone:synthetic9@service.invalid/db",
                    "-----BEGIN PRIVATE KEY-----"]
        for canary in canaries:
            with self.subTest(kind=canaries.index(canary)):
                with self.assertRaises(memory.MemoryError) as captured:
                    self.checkpoint(summary=canary)
                self.assertNotIn(canary, str(captured.exception))
        self.assertFalse((self.root / "docs/memory/checkpoints").exists())

    def test_existing_secret_content_stops_retrieval(self):
        handoff = self.root / "docs/memory/work/ISSUE-123.md"
        handoff.parent.mkdir()
        handoff.write_text("token=" + "synthetic9" * 3, encoding="utf-8")
        with self.assertRaises(memory.MemoryError):
            memory.recall(self.root, self.cfg, task="ISSUE-123")

    def test_new_record_cannot_self_approve(self):
        with self.assertRaisesRegex(memory.MemoryError, "draft"):
            self.checkpoint(review_status="accepted")

    def test_unfinished_record_requires_next_action(self):
        with self.assertRaisesRegex(memory.MemoryError, "next action"):
            self.checkpoint(next_actions=[])

    def test_unavailable_related_commit_is_rejected(self):
        with self.assertRaisesRegex(memory.MemoryError, "not available"):
            self.checkpoint(related_commits=["0" * 40])

    def test_body_edits_require_explicit_rerender(self):
        path = self.checkpoint()
        path.write_text(memory.read_text(path) + "\nUnverified claim.\n", encoding="utf-8")
        with self.assertRaisesRegex(memory.MemoryError, "body differs"):
            memory.records(self.root, self.cfg)
        value = memory.parse_record(memory.read_text(path), check_body=False)
        memory.atomic_write(path, memory.render_record(value))
        self.assertEqual(1, len(memory.records(self.root, self.cfg)))

    def test_old_record_is_labeled_stale(self):
        path = self.checkpoint()
        old = (memory.now() - dt.timedelta(days=100)).isoformat().replace("+00:00", "Z")
        value = self.edit(path, created_at=old)
        folder = path.parent.parent / old[:7]
        folder.mkdir(exist_ok=True)
        path.rename(folder / path.name)
        self.assertTrue(memory.recall(self.root, self.cfg, task=value["task"])[0]["stale"])

    def test_traversal_is_rejected(self):
        for path in ("../outside", "C:/outside", "docs/../../outside", "docs\\outside", ".git/config"):
            with self.subTest(path=path), self.assertRaises(memory.MemoryError):
                memory.safe_path(self.root, path)
        with self.assertRaises(memory.MemoryError):
            self.checkpoint(related_paths=["../outside"])

    def test_symlink_escape_is_rejected(self):
        outside = self.base / "outside"
        outside.mkdir()
        link = self.root / "docs/memory/lessons"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("Symlink creation is unavailable to this Windows account.")
        with self.assertRaises(memory.MemoryError):
            memory.recall(self.root, self.cfg, "anything")

    def test_remotes_and_url_rewrites_are_validated(self):
        run_git(self.root, "remote", "add", "origin", "https://github.com/org/project.git")
        self.assertEqual(["origin"], memory.verify_remotes(self.root))
        run_git(self.root, "remote", "set-url", "--push", "origin", "https://gitlab.example/org/project.git")
        with self.assertRaises(memory.MemoryError):
            memory.verify_remotes(self.root)
        run_git(self.root, "config", "--unset", "remote.origin.pushurl")
        run_git(self.root, "config", "url.https://gitlab.example/.insteadOf", "https://github.com/")
        with self.assertRaises(memory.MemoryError):
            memory.verify_remotes(self.root)

    def use_host(self, host, user="git"):
        value = dict(self.cfg, allowed_git_host=host, git_ssh_user=user)
        (self.root / "docs/memory/config.json").write_text(json.dumps(value), encoding="utf-8")
        self.cfg = memory.config(self.root)

    def test_configured_host_and_ssh_user_are_enforced(self):
        self.use_host("tenant.ghe.com", "tenant")
        run_git(self.root, "remote", "add", "origin", "tenant@tenant.ghe.com:org/project.git")
        memory.verify_remotes(self.root)
        run_git(self.root, "remote", "set-url", "origin", "https://tenant.ghe.com/org/project")
        memory.verify_remotes(self.root)
        run_git(self.root, "remote", "set-url", "origin", "git@tenant.ghe.com:org/project.git")
        with self.assertRaises(memory.MemoryError):
            memory.verify_remotes(self.root)
        run_git(self.root, "remote", "set-url", "origin", "https://github.com/org/project.git")
        with self.assertRaises(memory.MemoryError):
            memory.verify_remotes(self.root)

    def test_similar_looking_hosts_are_rejected(self):
        for url in ("https://github.com.evil.example/org/project.git", "https://evilgithub.com/org/project.git",
                    "https://user@github.com/org/project.git", "git@github.com.evil.example:org/project.git"):
            run_git(self.root, "remote", "add", "origin", url)
            with self.assertRaises(memory.MemoryError, msg=url):
                memory.verify_remotes(self.root)
            run_git(self.root, "remote", "remove", "origin")

    def test_initialization_detects_the_host_from_origin(self):
        target = self.base / "tenant install"
        target.mkdir()
        run_git(target, "init")
        run_git(target, "remote", "add", "origin", "tenant@tenant.ghe.com:Org/App.git")
        memory.initialize(target, self.root, True, False)
        value = memory.config(target)
        self.assertEqual(("tenant.ghe.com", "tenant"), (value["allowed_git_host"], value["git_ssh_user"]))
        self.assertIn("restricted to tenant.ghe.com", (target / "docs/memory/current-state.md").read_text())

    def test_initialization_accepts_an_explicit_host(self):
        target = self.base / "explicit install"
        target.mkdir()
        run_git(target, "init")
        memory.initialize(target, self.root, True, False, git_host="git.example.com")
        self.assertEqual("git.example.com", memory.config(target)["allowed_git_host"])
        run_git(target, "remote", "add", "origin", "https://github.com/org/project.git")
        with self.assertRaises(memory.MemoryError):
            memory.verify_remotes(target)
        with self.assertRaises(memory.MemoryError):
            memory.initialize(self.base, self.root, False, False, git_host="https://github.com")

    def test_kit_settings_are_not_exported_on_initialization(self):
        target = self.base / "plain install"
        target.mkdir()
        run_git(target, "init")
        memory.initialize(target, KIT, True, False)
        value = memory.config(target)
        self.assertEqual("github.com", value["allowed_git_host"])
        self.assertNotIn("session_repository", value)
        self.assertFalse(value["session_capture"])
        self.assertFalse(value["session_push"])

    def test_invalid_host_settings_and_unknown_fields_are_rejected(self):
        location = self.root / "docs/memory/config.json"
        for change in ({"allowed_git_host": "https://github.com"}, {"allowed_git_host": "GitHub.com"},
                       {"allowed_git_host": "localhost"}, {"allowed_git_host": "a/b.com"},
                       {"git_ssh_user": "bad user"}, {"development_repository": "github.com/org/repo"}):
            location.write_text(json.dumps(dict(self.cfg, **change)), encoding="utf-8")
            with self.assertRaises(memory.MemoryError, msg=str(change)):
                memory.config(self.root)

    def test_concurrent_sessions_create_distinct_records(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            paths = list(executor.map(lambda n: self.checkpoint(task=f"ISSUE-{n}"), range(8)))
        self.assertEqual(8, len(set(paths)))
        self.assertEqual(8, len(memory.records(self.root, self.cfg)))

    def test_worktree_records_use_own_checkout(self):
        run_git(self.root, "add", ".")
        run_git(self.root, "-c", "core.hooksPath=", "-c", "commit.gpgSign=false", "commit", "-m", "Add integration")
        worktree = self.base / "linked worktree"
        run_git(self.root, "worktree", "add", "-b", "task-branch", str(worktree))
        path = memory.make_checkpoint(worktree, memory.config(worktree), self.data())
        self.assertTrue(path.is_relative_to(worktree))
        self.assertEqual([], memory.records(self.root, self.cfg))

    def test_atomic_checkpoint_publication_never_overwrites_a_record(self):
        path = self.root / "published.md"
        path.write_text("Existing record", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            memory.atomic_create(path, "Replacement")
        self.assertEqual("Existing record", path.read_text())
        self.assertEqual([], list(self.root.glob(".memory-*")))

    def test_secret_in_agent_instruction_is_detected_without_echo(self):
        path = self.root / "AGENTS.md"
        canary = "ghp_" + "B2c3" * 10
        path.write_text("# Instructions\n" + canary, encoding="utf-8")
        with self.assertRaises(memory.MemoryError) as captured:
            memory.check(self.root, self.cfg)
        self.assertIn("AGENTS.md", str(captured.exception))
        self.assertNotIn(canary, str(captured.exception))

    def test_start_hook_injects_context_and_persists_no_payload(self):
        payload = json.dumps({"sessionId": "example-session", "initialPrompt": "sensitive material must not persist"})
        state = self.root / ".git" / "agent-memory"

        def tree():
            return sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*")
                          if p.is_file() and not p.is_relative_to(state))
        before = tree()
        output = memory.hook(self.root, "sessionStart", io.StringIO(payload))
        self.assertIn("additionalContext", output)
        self.assertNotIn("sensitive material", output["additionalContext"])
        self.assertEqual(before, tree())
        # Only the session ID and starting commit are recorded, never prompt text.
        for path in state.rglob("*.json"):
            self.assertNotIn("sensitive material", path.read_text(encoding="utf-8"))

    def test_hook_degrades_on_invalid_or_oversized_input(self):
        for raw in ("{broken", "[]", "x" * (memory.MAX_INPUT + 1)):
            self.assertEqual({}, memory.hook(self.root, "sessionStart", io.StringIO(raw)))
        with mock.patch.object(memory, "config", side_effect=memory.MemoryError("unavailable")):
            self.assertEqual({}, memory.hook(self.root, "sessionStart", io.StringIO("{}")))

    def test_missing_configuration_has_actionable_error(self):
        (self.root / "docs/memory/config.json").unlink()
        with self.assertRaisesRegex(memory.MemoryError, "not initialized"):
            memory.config(self.root)

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(memory.MemoryError):
            memory.read_json('{"task":"one","task":"two"}')

    def test_status_distinguishes_unshared_memory(self):
        state = memory.status(self.root, self.cfg)
        self.assertEqual("local-changes", state["sharing"])
        self.assertIsNone(state["upstream"])
        self.assertIn("No network check", state["delivery_note"])

    def test_local_validation_does_not_certify_unapproved_remote(self):
        run_git(self.root, "remote", "add", "origin", "https://gitlab.example/org/project.git")
        state = memory.status(self.root, self.cfg)
        self.assertFalse(state["git_destination_compliant"])
        with self.assertRaises(memory.MemoryError):
            memory.check(self.root, self.cfg)
        self.assertFalse(memory.check(self.root, self.cfg, content_only=True)["destination_checked"])
        with self.assertRaises(memory.MemoryError):
            self.checkpoint()

    def test_control_input_does_not_reach_shell(self):
        # Memory can describe commands, but retrieval never executes them.
        self.checkpoint(summary="Do not execute $(touch MEMORY_SHOULD_NOT_EXIST); investigate first.")
        hits = memory.recall(self.root, self.cfg, task="ISSUE-123")
        self.assertIn("$(touch", hits[0]["excerpt"])
        self.assertFalse((self.root / "MEMORY_SHOULD_NOT_EXIST").exists())

    def test_boolean_schema_version_is_not_an_integer_version(self):
        path = self.checkpoint()
        value = memory.parse_record(memory.read_text(path))
        value["schema_version"] = True
        with self.assertRaises(memory.MemoryError):
            memory.validate_record(value)

    def test_cli_checkpoint_and_recall_end_to_end(self):
        command = [sys.executable, str(self.root / "tools/memory/memory.py"), "--repo", str(self.root)]
        result = subprocess.run([*command, "checkpoint", "--stdin"], input=json.dumps(self.data()),
                                capture_output=True, text=True, check=True)
        self.assertFalse(json.loads(result.stdout)["staged"])
        result = subprocess.run([*command, "recall", "--task", "ISSUE-123", "--json"],
                                capture_output=True, text=True, check=True)
        self.assertEqual(1, len(json.loads(result.stdout)["results"]))
        result = subprocess.run([*command, "check", "--json"], capture_output=True, text=True, check=True)
        self.assertTrue(json.loads(result.stdout)["ok"])

    def test_cli_hook_uses_utf8_json_on_windows_pipes(self):
        current = self.root / "docs/memory/current-state.md"
        current.write_text("# Current state\nPayment constraints — résumé 日本語.\n", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(self.root / "tools/memory/memory.py"), "--repo", str(self.root), "hook", "sessionStart"],
            input=b'{}', capture_output=True, check=True,
        )
        output = json.loads(result.stdout.decode("utf-8"))
        self.assertIn("résumé 日本語", output["additionalContext"])

    @unittest.skipUnless(os.name == "nt", "Windows short-path behavior")
    def test_cli_accepts_windows_short_repository_path(self):
        import ctypes
        get_short_path = ctypes.windll.kernel32.GetShortPathNameW
        get_short_path.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
        get_short_path.restype = ctypes.c_uint
        buffer = ctypes.create_unicode_buffer(32768)
        length = get_short_path(str(self.root), buffer, len(buffer))
        if not length or length >= len(buffer):
            self.skipTest("The filesystem does not provide short path names.")
        alias = buffer.value
        self.assertEqual(self.root.resolve(), memory.repo_root(alias))
        result = subprocess.run(
            [sys.executable, str(self.root / "tools/memory/memory.py"), "--repo", alias, "check", "--json"],
            capture_output=True, text=True, encoding="utf-8", check=True,
        )
        self.assertTrue(json.loads(result.stdout)["ok"])


if __name__ == "__main__":
    unittest.main()
