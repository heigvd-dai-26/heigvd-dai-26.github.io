#!/usr/bin/env bash
#
# new-year.sh — set up a new semester's course org.
#
# The GitHub org itself must be created manually first (GitHub has no API
# for org creation): https://github.com/organizations/plan
# Everything after that is automated here:
#   1. fork the upstream course repo into the org
#   2. rename the fork to <org>.github.io so the site serves at the root
#      URL (https://<org>.github.io/) instead of /dai-course/
#   3. enable Actions on the fork (disabled by default on forks)
#   4. enable GitHub Pages (built by the publish workflow)
#   5. trigger the first site build
#
# Usage: ./new-year.sh <org> [upstream]
#   e.g. ./new-year.sh heigvd-dai-27

set -euo pipefail

UPSTREAM="${2:-HEIG-Courses/dai-course}"
UPSTREAM_NAME="${UPSTREAM#*/}"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <org> [upstream (default: $UPSTREAM)]" >&2
  exit 1
fi
ORG="$1"
SITE_REPO="${ORG}.github.io"
FORK="$ORG/$SITE_REPO"

echo "==> Checking gh authentication"
gh auth status >/dev/null

echo "==> Checking that org '$ORG' exists and is accessible"
if ! gh api "orgs/$ORG" --jq .login >/dev/null 2>&1; then
  echo "Org '$ORG' not found. Create it first: https://github.com/organizations/plan" >&2
  exit 1
fi

echo "==> Forking $UPSTREAM into $ORG (as $SITE_REPO)"
if gh api "repos/$FORK" --jq .full_name >/dev/null 2>&1; then
  echo "    $FORK already exists, skipping fork"
else
  gh repo fork "$UPSTREAM" --org "$ORG" --clone=false --default-branch-only
  # The fork is created asynchronously; wait until it is queryable
  for _ in $(seq 1 30); do
    gh api "repos/$ORG/$UPSTREAM_NAME" --jq .full_name >/dev/null 2>&1 && break
    sleep 2
  done
  gh api -X PATCH "repos/$ORG/$UPSTREAM_NAME" -f name="$SITE_REPO" >/dev/null
fi

echo "==> Enabling Actions on the fork"
gh api -X PUT "repos/$FORK/actions/permissions" \
  -F enabled=true -f allowed_actions=all >/dev/null

echo "==> Enabling GitHub Pages (workflow build)"
if ! gh api "repos/$FORK/pages" >/dev/null 2>&1; then
  gh api -X POST "repos/$FORK/pages" -f build_type=workflow >/dev/null
else
  gh api -X PUT "repos/$FORK/pages" -f build_type=workflow >/dev/null
fi

echo "==> Triggering the first site build"
if ! gh workflow run publish.yml -R "$FORK" 2>/dev/null; then
  echo "    Could not trigger publish.yml (workflow may need a first push); run:"
  echo "    gh workflow run publish.yml -R $FORK"
fi

echo
echo "Done. Site will be at: https://${SITE_REPO}/"
echo
echo "Manual checklist:"
echo "  [ ] Invite co-teacher(s) to the org (owner role)"
echo "  [ ] Enable org Discussions if used for the course"
echo "  [ ] Update the year variables (_variables.yml: year, org, dates)"
echo "  [ ] Update the schedule table(s) in index.qmd"
echo "  [ ] Invite/onboard students (org members or public visibility)"
