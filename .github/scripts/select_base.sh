#!/usr/bin/env bash
# Quality gate planning (T-041): comparison base, trial-merge target and whether the Windows job runs.
# Inputs (env): REF_NAME, BEFORE_SHA, HEAD_MESSAGE, GITHUB_EVENT_NAME. Writes base/merge_target/windows to $GITHUB_OUTPUT.
set -euo pipefail
git fetch --no-tags origin +main:refs/remotes/origin/main +staging:refs/remotes/origin/staging 2>/dev/null \
  || git fetch --no-tags origin +main:refs/remotes/origin/main
zero=0000000000000000000000000000000000000000
staging=origin/staging
git rev-parse --verify --quiet "$staging" >/dev/null || staging=origin/main
case "$REF_NAME" in
  main)
    if [ -n "${BEFORE_SHA:-}" ] && [ "$BEFORE_SHA" != "$zero" ] && git cat-file -e "$BEFORE_SHA^{commit}" 2>/dev/null; then
      base=$BEFORE_SHA
    else
      base=HEAD^
    fi
    target='' ;;
  staging|integration/*)
    base=origin/main; target=origin/main ;;
  *)
    # Task branches are cut from staging and finish on top of it (plan §3): compare and trial-merge with staging.
    base=$staging; target=$staging ;;
esac
windows=false
case "$REF_NAME" in main|staging) windows=true ;; esac
[ "${GITHUB_EVENT_NAME:-}" = workflow_dispatch ] && windows=true
case "${HEAD_MESSAGE:-}" in *"[ci windows]"*) windows=true ;; esac
echo "base=$base merge_target=$target windows=$windows"
{
  echo "base=$base"
  echo "merge_target=$target"
  echo "windows=$windows"
} >> "$GITHUB_OUTPUT"
