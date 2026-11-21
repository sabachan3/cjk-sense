#!/usr/bin/env bash
# End to end, on the files a release would upload. Not part of the gate.
#   1. build the sdist, and the wheel from that sdist
#   2. both archives hold exactly the expected files and metadata (evals/package_contents.py),
#      and `twine check --strict` accepts them
#   3. the wheel and the sdist are each installed into their own throwaway environment
#   4. each installed command prints its version and usage, then checks three pages served
#      over HTTP in a real browser (evals/e2e.py)
#   scripts/e2e.sh [--dist DIR] [--channel chrome|msedge]
# --dist DIR  after every step passed, copy the two archives into DIR (new or empty). The release
#             workflow uploads from there, so what is published is what was installed and run here.
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
DIST=""
PASS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --dist)
      [ $# -ge 2 ] || { echo "e2e: --dist needs a directory" >&2; exit 2; }
      DIST="$2"; shift 2 ;;
    *) PASS+=("$1"); shift ;;
  esac
done
if [ -n "$DIST" ]; then
  case "$DIST" in /*) ;; *) DIST="$PWD/$DIST" ;; esac
  if [ -e "$DIST" ] && { [ ! -d "$DIST" ] || [ -n "$(ls -A "$DIST")" ]; }; then
    echo "e2e: --dist $DIST must be a new or an empty directory" >&2; exit 2
  fi
fi
WORK="$(mktemp -d "${TMPDIR:-/tmp}/cjk-sense-e2e.XXXXXX")"
trap 'rm -r "$WORK"' EXIT
cd "$ROOT"
uv build --quiet --out-dir "$WORK/dist"
uv venv --quiet "$WORK/venv-wheel"
uv venv --quiet "$WORK/venv-sdist"
# From here on outside the repository, so only the built files and the installed package are used.
cd "$WORK"
"$WORK/venv-wheel/bin/python" "$ROOT/evals/package_contents.py" "$WORK/dist"
uv run --quiet --no-project --with-requirements "$ROOT/requirements-package.txt" twine check --strict "$WORK"/dist/*.whl "$WORK"/dist/*.tar.gz
WHEEL="$(basename "$WORK"/dist/*.whl)"
VERSION="${WHEEL#cjk_sense-}"; VERSION="${VERSION%%-*}"   # the contents check tied this name to pyproject.toml
# The browser driver is held at the pinned version, the one whose browser build CI installs.
uv pip install --quiet --python "$WORK/venv-wheel/bin/python" --constraint "$ROOT/requirements-browser.txt" "$WORK"/dist/*.whl
uv pip install --quiet --python "$WORK/venv-sdist/bin/python" --constraint "$ROOT/requirements-browser.txt" "$WORK"/dist/*.tar.gz
for KIND in wheel sdist; do
  "$WORK/venv-$KIND/bin/python" "$ROOT/evals/e2e.py" --command "$WORK/venv-$KIND/bin/cjk-sense" --work "$WORK/site-$KIND" \
    --label "$KIND" --expect-version "$VERSION" ${PASS[@]+"${PASS[@]}"}
done
if [ -n "$DIST" ]; then
  mkdir -p "$DIST"
  cp "$WORK"/dist/*.whl "$WORK"/dist/*.tar.gz "$DIST"/
  echo "e2e: copied to $DIST: $(ls "$DIST" | tr '\n' ' ')"
fi
