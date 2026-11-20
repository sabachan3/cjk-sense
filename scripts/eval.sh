#!/usr/bin/env bash
# Browser eval: pages with a known answer, checked end to end in a real browser.
# macOS: scripts/eval.sh            Windows: scripts/eval.sh --channel msedge
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
uv run --quiet --no-project --with-requirements requirements-browser.txt python evals/eval_fixtures.py "$@"
