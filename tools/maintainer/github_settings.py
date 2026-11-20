#!/usr/bin/env python3
"""Check or apply this kit repository's own GitHub settings.

Maintainer tool for TheMMTech/agent-memory only. The initializer never copies
it into other projects. It needs the GitHub CLI (`gh`) logged in as a
repository admin who can also manage the organization's teams.

    python tools/maintainer/github_settings.py            # report drift, change nothing
    python tools/maintainer/github_settings.py --apply    # make GitHub match

Rulesets, branch protection and push protection need a public repository on
GitHub Free. While the repository is private those items are reported as
"needs public" and skipped; run again with --apply right after the switch.
Exit status: 0 when everything matches (or was applied), 1 on drift or errors.
"""

import argparse
import json
import subprocess
import sys

REPO = "TheMMTech/agent-memory"
ORG = "TheMMTech"
TEAM = "maintainers"
TEAM_MEMBERS = ["pozzuoli"]
TEAM_PERMISSION = "maintain"
TOPICS = [
    "agent-memory", "ai-agents", "claude-code", "codex", "github-copilot",
    "developer-tools", "git", "python",
]
GITHUB_ACTIONS_APP = 15368  # integration id that must report the required checks
REQUIRED_CHECKS = [
    "test (ubuntu-latest, 3.10)",
    "test (ubuntu-latest, 3.14)",
    "test (windows-latest, 3.10)",
    "test (windows-latest, 3.14)",
    "Analyze (python)",
    "Analyze (actions)",
]
ADMIN_ROLE = 5  # built-in repository role id for "admin"

REPO_FIELDS = {
    "has_wiki": False,
    "has_projects": False,
    "has_discussions": False,
    "has_issues": True,
    "allow_squash_merge": True,
    "allow_merge_commit": False,
    "allow_rebase_merge": False,
    "allow_auto_merge": False,
    "allow_update_branch": True,
    "delete_branch_on_merge": True,
    "squash_merge_commit_title": "PR_TITLE",
    "squash_merge_commit_message": "PR_BODY",
    "web_commit_signoff_required": False,
}
SECURITY_AND_ANALYSIS = ["secret_scanning", "secret_scanning_push_protection"]

RULESETS = [
    {
        "name": "main",
        "target": "branch",
        "enforcement": "active",
        "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
        # Admins may merge a pull request past a rule (for example when CI is
        # broken upstream) but cannot push to main directly.
        "bypass_actors": [
            {"actor_id": ADMIN_ROLE, "actor_type": "RepositoryRole", "bypass_mode": "pull_request"},
        ],
        "rules": [
            {"type": "deletion"},
            {"type": "non_fast_forward"},
            {"type": "required_linear_history"},
            {"type": "required_signatures"},
            {
                "type": "pull_request",
                "parameters": {
                    "required_approving_review_count": 0,
                    "dismiss_stale_reviews_on_push": True,
                    "require_code_owner_review": False,
                    "require_last_push_approval": False,
                    "required_review_thread_resolution": True,
                    "allowed_merge_methods": ["squash"],
                },
            },
            {
                "type": "required_status_checks",
                "parameters": {
                    "strict_required_status_checks_policy": True,
                    "do_not_enforce_on_create": False,
                    "required_status_checks": [
                        {"context": c, "integration_id": GITHUB_ACTIONS_APP} for c in REQUIRED_CHECKS
                    ],
                },
            },
            {
                "type": "code_scanning",
                "parameters": {
                    "code_scanning_tools": [
                        {"tool": "CodeQL", "security_alerts_threshold": "high_or_higher", "alerts_threshold": "errors"},
                    ],
                },
            },
        ],
    },
    {
        "name": "release tags",
        "target": "tag",
        "enforcement": "active",
        "conditions": {"ref_name": {"include": ["refs/tags/v*"], "exclude": []}},
        # Only admins create release tags; nobody moves or deletes one without
        # an explicit admin bypass.
        "bypass_actors": [
            {"actor_id": ADMIN_ROLE, "actor_type": "RepositoryRole", "bypass_mode": "always"},
        ],
        "rules": [{"type": "creation"}, {"type": "update"}, {"type": "deletion"}, {"type": "non_fast_forward"}],
    },
]


class NeedsPublic(Exception):
    pass


def gh(method, path, body=None, ok_missing=False, accept="application/vnd.github+json"):
    """Call the GitHub REST API through gh; return parsed JSON, True for 204, None for 404."""
    cmd = ["gh", "api", "--method", method, "-H", f"Accept: {accept}", path, "-i"]
    if body is not None:
        cmd += ["--input", "-"]
    proc = subprocess.run(cmd, input=json.dumps(body) if body is not None else None,
                          capture_output=True, text=True, encoding="utf-8")
    head, _, payload = proc.stdout.replace("\r\n", "\n").partition("\n\n")
    status = int(head.split()[1]) if head.startswith("HTTP/") else 0
    if ok_missing and (status == 404 or (status == 409 and "All actions" in payload)):
        return None  # not configured (409: selected-actions while all actions are allowed)
    text = payload + proc.stderr
    if status in (403, 422) and ("make this repository public" in text or "for private repositories" in text
                                  or "Advanced Security must be enabled" in text):
        raise NeedsPublic(path)
    if proc.returncode != 0 or status >= 400:
        raise RuntimeError(f"{method} {path}: HTTP {status} {(payload or proc.stderr).strip()[:300]}")
    if status == 204 or not payload.strip():
        return True
    return json.loads(payload)


class Runner:
    def __init__(self, apply):
        self.apply = apply
        self.drift = 0
        self.errors = 0

    def item(self, name, current, wanted, fix):
        if current == wanted:
            print(f"  ok         {name}")
            return
        if not self.apply:
            self.drift += 1
            print(f"  DRIFT      {name}: is {current!r}, want {wanted!r}")
            return
        fix()
        print(f"  applied    {name}: {current!r} -> {wanted!r}")

    def section(self, title, func):
        print(title)
        try:
            func()
        except NeedsPublic:
            self.drift += 1
            print("  needs public  (GitHub Free allows this only on a public repository)")
        except RuntimeError as exc:
            self.errors += 1
            print(f"  ERROR      {exc}")


def team_section(r):
    team = gh("GET", f"orgs/{ORG}/teams/{TEAM}", ok_missing=True)
    r.item("team exists", team is not None, True, lambda: gh("POST", f"orgs/{ORG}/teams", {
        "name": TEAM, "privacy": "closed",
        "description": "Maintainers of agent-memory (CODEOWNERS)"}))
    for login in TEAM_MEMBERS:
        m = gh("GET", f"orgs/{ORG}/teams/{TEAM}/memberships/{login}", ok_missing=True) if team or r.apply else None
        state = m.get("state") if isinstance(m, dict) else None
        r.item(f"team member {login}", state, "active", lambda login=login: gh(
            "PUT", f"orgs/{ORG}/teams/{TEAM}/memberships/{login}", {"role": "maintainer"}))
    perm = None
    if team or r.apply:
        p = gh("GET", f"orgs/{ORG}/teams/{TEAM}/repos/{REPO}", ok_missing=True,
               accept="application/vnd.github.v3.repository+json")
        if isinstance(p, dict):
            perm = p.get("role_name")
    r.item("team repo role", perm, TEAM_PERMISSION, lambda: gh(
        "PUT", f"orgs/{ORG}/teams/{TEAM}/repos/{REPO}", {"permission": TEAM_PERMISSION}))


def repo_section(r):
    repo = gh("GET", f"repos/{REPO}")
    # GitHub validates the squash title and message as a pair, so send them together.
    pair = ("squash_merge_commit_title", "squash_merge_commit_message")
    for key, want in REPO_FIELDS.items():
        if key in pair:
            continue
        r.item(key, repo.get(key), want, lambda key=key, want=want: gh("PATCH", f"repos/{REPO}", {key: want}))
    want_pair = {k: REPO_FIELDS[k] for k in pair}
    r.item("squash commit title and message", {k: repo.get(k) for k in pair}, want_pair,
           lambda: gh("PATCH", f"repos/{REPO}", want_pair))
    topics = gh("GET", f"repos/{REPO}/topics")["names"]
    r.item("topics", sorted(topics), sorted(TOPICS), lambda: gh("PUT", f"repos/{REPO}/topics", {"names": TOPICS}))


def security_section(r):
    repo = gh("GET", f"repos/{REPO}")
    if repo.get("private"):
        raise NeedsPublic("security_and_analysis")
    sa = repo.get("security_and_analysis") or {}
    for key in SECURITY_AND_ANALYSIS:
        r.item(key, (sa.get(key) or {}).get("status"), "enabled", lambda key=key: gh(
            "PATCH", f"repos/{REPO}", {"security_and_analysis": {key: {"status": "enabled"}}}))
    alerts = gh("GET", f"repos/{REPO}/vulnerability-alerts", ok_missing=True) is True
    r.item("Dependabot alerts", alerts, True, lambda: gh("PUT", f"repos/{REPO}/vulnerability-alerts"))
    fixes = (gh("GET", f"repos/{REPO}/automated-security-fixes", ok_missing=True) or {})
    r.item("Dependabot security updates", isinstance(fixes, dict) and fixes.get("enabled"), True,
           lambda: gh("PUT", f"repos/{REPO}/automated-security-fixes"))
    pvr = gh("GET", f"repos/{REPO}/private-vulnerability-reporting", ok_missing=True) or {}
    r.item("private vulnerability reporting", isinstance(pvr, dict) and pvr.get("enabled"), True,
           lambda: gh("PUT", f"repos/{REPO}/private-vulnerability-reporting"))
    imm = gh("GET", f"repos/{REPO}/immutable-releases", ok_missing=True) or {}
    r.item("immutable releases", isinstance(imm, dict) and imm.get("enabled"), True,
           lambda: gh("PUT", f"repos/{REPO}/immutable-releases"))


def actions_section(r):
    perms = gh("GET", f"repos/{REPO}/actions/permissions")
    want = {"enabled": True, "allowed_actions": "selected", "sha_pinning_required": True}
    r.item("allowed actions", {k: perms.get(k) for k in want}, want,
           lambda: gh("PUT", f"repos/{REPO}/actions/permissions", want))
    want_sel = {"github_owned_allowed": True, "verified_allowed": False,
                "patterns_allowed": ["ossf/scorecard-action@*"]}
    sel = gh("GET", f"repos/{REPO}/actions/permissions/selected-actions", ok_missing=True) or {}
    cur_sel = {k: sel.get(k) for k in want_sel} if isinstance(sel, dict) else {}
    r.item("selected actions", cur_sel, want_sel,
           lambda: gh("PUT", f"repos/{REPO}/actions/permissions/selected-actions", want_sel))
    want_wf = {"default_workflow_permissions": "read", "can_approve_pull_request_reviews": False}
    wf = gh("GET", f"repos/{REPO}/actions/permissions/workflow")
    r.item("workflow token", {k: wf.get(k) for k in want_wf}, want_wf,
           lambda: gh("PUT", f"repos/{REPO}/actions/permissions/workflow", want_wf))
    fork = gh("GET", f"repos/{REPO}/actions/permissions/fork-pr-contributor-approval", ok_missing=True) or {}
    r.item("fork PR approval", isinstance(fork, dict) and fork.get("approval_policy"), "all_external_contributors",
           lambda: gh("PUT", f"repos/{REPO}/actions/permissions/fork-pr-contributor-approval",
                      {"approval_policy": "all_external_contributors"}))


def normalize(ruleset):
    keep = ("name", "target", "enforcement", "conditions", "bypass_actors", "rules")
    out = {k: ruleset.get(k) for k in keep}
    out["bypass_actors"] = sorted(
        ({k: a.get(k) for k in ("actor_id", "actor_type", "bypass_mode")} for a in out["bypass_actors"] or []),
        key=json.dumps)
    out["rules"] = sorted(out["rules"] or [], key=lambda x: x["type"])
    return json.loads(json.dumps(out, sort_keys=True))


def covers(current, wanted):
    """True when every key set in wanted has the same value in current (GitHub adds defaults)."""
    if isinstance(wanted, dict):
        return isinstance(current, dict) and all(covers(current.get(k), v) for k, v in wanted.items())
    if isinstance(wanted, list):
        return (isinstance(current, list) and len(current) == len(wanted)
                and all(covers(c, w) for c, w in zip(current, wanted)))
    return current == wanted


def rulesets_section(r):
    # The required checks below only work while CodeQL uploads from codeql.yml;
    # GitHub's default code scanning setup would reject those uploads.
    setup = gh("GET", f"repos/{REPO}/code-scanning/default-setup")
    if setup.get("state") != "not-configured":
        raise RuntimeError("code scanning default setup is enabled; turn it off so codeql.yml can upload")
    existing = {rs["name"]: rs["id"] for rs in gh("GET", f"repos/{REPO}/rulesets?includes_parents=false")}
    for want in RULESETS:
        rid = existing.get(want["name"])
        current = normalize(gh("GET", f"repos/{REPO}/rulesets/{rid}")) if rid else None
        if rid:
            fix = lambda rid=rid, want=want: gh("PUT", f"repos/{REPO}/rulesets/{rid}", want)
        else:
            fix = lambda want=want: gh("POST", f"repos/{REPO}/rulesets", want)
        shown = "missing" if current is None else ("differs" if not covers(current, normalize(want)) else "matches")
        r.item(f"ruleset '{want['name']}'", shown, "matches", fix)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="change GitHub to match (default: report only)")
    parser.add_argument("--without-rulesets", action="store_true",
                        help="skip rulesets (first run after going public, before CodeQL has a green run on main)")
    args = parser.parse_args()
    r = Runner(args.apply)
    print(f"{REPO}: {'applying' if args.apply else 'checking (read-only)'}")
    r.section("Team and CODEOWNERS", lambda: team_section(r))
    r.section("Repository", lambda: repo_section(r))
    r.section("Actions", lambda: actions_section(r))
    r.section("Security features", lambda: security_section(r))
    if args.without_rulesets:
        print("Rulesets\n  skipped    (--without-rulesets)")
    else:
        r.section("Rulesets", lambda: rulesets_section(r))
    print(f"drift: {r.drift}  errors: {r.errors}")
    return 1 if r.drift or r.errors else 0


if __name__ == "__main__":
    sys.exit(main())
