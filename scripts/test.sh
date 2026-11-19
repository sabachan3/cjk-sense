#!/usr/bin/env bash
# Gate tests: deterministic, local, no network, no browser. Also the pre-commit hook.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
uv run --quiet --no-project --with pytest pytest -q services/detect/tests services/fonts/tests services/snapshot/tests services/check/tests tests
