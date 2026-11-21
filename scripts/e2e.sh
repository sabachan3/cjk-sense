#!/usr/bin/env bash
# End to end: build the wheel, install it into a throwaway environment, serve three pages over
# HTTP and run the installed command against them in a real browser. Not part of the gate.
#   scripts/e2e.sh [--channel chrome|msedge]
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/cjk-sense-e2e.XXXXXX")"
trap 'rm -r "$WORK"' EXIT
cd "$ROOT"
uv build --quiet --wheel --out-dir "$WORK/dist"
uv venv --quiet "$WORK/venv"
# The browser driver is held at the pinned version, the one whose browser build CI installs.
uv pip install --quiet --python "$WORK/venv/bin/python" --constraint "$ROOT/requirements-browser.txt" "$WORK"/dist/*.whl
# Run from outside the repository so only the installed package can be imported.
cd "$WORK"
"$WORK/venv/bin/python" "$ROOT/evals/e2e.py" --command "$WORK/venv/bin/cjk-sense" --work "$WORK/site" "$@"
