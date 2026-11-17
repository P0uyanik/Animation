# GitHub rulesets (import once)

The cloud sessions cannot change repository settings (the proxy allows code pushes only), so the owner imports these.

**How:** GitHub → repository **Settings → Rules → Rulesets → New ruleset → Import a ruleset**, choose a file,
check it shows *Active*, click **Create**. Repeat for all three files.

| File | Protects | Rules |
| --- | --- | --- |
| `1-protect-main-staging.json` | `main`, `staging` | no deletion, no force-push / history rewrite |
| `2-protect-process-archive-branches.json` | `relay-channel`, `supervisor-state`, `decisions-tools`, `archive/**`, `codex/**` | no deletion, no force-push |
| `3-protect-backup-tags.json` | tags `backup/**`, `backup-*` | no deletion, no moving, no force-update (creating new backup tags stays allowed) |

No bypass list: nobody (not even admins or agents) can delete or rewrite these by accident; the owner can still edit
or disable a ruleset in Settings in an emergency.

**Why not "require status checks" / "restrict pushes" yet:**
- All sessions push with the owner's identity (admin), so a push restriction would not separate the Supervisor from
  Implementers; the Supervisor-only rule for `main`/`staging` is enforced by process and by the gate instead.
- The GitHub-hosted quality gate has not passed on GitHub runners yet (it passes locally). Requiring it now would
  block every merge. Once T-041/42 makes it green on GitHub, add to ruleset 1: *Require status checks to pass*
  → the "Quality gate" jobs (applies to `main`; `staging` commits are checked before promotion).
