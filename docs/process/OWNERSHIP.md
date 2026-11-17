# Active task path ownership

Use this table before dispatching parallel tasks. Each active task owns its listed paths exclusively until it is
integrated, cancelled, or explicitly handed off. Prefer exact repository-relative paths; use a trailing `/` only
when the task owns the complete directory. The Supervisor resolves overlaps before work begins.

| Active task | Owner / branch | Owned paths | Status / handoff notes |
| --- | --- | --- | --- |
| T-000: example task | `t-000-example` | `path/to/file.py`<br>`path/to/tests/` | Replace this example row. |

Rules:

- One path has one active owner. Parent directories and matching globs count as overlaps.
- Central files and guarded paths must be named explicitly; approval trailers remain required.
- Update the row when ownership changes, and remove or archive it after integration.
- Generated outputs belong to the task that owns their source unless the Supervisor records a different owner.
