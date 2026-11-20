#!/usr/bin/env bash
# One-time (and repeatable) setup of a clone: hook, browser, then the gate as proof it works.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
command -v uv >/dev/null 2>&1 || { echo "uv is required: https://docs.astral.sh/uv/" >&2; exit 2; }
git config core.hooksPath .githooks
# Dependencies are resolved per command by `uv run --with`, so there is no environment to sync.
# `playwright install` does nothing when the browser is already there.
uv run --quiet --no-project --with-requirements requirements-browser.txt playwright install chromium-headless-shell
scripts/test.sh
echo "setup done: pre-commit hook active, browser installed, gate green"
