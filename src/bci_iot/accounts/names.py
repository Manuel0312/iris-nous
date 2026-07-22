"""Shared helpers for safe on-disk profile identifiers."""

from __future__ import annotations


def safe_username(username: str) -> str:
    """Normalize a username for filenames (models, etc.)."""

    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in username.strip().lower())
