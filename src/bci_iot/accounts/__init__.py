"""Account authentication and profile persistence."""

from __future__ import annotations

from bci_iot.accounts.access_db import AccessDatabase, AccessEvent
from bci_iot.accounts.gender import (
    GENDER_LABELS_IT,
    display_name,
    hello_line,
    normalize_gender,
    welcome_back,
    welcome_new,
)
from bci_iot.accounts.security import hash_password, verify_password
from bci_iot.accounts.store import ProfileStore, UserProfile

__all__ = [
    "AccessDatabase",
    "AccessEvent",
    "GENDER_LABELS_IT",
    "ProfileStore",
    "UserProfile",
    "display_name",
    "hash_password",
    "hello_line",
    "normalize_gender",
    "verify_password",
    "welcome_back",
    "welcome_new",
]
