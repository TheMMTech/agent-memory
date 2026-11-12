"""Session capture tests use disposable repositories, local bare remotes, and synthetic canaries only."""

import contextlib
import gzip
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
SPEC = importlib.util.spec_from_file_location("project_memory_sessions", KIT / "tools/memory/memory.py")
memory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(memory)

# Canaries are assembled at runtime so that this file contains no credential shapes.
GITHUB = "ghp_" + "Zq8" * 12
AWS = "AKIA" + "QWERTYUIOPASDFGH"
PASSWORD = "Tr0ub4dor" + "-and-3"
BEARER = "abcDEF123" * 3
EMAIL = "pat.doe" + "@" + "team.example"
PRIVATE = "-----BEGIN RSA " + "PRIVATE KEY-----\nMIIEow" + "IBAAKCAQEA\n-----END RSA " + "PRIVATE KEY-----"
RANDOM = "Xk9" + "pQ2vL7mN4bR8tY1wZ6cF3hJ5sD0gA"


def run_git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                            text=True, encoding="utf-8", check=True)
    return result.stdout.strip()


def commit(root, message):
    run_git(root, "-c", "core.hooksPath=", "-c", "commit.gpgSign=false", "commit", "--allow-empty", "-m", message)
    return run_git(root, "rev-parse", "HEAD")


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="project-memory-session-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / "repo"
        self.root.mkdir()
        run_git(self.root, "init", "--initial-branch=main")
        run_git(self.root, "config", "user.name", "Memory Test")
        run_git(self.root, "config", "user.email", "memory-test@example.invalid")
        commit(self.root, "Initial code state")
        memory.initialize(self.root, KIT, True, False)
        self.cfg = memory.config(self.root)
        self.homes = {name: self.base / name for name in ("claude", "codex", "copilot", "appdata")}
        environment = {"CLAUDE_CONFIG_DIR": str(self.homes["claude"]), "CODEX_HOME": str(self.homes["codex"]),
                       "COPILOT_HOME": str(self.homes["copilot"]), "APPDATA": str(self.homes["appdata"]),
                       "XDG_CONFIG_HOME": str(self.homes["appdata"])}
        patcher = mock.patch.dict(os.environ, environment)
        patcher.start()
        self.addCleanup(patcher.stop)
        for name in [key for key in os.environ if key.startswith("AGENT_MEMORY_")]:
            os.environ.pop(name)
        spawn = mock.patch.object(memory, "spawn_worker")
        self.spawned = spawn.start()
        self.addCleanup(spawn.stop)

    def transcript(self, relative, lines, home="claude"):
        path = self.homes[home] / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(line) for line in lines) + "\n", encoding="utf-8")
        return path

    def stored(self, session_id):
        result = memory.show_session(self.root, session_id, transcript=True, max_chars=0)
        return result["session"], result["transcript"]

    def secret_lines(self):
        return [
            {"type": "user", "message": {"role": "user", "content": f"Deploy with {GITHUB} and email {EMAIL}"}},
            {"type": "assistant", "message": {"role": "assistant", "content": [
                {"type": "tool_use", "input": {"command": f"export AWS_KEY={AWS}; curl -H 'Authorization: Bearer {BEARER}'"}},
                {"type": "text", "text": f"Found key file:\n{PRIVATE}\npassword={PASSWORD}\nsession {RANDOM}"},
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "iVBORw0KGgo" * 40}},
            ]}},
            {"type": "result", "settings": {"client_secret": PASSWORD, "request_id": "req-123"}},
            {"type": "user", "message": {"role": "user", "content": "Use git@github.com:org/repo for the remote."}},
        ]

    def test_v01_configuration_without_session_keys_stays_valid(self):
        path = self.root / "docs/memory/config.json"
        path.write_text(json.dumps(memory.REQUIRED_CONFIG), encoding="utf-8")
        value = memory.config(self.root)
        self.assertTrue(value["session_capture"])
        self.assertEqual(30, value["session_retention_days"])

    def test_invalid_session_configuration_is_rejected(self):
        path = self.root / "docs/memory/config.json"
        for change in ({"session_capture": "yes"}, {"session_retention_days": 0},
                       {"session_max_transcript_bytes": 200 * memory.MIB}, {"session_unknown": True}):
            path.write_text(json.dumps({**memory.DEFAULTS, **change}), encoding="utf-8")
            with self.assertRaises(memory.MemoryError):
                memory.config(self.root)

    def test_kit_repository_keeps_capture_and_push_off(self):
        # The kit's own repository is public; its development sessions are never captured.
        value = memory.config(KIT)
        self.assertFalse(value["session_capture"])
        self.assertFalse(value["session_push"])
        self.assertTrue(memory.DEFAULTS["session_capture"])
        self.assertTrue(memory.DEFAULTS["session_push"])

    def test_retention_precedence_flag_then_variable_then_configuration(self):
        self.assertEqual(30, memory.retention_days(self.cfg))
        with mock.patch.dict(os.environ, {"AGENT_MEMORY_RETENTION_DAYS": "60"}):
            self.assertEqual(60, memory.retention_days(self.cfg))
            self.assertEqual(7, memory.retention_days(self.cfg, 7))
        with mock.patch.dict(os.environ, {"AGENT_MEMORY_RETENTION_DAYS": " "}):
            self.assertEqual(30, memory.retention_days(self.cfg))
        for bad in ("thirty", "0", "-5"):
            with mock.patch.dict(os.environ, {"AGENT_MEMORY_RETENTION_DAYS": bad}):
                with self.assertRaises(memory.MemoryError):
                    memory.retention_days(self.cfg)

    def test_claude_session_is_redacted_linked_and_kept_off_branches(self):
        payload = {"session_id": "claude-1", "hook_event_name": "SessionStart"}
        output = memory.hook(self.root, "SessionStart", io.StringIO(json.dumps(payload)), "claude-code")
        self.assertEqual("SessionStart", output["hookSpecificOutput"]["hookEventName"])
        made = commit(self.root, "Agent change")
        path = self.transcript("projects/repo/claude-1.jsonl", self.secret_lines())
        branches, tree = run_git(self.root, "branch", "--list"), run_git(self.root, "write-tree")
        result = memory.capture_session(self.root, self.cfg, "claude-code", "claude-1", str(path))
        self.assertTrue(result["captured"])
        self.assertRegex(result["ref"], r"^refs/agent-memory/sessions/\d{4}-\d{2}-\d{2}/claude-1$")
        self.assertEqual(branches, run_git(self.root, "branch", "--list"))
        self.assertEqual(tree, run_git(self.root, "write-tree"))
        metadata, text = self.stored("claude-1")
        for canary in (GITHUB, AWS, PASSWORD, BEARER, EMAIL, "MIIEow", RANDOM, "iVBORw0KGgo"):
            self.assertNotIn(canary, text)
        self.assertIn("git@github.com:org/repo", text)
        self.assertIn("[REDACTED:github-token]", text)
        self.assertEqual([made], metadata["commits"])
        self.assertEqual("claude-code", metadata["agent"])
        self.assertGreaterEqual(metadata["transcript"]["redactions"]["image"], 1)
        self.assertNotIn(str(self.base), json.dumps(metadata))  # No local paths or usernames.
        self.assertEqual(result["commit"], run_git(self.root, "rev-parse", result["ref"]))

    def test_unchanged_transcript_is_not_recaptured(self):
        path = self.transcript("projects/a/same.jsonl", [{"role": "user", "content": "hello"}])
        self.assertTrue(memory.capture_session(self.root, self.cfg, "claude-code", "same", str(path))["captured"])
        self.assertFalse(memory.capture_session(self.root, self.cfg, "claude-code", "same", str(path))["captured"])

    def test_transcript_outside_agent_directory_is_refused(self):
        outside = self.base / "elsewhere" / "id_rsa.jsonl"
        outside.parent.mkdir()
        outside.write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(memory.MemoryError, "outside the agent"):
            memory.capture_session(self.root, self.cfg, "claude-code", "s1", str(outside))
        with self.assertRaises(memory.MemoryError):
            memory.capture_session(self.root, self.cfg, "codex", "s1", str(self.homes["claude"] / "x.jsonl"))
        self.assertEqual([], memory.session_refs(self.root))

    def test_copilot_cli_session_end_finds_transcript_from_session_id(self):
        self.transcript("session-state/cli-7/events.jsonl",
                        [{"type": "user.message", "data": {"content": "fix the build"}}], home="copilot")
        payload = json.dumps({"sessionId": "cli-7", "timestamp": 1, "cwd": str(self.root), "reason": "complete"})
        self.assertEqual({}, memory.hook(self.root, "sessionEnd", io.StringIO(payload)))
        self.spawned.assert_called_once()
        summary = memory.run_worker(self.root)
        self.assertEqual(1, summary["captured"])
        metadata, text = self.stored("cli-7")
        self.assertEqual("copilot-cli", metadata["surface"])
        self.assertIn("fix the build", text)

    def test_vscode_stop_payload_uses_shared_hook_file(self):
        path = self.transcript("Code/User/workspaceStorage/abc/GitHub.copilot-chat/transcripts/vs-1.jsonl",
                               [{"role": "user", "content": "explain retries"}], home="appdata")
        payload = json.dumps({"hookEventName": "Stop", "sessionId": "vs-1", "transcript_path": str(path)})
        memory.hook(self.root, "agentStop", io.StringIO(payload))
        memory.run_worker(self.root)
        self.assertEqual("vscode", self.stored("vs-1")[0]["surface"])

    def test_codex_hooks_always_print_json_and_queue_the_turn(self):
        path = self.transcript("sessions/2026/11/04/rollout-x.jsonl",
                               [{"type": "response_item", "payload": {"role": "user", "content": "hi"}}], home="codex")
        payload = json.dumps({"session_id": "codex-1", "transcript_path": str(path), "hook_event_name": "Stop"})
        self.assertEqual({}, memory.hook(self.root, "Stop", io.StringIO(payload), "codex"))
        start = memory.hook(self.root, "SessionStart", io.StringIO('{"session_id": "codex-1"}'), "codex")
        self.assertIn("additionalContext", start["hookSpecificOutput"])
        queued = memory.state_dir(self.root) / "queue" / "codex--codex-1.json"
        self.assertEqual(str(path), json.loads(queued.read_text(encoding="utf-8"))["transcript_path"])

    def test_capture_can_be_disabled_by_configuration_or_variable(self):
        payload = json.dumps({"session_id": "off-1", "transcript_path": "/nowhere.jsonl"})
        with mock.patch.dict(os.environ, {"AGENT_MEMORY_SESSION_CAPTURE": "0"}):
            memory.hook(self.root, "Stop", io.StringIO(payload), "claude-code")
        path = self.root / "docs/memory/config.json"
        path.write_text(json.dumps({**memory.DEFAULTS, "session_capture": False}), encoding="utf-8")
        memory.hook(self.root, "Stop", io.StringIO(payload), "claude-code")
        self.assertFalse((memory.state_dir(self.root) / "queue").exists())
        self.spawned.assert_not_called()

    def test_unsafe_session_ids_are_ignored(self):
        for bad in ("../../etc", "a..b", "x.lock", "-start", "a/b", "", "x" * 200):
            payload = json.dumps({"session_id": bad, "transcript_path": "/tmp/x"})
            self.assertEqual({}, memory.hook(self.root, "Stop", io.StringIO(payload), "claude-code"))
        self.assertFalse((memory.state_dir(self.root) / "queue").exists())

    def test_push_fetch_list_and_retention_with_a_local_remote(self):
        remote = self.base / "remote.git"
        run_git(self.base, "init", "--bare", str(remote))
        run_git(self.root, "remote", "add", "origin", str(remote))
        made = commit(self.root, "Linked change")
        path = self.transcript("projects/p/push-1.jsonl", [{"role": "user", "content": "ship it"}])
        with mock.patch.object(memory, "verify_remotes", return_value=["origin"]):
            memory.capture_session(self.root, self.cfg, "claude-code", "push-1", str(path))
            old = memory.session_refs(self.root)[0]["commit"]
            run_git(self.root, "update-ref", "refs/agent-memory/sessions/2020-01-01/old-1", old)
            self.assertEqual(2, memory.push_sessions(self.root, self.cfg)["pushed"])
            self.assertEqual(0, memory.push_sessions(self.root, self.cfg)["pushed"])
            self.assertIn("refs/agent-memory/sessions/2020-01-01/old-1", run_git(remote, "for-each-ref"))
            clone = self.base / "clone"
            run_git(self.base, "clone", "--quiet", str(remote), str(clone))
            memory.initialize(clone, KIT, True, False)
            self.assertEqual(2, memory.fetch_sessions(clone, memory.config(clone))["fetched_sessions"])
            listed = memory.list_sessions(clone, commit=made)
            self.assertEqual("push-1", listed[0]["session_id"])  # Newest first.
            self.assertEqual("fetched", listed[0]["source"])
            self.assertEqual([], memory.list_sessions(clone, commit="0" * 40))
            self.assertIn("ship it", memory.show_session(clone, "push-1", transcript=True)["transcript"])
            dry = memory.prune_sessions(self.root, self.cfg, remote=True, dry_run=True)
            self.assertEqual((1, 1), (dry["local_expired"], dry["remote_expired"]))
            self.assertEqual(2, len(memory.session_refs(self.root)))
            result = memory.prune_sessions(self.root, self.cfg, remote=True)
            self.assertEqual(1, result["remote_deleted"])
        refs = run_git(remote, "for-each-ref", "refs/agent-memory/")
        self.assertNotIn("old-1", refs)
        self.assertIn("push-1", refs)
        self.assertEqual(["push-1"], [item["id"] for item in memory.session_refs(self.root)])

    def test_rejected_push_is_recorded_once_and_not_retried(self):
        run_git(self.root, "remote", "add", "origin", str(self.base / "unused.git"))
        path = self.transcript("projects/p/rej-1.jsonl", [{"role": "user", "content": "x"}])
        with mock.patch.object(memory, "verify_remotes", return_value=["origin"]):
            result = memory.capture_session(self.root, self.cfg, "claude-code", "rej-1", str(path))
            rejection = f"To remote\n!\t{result['commit']}:{result['ref']}\t[remote rejected] (push declined)\nDone\n"
            with mock.patch.object(memory, "git_network", return_value=(1, rejection)) as network:
                self.assertEqual(1, memory.push_sessions(self.root, self.cfg)["rejected"])
                self.assertEqual(0, memory.push_sessions(self.root, self.cfg, force=True)["rejected"])
                self.assertEqual(1, network.call_count)
        self.assertEqual(1, memory.session_status(self.root, self.cfg)["rejected_pushes"])

    def test_changed_session_waits_for_push_interval_unless_forced(self):
        path = self.transcript("projects/p/thr-1.jsonl", [{"role": "user", "content": "one"}])
        memory.capture_session(self.root, self.cfg, "claude-code", "thr-1", str(path))
        item = memory.session_refs(self.root)[0]
        state = {item["ref"]: {"commit": "0" * 40, "status": "pushed", "at": memory.time.time()}}
        self.assertEqual([], memory.pending_pushes(self.root, state))
        self.assertEqual(1, len(memory.pending_pushes(self.root, state, force=True)))

    def test_push_is_skipped_when_disabled_and_blocked_off_policy(self):
        with mock.patch.dict(os.environ, {"AGENT_MEMORY_SESSION_PUSH": "0"}):
            self.assertIn("skipped", memory.push_sessions(self.root, self.cfg))
        run_git(self.root, "remote", "add", "origin", "https://gitlab.example/org/project.git")
        with self.assertRaises(memory.MemoryError):
            memory.push_sessions(self.root, self.cfg)
        path = self.transcript("projects/p/off.jsonl", [{"role": "user", "content": "x"}])
        with self.assertRaises(memory.MemoryError):
            memory.capture_session(self.root, self.cfg, "claude-code", "off", str(path))

    def test_oversized_transcript_keeps_the_newest_whole_lines(self):
        self.cfg["session_max_transcript_bytes"] = memory.MIB
        lines = [{"n": index, "text": "x" * 500} for index in range(3000)]
        path = self.transcript("projects/p/big.jsonl", lines)
        memory.capture_session(self.root, self.cfg, "claude-code", "big", str(path))
        metadata, text = self.stored("big")
        self.assertTrue(metadata["transcript"]["truncated"])
        self.assertIn('"n":2999', text)
        self.assertNotIn('"n":0,', text)
        json.loads(text.splitlines()[0])  # The first kept line is complete.

    def test_redaction_rules_keep_useful_context(self):
        counts = {}
        cases = {
            "\\n" + GITHUB: "[REDACTED:github-token]",
            "password = settings.DB_PASSWORD": "settings.DB_PASSWORD",
            "token = ${API_TOKEN}": "${API_TOKEN}",
            "https://user:" + PASSWORD + "@github.com/org/repo": "https://user:[REDACTED:credentialed-url]@",
            "commit 4f8e2a9c1b7d3e5f60718293a4b5c6d7e8f90a1b": "4f8e2a9c1b7d3e5f60718293a4b5c6d7e8f90a1b",
            "tenant@tenant.ghe.com:org/repo": "tenant@tenant.ghe.com:org/repo",
            "AccountKey=" + RANDOM + ";EndpointSuffix=core": "AccountKey=[REDACTED:connection-secret];",
        }
        for text, expected in cases.items():
            self.assertIn(expected, memory.redact_text(text, counts, True))
        value = memory.redact_value({"password": PASSWORD, "id": RANDOM, "note": RANDOM}, counts, True)
        self.assertEqual("[REDACTED:credential-value]", value["password"])
        self.assertEqual(RANDOM, value["id"])
        self.assertEqual("[REDACTED:high-entropy]", value["note"])

    def test_worker_lock_prevents_concurrent_workers(self):
        lock = memory.state_dir(self.root) / "worker.lock"
        self.assertTrue(memory.acquire_lock(lock))
        self.assertFalse(memory.run_worker(self.root)["ran"])
        lock.unlink()
        self.assertTrue(memory.run_worker(self.root)["ran"])
        self.assertFalse(lock.exists())

    def test_start_brief_mentions_captured_sessions(self):
        path = self.transcript("projects/p/brief-1.jsonl", [{"role": "user", "content": "x"}])
        memory.capture_session(self.root, self.cfg, "claude-code", "brief-1", str(path))
        self.assertIn("brief-1", memory.bootstrap(self.root, self.cfg))

    def test_init_merges_existing_agent_settings_and_is_idempotent(self):
        target = self.base / "app"
        target.mkdir()
        run_git(target, "init")
        settings = target / ".claude/settings.json"
        settings.parent.mkdir()
        original = {"permissions": {"allow": ["Bash(ls)"]},
                    "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo team"}]}]}}
        settings.write_text(json.dumps(original), encoding="utf-8")
        memory.initialize(target, KIT, True, True)
        merged = json.loads(settings.read_text(encoding="utf-8"))
        self.assertEqual(["Bash(ls)"], merged["permissions"]["allow"])
        self.assertEqual("echo team", merged["hooks"]["Stop"][0]["hooks"][0]["command"])
        self.assertEqual(memory.claude_hooks()["hooks"]["Stop"][0], merged["hooks"]["Stop"][1])
        self.assertTrue((target / ".codex/hooks.json").is_file())
        self.assertTrue((target / ".github/workflows/agent-session-retention.yml").is_file())
        self.assertTrue(json.loads((target / "docs/memory/config.json").read_text())["session_push"])
        self.assertEqual([], memory.initialize(target, KIT, True, True))

    def test_init_refuses_a_changed_project_memory_hook(self):
        target = self.base / "app2"
        target.mkdir()
        run_git(target, "init")
        hooks = target / ".codex/hooks.json"
        hooks.parent.mkdir()
        changed = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "python tools/memory/memory.py hook Stop"}]}]}}
        hooks.write_text(json.dumps(changed), encoding="utf-8")
        with self.assertRaisesRegex(memory.MemoryError, "differs"):
            memory.initialize(target, KIT, True, True)
        self.assertFalse((target / "tools").exists())
        self.assertEqual(changed, json.loads(hooks.read_text(encoding="utf-8")))

    def test_kit_hook_files_match_the_generators(self):
        for relative, generator in ((".github/hooks/project-memory.json", memory.copilot_hooks),
                                    (".claude/settings.json", memory.claude_hooks),
                                    (".codex/hooks.json", memory.codex_hooks)):
            self.assertEqual(generator(), json.loads((KIT / relative).read_text(encoding="utf-8")), relative)

    # --- Regression tests for the independent security review -----------------

    def test_remote_without_url_cannot_receive_sessions(self):
        # No mocks: the real destination check must stop this push.
        target = self.base / "unapproved.git"
        run_git(self.base, "init", "--bare", str(target))
        run_git(self.root, "remote", "add", "origin", "https://github.com/org/repo.git")
        path = self.transcript("projects/p/leak-1.jsonl", [{"role": "user", "content": "x"}])
        memory.capture_session(self.root, self.cfg, "claude-code", "leak-1", str(path))
        run_git(self.root, "config", "remote.ev.fetch", "+refs/heads/*:refs/remotes/ev/*")
        run_git(self.root, "config", "branch.main.remote", "ev")
        run_git(self.root, "config", f"url.{target.as_posix()}.insteadOf", "ev")
        with self.assertRaisesRegex(memory.MemoryError, "no URL"):
            memory.push_sessions(self.root, self.cfg)
        self.assertEqual("", run_git(target, "for-each-ref"))

    def test_remote_named_like_an_option_is_rejected(self):
        run_git(self.root, "config", "remote.--dry-run.url", "https://github.com/org/repo.git")
        with self.assertRaisesRegex(memory.MemoryError, "unsupported name"):
            memory.verify_remotes(self.root)

    def test_pushes_are_pinned_to_the_installed_repository(self):
        target = self.base / "app3"
        target.mkdir()
        run_git(target, "init", "--initial-branch=main")
        run_git(target, "remote", "add", "origin", "https://github.com/Org/App.git")
        memory.initialize(target, KIT, True, False)
        cfg = memory.config(target)
        self.assertEqual("org/app", cfg["session_repository"])
        self.assertEqual("origin", memory.session_remote(target, cfg))
        run_git(target, "remote", "set-url", "origin", "https://github.com/me/app-fork.git")
        run_git(target, "remote", "add", "upstream", "https://github.com/org/app")
        run_git(target, "config", "branch.main.remote", "origin")
        self.assertEqual("upstream", memory.session_remote(target, cfg))
        run_git(target, "remote", "remove", "upstream")
        with self.assertRaisesRegex(memory.MemoryError, "session_repository"):
            memory.session_remote(target, cfg)

    def test_redaction_stays_fast_on_adversarial_text(self):
        hostile = ["a_" * 50000, "a." * 50000 + "@", "x@" + "a." * 20000 + ":", "x_" * 20000 + "password=",
                   "-----BEGIN " + "PRIVATE KEY-----" + "A" * 200000, ("ab" * 20 + "/") * 5000]
        started = memory.time.time()
        for text in hostile:
            memory.redact_text(text, {}, True)
            memory.redact_transcript(json.dumps({"tool_result": text}).encode(), True)
        self.assertLess(memory.time.time() - started, 10)

    def test_more_secret_formats_are_redacted_and_paths_kept(self):
        aws_secret = "Zx81Kq" + "/Pw0Lm9" + "Rt5Yb2Nc7Vd4Hf6Jg3Sa1Qe8Wu"
        pgp = "-----BEGIN PGP " + "PRIVATE KEY BLOCK-----\nlQOYBF" + "xyz\n-----END PGP " + "PRIVATE KEY BLOCK-----"
        azure = "Ab3" + "8Q~" + "dEfGhIjKlMnOpQrStUvWxYz012345678"
        devops = "abcdefghijklmnopqrstuvwxyz234567" + "abcdefghijklmnopqrst"
        webhook = "https://hooks.slack.com/services/" + "T0001/B0001/" + "Xy9Zz8"
        samples = {
            "AWS_SECRET_ACCESS_KEY=" + aws_secret: aws_secret,
            "key: " + pgp: "lQOYBF",
            "secret is " + azure + " ok": azure,
            "pat " + devops + " end": devops,
            "post to " + webhook: "Xy9Zz8",
            "password=Summer2024" + ".Secure": "Summer2024",
            "contact " + EMAIL + ": hello": EMAIL,
            "escaped \\u0022" + GITHUB: GITHUB,
            "see ![](data:image/png;base64," + "iVBORw0KGgo" * 20 + ")": "iVBORw0KGgo",
        }
        for text, secret in samples.items():
            self.assertNotIn(secret, memory.redact_text(text, {}, True), text[:30])
        stored = memory.redact_value({"env": {"AWS_SECRET_ACCESS_KEY": aws_secret}}, {}, True)
        self.assertNotIn(aws_secret, json.dumps(stored))
        for path in ("/Users/shepard/AppData/Local/Temp/claude/af8e6e1950eec632/file.txt",
                     "src/memory/test_sessions_capture_2024.py", "tenant@tenant.ghe.com:org/repo"):
            self.assertIn(path, memory.redact_text(path, {}, True))

    def test_allowlist_excludes_credentials_files_and_hard_links(self):
        credentials = self.homes["codex"] / "auth.json"
        credentials.parent.mkdir(parents=True)
        credentials.write_text("{}", encoding="utf-8")
        notes = self.transcript("projects/p/notes.jsonl", [{"x": 1}])
        renamed = notes.with_suffix(".txt")
        notes.rename(renamed)
        original = self.transcript("projects/p/a.jsonl", [{"x": 1}])
        linked = original.with_name("b.jsonl")
        os.link(original, linked)
        for agent, path, reason in (("codex", credentials, "outside"), ("claude-code", renamed, "jsonl"),
                                    ("claude-code", linked, "hard links")):
            with self.assertRaisesRegex(memory.MemoryError, reason):
                memory.locate_transcript(agent, "s", str(path))

    def test_stale_lock_is_taken_over_and_only_its_owner_releases_it(self):
        lock = memory.state_dir(self.root) / "worker.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text('{"token": "old"}', encoding="utf-8")
        past = memory.time.time() - memory.WORKER_STALE - 60
        os.utime(lock, (past, past))
        token = memory.acquire_lock(lock)
        self.assertTrue(token)
        self.assertIsNone(memory.acquire_lock(lock))
        memory.release_lock(lock, "someone-else")
        self.assertTrue(lock.exists())
        memory.release_lock(lock, token)
        self.assertFalse(lock.exists())

    def test_queued_job_survives_an_unexpected_worker_failure(self):
        payload = json.dumps({"session_id": "keep-1", "transcript_path": "/x.jsonl"})
        memory.hook(self.root, "Stop", io.StringIO(payload), "claude-code")
        job = memory.state_dir(self.root) / "queue" / "claude-code--keep-1.json"
        with mock.patch.object(memory, "capture_session", side_effect=RuntimeError("killed")):
            with self.assertRaises(RuntimeError):
                memory.run_worker(self.root)
        self.assertTrue(job.exists())
        self.assertFalse((memory.state_dir(self.root) / "worker.lock").exists())

    def test_future_dated_and_malformed_remote_refs_expire(self):
        base = "refs/agent-memory/sessions/"
        listing = "\n".join(f"{'a' * 40}\t{base}{name}" for name in (
            "2026-11-03/recent", "2020-01-01/old", "9999-12-31/future", "2020-01-01/deep/c", "2020-1-1/badday"))
        listing += f"\n{'a' * 40}\trefs/heads/main"
        found = memory.expired_refs(listing, "2026-10-05", "2026-11-05")
        self.assertEqual(sorted(base + n for n in ("2020-01-01/old", "9999-12-31/future", "2020-01-01/deep/c",
                                                  "2020-1-1/badday")), sorted(found))

    def test_rejected_batch_is_retried_one_ref_at_a_time(self):
        run_git(self.root, "remote", "add", "origin", str(self.base / "unused.git"))
        results = []
        with mock.patch.object(memory, "verify_remotes", return_value=["origin"]):
            for name in ("bat-1", "bat-2"):
                path = self.transcript(f"projects/p/{name}.jsonl", [{"role": "user", "content": name}])
                results.append(memory.capture_session(self.root, self.cfg, "claude-code", name, str(path)))
            first, second = results

            def line(flag, item):
                return f"{flag}\t{item['commit']}:{item['ref']}\t[status]"
            replies = [(1, f"{line('!', first)}\n{line('!', second)}\n"), (0, line("*", first) + "\n"),
                       (1, line("!", second) + "\n")]
            with mock.patch.object(memory, "git_network", side_effect=replies) as network:
                summary = memory.push_sessions(self.root, self.cfg)
        self.assertEqual((1, 1), (summary["pushed"], summary["rejected"]))
        self.assertEqual(3, network.call_count)

    def test_running_session_is_captured_at_most_once_per_interval(self):
        path = self.transcript("projects/p/thr-2.jsonl", [{"role": "user", "content": "one"}])
        memory.capture_session(self.root, self.cfg, "claude-code", "thr-2", str(path))
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"role": "user", "content": "two"}) + "\n")
        payload = json.dumps({"session_id": "thr-2", "transcript_path": str(path)})
        memory.hook(self.root, "Stop", io.StringIO(payload), "claude-code")
        summary = memory.run_worker(self.root)
        self.assertEqual((0, 1), (summary["captured"], summary["deferred"]))
        self.assertTrue((memory.state_dir(self.root) / "queue" / "claude-code--thr-2.json").exists())
        memory.hook(self.root, "SessionEnd", io.StringIO(payload), "claude-code")
        self.assertEqual(1, memory.run_worker(self.root)["captured"])
        self.assertIn("two", self.stored("thr-2")[1])

    def test_ended_session_skips_the_push_interval(self):
        path = self.transcript("projects/p/end-1.jsonl", [{"role": "user", "content": "one"}])
        memory.capture_session(self.root, self.cfg, "claude-code", "end-1", str(path))
        item = memory.session_refs(self.root)[0]
        state = {item["ref"]: {"commit": "0" * 40, "status": "pushed", "at": memory.time.time()}}
        self.assertEqual(1, len(memory.pending_pushes(self.root, state, force_ids={"end-1"})))

    def test_start_hook_keeps_the_brief_when_bookkeeping_fails(self):
        with mock.patch.object(memory, "record_start", side_effect=memory.MemoryError("disk full")):
            output = memory.hook(self.root, "SessionStart", io.StringIO('{"session_id": "s-1"}'), "claude-code")
        self.assertIn("additionalContext", output["hookSpecificOutput"])

    def test_vscode_payload_through_another_hook_file_is_attributed_to_copilot(self):
        payload = json.dumps({"hookEventName": "Stop", "session_id": "vs-2", "transcript_path": "/x.jsonl"})
        memory.hook(self.root, "Stop", io.StringIO(payload), "claude-code")
        self.assertTrue((memory.state_dir(self.root) / "queue" / "copilot--vs-2.json").exists())

    def test_session_commits_carry_no_developer_email(self):
        path = self.transcript("projects/p/who-1.jsonl", [{"role": "user", "content": "x"}])
        result = memory.capture_session(self.root, self.cfg, "claude-code", "who-1", str(path))
        self.assertEqual("project-memory@invalid", run_git(self.root, "log", "-1", "--format=%ae%n%ce",
                                                           result["commit"]).splitlines()[0])
        self.assertNotIn("memory-test@example.invalid", run_git(self.root, "log", "-1", "--format=%ae %ce",
                                                                result["commit"]))
        self.assertEqual("Memory Test", self.stored("who-1")[0]["developer"])

    def test_cli_expired_prints_refs_from_saved_listing(self):
        listing = self.base / "refs.txt"
        listing.write_text(f"{'a' * 40}\trefs/agent-memory/sessions/2020-01-01/old\n", encoding="utf-8")
        command = [sys.executable, str(self.root / "tools/memory/memory.py"), "--repo", str(self.root),
                   "sessions", "expired", "--ls-remote-file", str(listing)]
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=True)
        self.assertEqual(["refs/agent-memory/sessions/2020-01-01/old"], result.stdout.split())

    # --- Second review pass ----------------------------------------------------

    def test_users_own_ssh_program_is_respected(self):
        real, seen = subprocess.run, []

        def spy(command, *args, **kwargs):
            if "credential.interactive=false" in command:
                seen.append(kwargs.get("env") or {})
            return real(command, *args, **kwargs)
        with mock.patch.object(memory.subprocess, "run", side_effect=spy):
            with mock.patch.dict(os.environ, {"GIT_SSH": "plink.exe"}):
                os.environ.pop("GIT_SSH_COMMAND", None)
                memory.git_network(self.root, "--version")
            with mock.patch.dict(os.environ, {}):
                os.environ.pop("GIT_SSH", None)
                os.environ.pop("GIT_SSH_COMMAND", None)
                memory.git_network(self.root, "--version")
        self.assertNotIn("GIT_SSH_COMMAND", seen[0])
        self.assertEqual("ssh -o BatchMode=yes", seen[1]["GIT_SSH_COMMAND"])

    def test_camel_case_and_pwd_keys_are_redacted(self):
        value = "Hunter2" + "Pass!x"
        token = "abc123XYZ" + "987secretvalue"
        stored = memory.redact_value({"dbPassword": value, "githubToken": token, "SecretAccessKey": token,
                                      "SessionToken": token, "tokenCount": 12}, {}, True)
        self.assertNotIn(value, json.dumps(stored))
        self.assertNotIn(token, json.dumps(stored))
        self.assertEqual(12, stored["tokenCount"])
        for text in ("dbPassword=" + value, "MYSQL_PWD=" + value, "export githubToken=" + token):
            self.assertNotIn(value if "Hunter" in text else token, memory.redact_text(text, {}, True), text)

    def test_one_short_segment_does_not_shield_a_bare_secret(self):
        secret = "Xk9pQ2vL7mN4" + "/7/" + "bR8tY1wZ6cF3hJ5sD0gAqWe"
        self.assertNotIn(secret, memory.redact_text("value " + secret, {}, True))

    def test_oversized_fetched_metadata_is_not_read(self):
        blob = memory.git_bytes(self.root, "hash-object", "-w", "--stdin",
                                data=json.dumps({"agent": "x", "pad": "y" * 100000}).encode()).decode().strip()
        tree = memory.git_bytes(self.root, "mktree", data=f"100644 blob {blob}\tsession.json\n".encode()).decode().strip()
        made = memory.git_bytes(self.root, "commit-tree", tree, "-m", "big",
                                env=dict(os.environ, **memory.SESSION_IDENTITY)).decode().strip()
        run_git(self.root, "update-ref", "refs/agent-memory/remote/sessions/2026-11-04/huge", made)
        listed = memory.list_sessions(self.root)
        self.assertEqual(["huge"], [item["session_id"] for item in listed])
        self.assertIsNone(listed[0]["agent"])
        self.assertEqual({}, memory.session_metadata(self.root, made))

    def test_init_preview_shows_the_repository_it_will_pin(self):
        target = self.base / "app4"
        target.mkdir()
        run_git(target, "init")
        run_git(target, "remote", "add", "origin", "tenant@tenant.ghe.com:Org/App4.git")
        changes = memory.initialize(target, KIT, False, False)
        planned = [item for item in changes if item["path"] == "docs/memory/config.json"]
        self.assertEqual("org/app4", planned[0]["session_repository"])

    def test_push_refreshes_the_worker_lock(self):
        run_git(self.root, "remote", "add", "origin", str(self.base / "unused.git"))
        path = self.transcript("projects/p/hb-1.jsonl", [{"role": "user", "content": "x"}])
        beats = []
        with mock.patch.object(memory, "verify_remotes", return_value=["origin"]):
            memory.capture_session(self.root, self.cfg, "claude-code", "hb-1", str(path))
            with mock.patch.object(memory, "git_network", return_value=(1, "")):
                memory.push_sessions(self.root, self.cfg, heartbeat=lambda: beats.append(1))
        self.assertEqual(1, len(beats))

    def test_cli_sessions_status_and_claude_start_hook(self):
        command = [sys.executable, str(self.root / "tools/memory/memory.py"), "--repo", str(self.root)]
        result = subprocess.run([*command, "sessions", "status", "--json"], capture_output=True,
                                text=True, encoding="utf-8", check=True)
        self.assertTrue(json.loads(result.stdout)["capture_enabled"])
        result = subprocess.run([*command, "hook", "--agent", "claude-code", "SessionStart"],
                                input=b'{"session_id": "cli-start"}', capture_output=True, check=True)
        self.assertIn("additionalContext", json.loads(result.stdout.decode("utf-8"))["hookSpecificOutput"])


if __name__ == "__main__":
    unittest.main()
