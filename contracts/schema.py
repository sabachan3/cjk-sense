"""Shapes passed between services. Every boundary validates with these; see README.md here."""

from __future__ import annotations

RULES = ("lang-missing", "lang-mismatch", "wrong-language", "han-font", "page-error")
SEVERITIES = ("fail", "warn")
REPORT_VERSION = 1


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_snapshot(snapshot: dict) -> dict:
    """A page snapshot: either an error, or text plus the groups of Han text by font list and lang."""
    _require(isinstance(snapshot, dict) and isinstance(snapshot.get("url"), str), "snapshot needs a url")
    if "error" in snapshot:
        _require(isinstance(snapshot["error"], str), "snapshot error must be text")
        return snapshot
    _require(isinstance(snapshot.get("text"), str), "snapshot needs text")
    _require(snapshot.get("html_lang") is None or isinstance(snapshot["html_lang"], str), "html_lang must be text or null")
    _require(isinstance(snapshot.get("webfonts"), list), "snapshot needs a webfonts list")
    _require(isinstance(snapshot.get("groups"), list), "snapshot needs a groups list")
    for group in snapshot["groups"]:
        _require(isinstance(group.get("stack"), str), "group needs a font stack")
        _require(isinstance(group.get("lang"), str), "group needs a lang (empty when unset)")
        _require(isinstance(group.get("chars"), int) and group["chars"] >= 0, "group needs a Han character count")
        _require(isinstance(group.get("fonts", []), list), "group fonts must be a list")
    return snapshot


def validate_finding(finding: dict) -> dict:
    _require(finding.get("rule") in RULES, f"unknown rule {finding.get('rule')!r}")
    _require(finding.get("severity") in SEVERITIES, f"unknown severity {finding.get('severity')!r}")
    _require(isinstance(finding.get("message"), str) and finding["message"], "finding needs a message")
    _require(isinstance(finding.get("fix"), str), "finding needs a fix (may be empty)")
    return finding
