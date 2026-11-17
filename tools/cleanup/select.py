#!/usr/bin/env python3
"""Pure decision logic for the branch cleanup workflow (T-048, DELIVERY_PLAN §8.2).

Everything in this module is a pure function of its inputs: no git, no network, no file access. Facts about
branches, backups and earlier dry runs are gathered elsewhere (``gitfacts.py`` and the workflow) and passed in.
That keeps every rule unit-testable and makes the safety argument readable in one place.

A branch is deleted only if ALL of these hold; otherwise it is skipped with a reason:
  * the request is valid, its mode is ``delete`` and an earlier, successful dry run of the same request content
    (same request hash) approved this branch at this exact tip SHA;
  * the branch name is valid, exists on the remote and is not protected (fixed names, protected patterns, or a
    branch named in an open row of TASK_LOG.md);
  * its tip is an ancestor of origin/main (fully merged, nothing pushed after the merge);
  * its tip is reachable from a ``backup/*`` tag or an ``archive/backup-*`` branch;
  * the latest completed ``backup.yml`` run on main concluded ``success``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import re

REQUEST_MODES = ("dry-run", "delete")
MAX_BRANCHES = 200

PROTECTED_NAMES = frozenset({
    "main", "master", "staging", "relay-channel", "supervisor-state", "decisions-tools", "cleanup-request",
})
PROTECTED_PREFIXES = ("archive/", "backup/", "codex/")

ACTION_DELETE = "delete"            # mode delete, all conditions hold: the workflow deletes it
ACTION_WOULD_DELETE = "would-delete"  # mode dry-run, all conditions hold
ACTION_SKIP = "skip"

BACKUP_WORKFLOW = "backup.yml"
CLEANUP_WORKFLOW = "cleanup.yml"


class RequestError(ValueError):
    """The cleanup request is malformed; nothing is considered."""


@dataclass(frozen=True)
class Request:
    mode: str
    branches: tuple[str, ...]
    requested_by: str
    reason: str


@dataclass(frozen=True)
class BranchFacts:
    """What git says about one requested branch (gathered by gitfacts.py)."""
    name: str
    exists: bool
    sha: str | None = None
    merged: bool = False                     # tip is an ancestor of origin/main
    backup_refs: tuple[str, ...] = ()        # backup/* tags or archive/backup-* branches containing the tip


@dataclass(frozen=True)
class Decision:
    branch: str
    sha: str | None
    action: str
    reason: str


@dataclass
class DryRunApproval:
    """Outcome of looking up an earlier dry run for this request hash."""
    ok: bool
    reason: str
    run_id: str | None = None
    approved: dict[str, str] = field(default_factory=dict)  # branch -> sha the dry run would have deleted


# --------------------------------------------------------------------------------------------------------------
# Request

def parse_request(text: str) -> Request:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise RequestError(f"REQUEST.json is not valid JSON: {error}") from error
    if not isinstance(data, dict):
        raise RequestError("REQUEST.json must be a JSON object")
    allowed = {"mode", "branches", "requested_by", "reason"}
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise RequestError(f"unknown request fields: {', '.join(unknown)}")
    mode = data.get("mode")
    if mode not in REQUEST_MODES:
        raise RequestError(f"mode must be one of {', '.join(REQUEST_MODES)}, got {mode!r}")
    branches = data.get("branches")
    if not isinstance(branches, list) or not branches:
        raise RequestError("branches must be a non-empty list of branch names")
    if len(branches) > MAX_BRANCHES:
        raise RequestError(f"at most {MAX_BRANCHES} branches per request")
    if not all(isinstance(item, str) for item in branches):
        raise RequestError("every branch must be a string")
    if len(set(branches)) != len(branches):
        raise RequestError("branches contains duplicates")
    for key in ("requested_by", "reason"):
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            raise RequestError(f"{key} must be a non-empty string")
    return Request(mode, tuple(branches), data["requested_by"].strip(), data["reason"].strip())


def request_hash(request: Request) -> str:
    """Hash of the request content WITHOUT the mode, so a dry run and the following delete share one hash."""
    canonical = json.dumps(
        {"branches": list(request.branches), "requested_by": request.requested_by, "reason": request.reason},
        sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------------------------------------------
# Names and protection

_BAD_NAME_CHARS = re.compile(r"[\x00-\x20\x7f~^:?*\[\\]")


def invalid_name_reason(name: str) -> str | None:
    """Rules of git check-ref-format for a branch, plus: no wildcards, no full ref paths."""
    if not name:
        return "empty branch name"
    if name.startswith("refs/") or name.startswith("origin/"):
        return "give the bare branch name, not a ref path"
    if _BAD_NAME_CHARS.search(name):
        return "invalid character in branch name (wildcards are never allowed)"
    if name.startswith("-") or name.startswith("/") or name.endswith("/") or name.endswith(".") or "//" in name:
        return "invalid branch name"
    if ".." in name or "@{" in name or name == "@":
        return "invalid branch name"
    for part in name.split("/"):
        if part.startswith(".") or part.endswith(".lock"):
            return "invalid branch name"
    if name == "HEAD":
        return "invalid branch name"
    return None


def protected_reason(name: str, open_task_branches: frozenset[str] | set[str]) -> str | None:
    if name in PROTECTED_NAMES:
        return f"protected branch '{name}'"
    for prefix in PROTECTED_PREFIXES:
        if name.startswith(prefix):
            return f"protected pattern '{prefix}**'"
    if name in open_task_branches:
        return "named in an open TASK_LOG row"
    return None


# --------------------------------------------------------------------------------------------------------------
# TASK_LOG.md

_CLOSED_STATE = re.compile(r"\b(result accepted|merged|in main|closed|done|rejected|cancell?ed|superseded|abandoned)\b",
                           re.IGNORECASE)
_NEGATED_CLOSED = re.compile(r"\b(not|un|never)[\s-]*(merged|in main|accepted|done)\b|\bunmerged\b", re.IGNORECASE)


def _cells(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    return [cell.strip() for cell in body.split("|")]


def _is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells if cell)


def state_is_closed(state: str) -> bool:
    if _NEGATED_CLOSED.search(state):
        return False
    return bool(_CLOSED_STATE.search(state))


def open_task_rows(task_log: str) -> list[str]:
    """Rows of every markdown table whose State/Status cell is not clearly closed.

    Conservative by design: a row without a recognisable state column, or with any state that is not explicitly
    closed (accepted, merged, in main, ...), counts as open, so its branches stay protected.
    """
    rows: list[str] = []
    header: list[str] | None = None
    state_index: int | None = None
    previous: list[str] | None = None
    for line in task_log.splitlines():
        if not line.strip().startswith("|"):
            header, state_index, previous = None, None, None
            continue
        cells = _cells(line)
        if _is_separator(cells):
            header = previous
            state_index = None
            if header:
                for index, title in enumerate(header):
                    if title.strip("* ").lower() in ("state", "status"):
                        state_index = index
                        break
            continue
        previous = cells
        if header is None:
            continue  # this is a header line, the separator follows
        state = cells[state_index] if state_index is not None and state_index < len(cells) else ""
        if state_index is None or not state_is_closed(state):
            rows.append(line)
    return rows


_NAME_CHARS = r"A-Za-z0-9_\-/"


def branch_named_in(name: str, text: str) -> bool:
    """True if ``name`` occurs in ``text`` as a whole branch-name token (a trailing sentence period is allowed)."""
    pattern = re.compile(rf"(?<![{_NAME_CHARS}.]){re.escape(name)}(?![{_NAME_CHARS}])(?!\.[A-Za-z0-9_])")
    return bool(pattern.search(text))


def open_task_branches(task_log: str, candidates) -> frozenset[str]:
    rows = open_task_rows(task_log)
    return frozenset(name for name in candidates if any(branch_named_in(name, row) for row in rows))


# --------------------------------------------------------------------------------------------------------------
# Backup workflow status

def backup_run_status(runs: list[dict] | None) -> tuple[bool, str]:
    """``runs``: GitHub API workflow runs of backup.yml (any order). None means the lookup failed."""
    if runs is None:
        return False, "backup.yml run status unavailable (lookup failed): no backup = no delete"
    on_main = [run for run in runs if run.get("head_branch") == "main"]
    if not on_main:
        return False, "backup.yml has never run on main: no backup = no delete"
    completed = [run for run in on_main if run.get("status") == "completed"]
    if not completed:
        return False, "no completed backup.yml run on main yet: no backup = no delete"
    latest = max(completed, key=lambda run: (str(run.get("created_at", "")), int(run.get("id", 0) or 0)))
    conclusion = latest.get("conclusion")
    if conclusion != "success":
        return False, f"latest backup.yml run on main ({latest.get('id')}) concluded {conclusion!r}, not 'success'"
    return True, f"latest backup.yml run on main ({latest.get('id')}) concluded success"


# --------------------------------------------------------------------------------------------------------------
# Dry-run log

def dry_run_record(request: Request, run_id: str, date: str, decisions: list[Decision]) -> dict:
    return {
        "date": date,
        "request_hash": request_hash(request),
        "run_id": str(run_id),
        "mode": request.mode,
        "would_delete": {d.branch: d.sha for d in decisions if d.action == ACTION_WOULD_DELETE},
    }


def parse_dry_run_log(text: str) -> list[dict]:
    records = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue  # a damaged line never approves anything
        if isinstance(record, dict):
            records.append(record)
    return records


def runs_to_verify(hash_: str, records: list[dict]) -> list[str]:
    return sorted({str(r.get("run_id")) for r in records if r.get("request_hash") == hash_ and r.get("run_id")})


def verified_run(run: dict | None) -> bool:
    """A recorded dry run counts only if GitHub confirms it was a successful run of cleanup.yml."""
    if not isinstance(run, dict):
        return False
    path = str(run.get("path", ""))
    return path.split("@")[0].endswith(f".github/workflows/{CLEANUP_WORKFLOW}") and run.get("conclusion") == "success"


def dry_run_approval(hash_: str, records: list[dict], run_info: dict[str, dict]) -> DryRunApproval:
    """Find the latest dry run for this hash whose run GitHub confirms as a successful cleanup.yml run."""
    matching = [r for r in records if r.get("request_hash") == hash_ and r.get("mode") == "dry-run"]
    if not matching:
        return DryRunApproval(False, "no earlier dry run for this request content (hash): run mode dry-run first")
    confirmed = [r for r in matching if verified_run(run_info.get(str(r.get("run_id"))))]
    if not confirmed:
        return DryRunApproval(False, "earlier dry run for this hash is not confirmed as a successful cleanup.yml run")
    latest = confirmed[-1]
    approved = latest.get("would_delete") or {}
    if not isinstance(approved, dict):
        approved = {}
    return DryRunApproval(True, f"dry run {latest.get('run_id')} approved", str(latest.get("run_id")),
                          {str(k): str(v) for k, v in approved.items()})


# --------------------------------------------------------------------------------------------------------------
# The decision

def decide_branch(request: Request, facts: BranchFacts, open_tasks: frozenset[str], backup_ok: tuple[bool, str],
                  approval: DryRunApproval | None) -> Decision:
    name = facts.name
    reason = invalid_name_reason(name)
    if reason:
        return Decision(name, None, ACTION_SKIP, reason)
    reason = protected_reason(name, open_tasks)
    if reason:
        return Decision(name, facts.sha, ACTION_SKIP, reason)
    if not facts.exists or not facts.sha:
        return Decision(name, None, ACTION_SKIP, "unknown branch: not on the remote")
    if not facts.merged:
        return Decision(name, facts.sha, ACTION_SKIP, "not merged: tip is not an ancestor of origin/main")
    if not facts.backup_refs:
        return Decision(name, facts.sha, ACTION_SKIP,
                        "no backup: tip not reachable from a backup/* tag or archive/backup-* branch")
    if not backup_ok[0]:
        return Decision(name, facts.sha, ACTION_SKIP, backup_ok[1])
    if request.mode == "dry-run":
        return Decision(name, facts.sha, ACTION_WOULD_DELETE, f"all conditions hold (backup: {facts.backup_refs[0]})")
    if approval is None or not approval.ok:
        return Decision(name, facts.sha, ACTION_SKIP,
                        approval.reason if approval else "no earlier dry run for this request content")
    approved_sha = approval.approved.get(name)
    if approved_sha is None:
        return Decision(name, facts.sha, ACTION_SKIP, f"not approved by dry run {approval.run_id}")
    if approved_sha != facts.sha:
        return Decision(name, facts.sha, ACTION_SKIP,
                        f"tip changed since dry run {approval.run_id} ({approved_sha[:12]} -> {facts.sha[:12]})")
    return Decision(name, facts.sha, ACTION_DELETE,
                    f"all conditions hold; approved by dry run {approval.run_id} (backup: {facts.backup_refs[0]})")


def decide(request: Request, facts: dict[str, BranchFacts], task_log: str, backup_runs: list[dict] | None,
           approval: DryRunApproval | None) -> list[Decision]:
    open_tasks = open_task_branches(task_log, request.branches)
    backup_ok = backup_run_status(backup_runs)
    decisions = []
    for name in request.branches:
        fact = facts.get(name) or BranchFacts(name, exists=False)
        decisions.append(decide_branch(request, fact, open_tasks, backup_ok, approval))
    return decisions


# --------------------------------------------------------------------------------------------------------------
# Reporting and the deletion log

def summary_markdown(request: Request, hash_: str, decisions: list[Decision], header_notes: list[str]) -> str:
    counts = {action: sum(1 for d in decisions if d.action == action)
              for action in (ACTION_DELETE, ACTION_WOULD_DELETE, ACTION_SKIP)}
    lines = [
        f"## Branch cleanup — mode `{request.mode}`",
        "",
        f"- request hash: `{hash_}`",
        f"- requested by: {_md(request.requested_by)}; reason: {_md(request.reason)}",
        *[f"- {_md(note)}" for note in header_notes],
        f"- delete: {counts[ACTION_DELETE]}, would delete: {counts[ACTION_WOULD_DELETE]}, skip: {counts[ACTION_SKIP]}",
        "",
        "| Branch | SHA | Decision | Reason |",
        "| --- | --- | --- | --- |",
    ]
    for d in decisions:
        lines.append(f"| `{_md(d.branch)}` | `{(d.sha or '-')[:12]}` | {d.action} | {_md(d.reason)} |")
    lines += ["", "Restore any deleted branch: `git push origin <sha>:refs/heads/<name>` (SHA from CLEANUP_LOG.md)."]
    return "\n".join(lines) + "\n"


def _md(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


CLEANUP_LOG_HEADER = (
    "# Branch cleanup log\n\n"
    "Written by `.github/workflows/cleanup.yml` on branch `cleanup-request` only. One line per deleted branch.\n"
    "Restore: `git push origin <sha>:refs/heads/<name>`.\n\n"
    "date | branch | sha | request hash\n"
    "--- | --- | --- | ---\n"
)


def cleanup_log_line(date: str, branch: str, sha: str, hash_: str) -> str:
    return f"{date} | {branch} | {sha} | {hash_}"


def parse_cleanup_log(text: str) -> list[dict]:
    entries = []
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.split("|")]
        if len(cells) != 4 or not re.fullmatch(r"[0-9a-f]{40}", cells[2]):
            continue
        entries.append({"date": cells[0], "branch": cells[1], "sha": cells[2], "request_hash": cells[3]})
    return entries


def restore_command(entry: dict, remote: str = "origin") -> list[str]:
    return ["git", "push", remote, f"{entry['sha']}:refs/heads/{entry['branch']}"]
