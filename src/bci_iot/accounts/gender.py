"""Italian gender-aware copy for the private area."""

from __future__ import annotations

from typing import Literal

Gender = Literal["female", "male", "non_binary"]

ALLOWED_GENDERS: frozenset[str] = frozenset({"female", "male", "non_binary"})

GENDER_LABELS_IT: dict[str, str] = {
    "female": "Donna",
    "male": "Uomo",
    "non_binary": "Non binario",
}


def normalize_gender(value: str) -> Gender:
    key = (value or "").strip().lower()
    aliases = {
        "f": "female",
        "femmina": "female",
        "donna": "female",
        "female": "female",
        "m": "male",
        "maschio": "male",
        "uomo": "male",
        "male": "male",
        "nb": "non_binary",
        "non_binario": "non_binary",
        "non-binario": "non_binary",
        "non binario": "non_binary",
        "non_binary": "non_binary",
        "x": "non_binary",
    }
    mapped = aliases.get(key)
    if mapped is None:
        raise ValueError("Seleziona un’identità di genere valida.")
    return mapped  # type: ignore[return-value]


def display_name(*, first_name: str, username: str) -> str:
    name = (first_name or "").strip()
    return name if name else username


def welcome_back(*, first_name: str, username: str, gender: str) -> str:
    """Login flash after credentials are accepted."""

    name = display_name(first_name=first_name, username=username)
    if gender == "female":
        return f"Bentornata, {name}."
    if gender == "male":
        return f"Bentornato, {name}."
    if gender == "non_binary":
        return f"Bentornatə, {name}."
    return f"Ciao, {name}."


def welcome_new(*, first_name: str, username: str, gender: str) -> str:
    name = display_name(first_name=first_name, username=username)
    if gender == "female":
        return f"Benvenuta, {name}. Ora puoi configurare la cuffia."
    if gender == "male":
        return f"Benvenuto, {name}. Ora puoi configurare la cuffia."
    if gender == "non_binary":
        return f"Benvenutə, {name}. Ora puoi configurare la cuffia."
    return f"Ciao, {name}. Ora puoi configurare la cuffia."


def hello_line(*, first_name: str, username: str, gender: str) -> str:
    """Short heading for the private area."""

    name = display_name(first_name=first_name, username=username)
    if gender == "female":
        return f"Ciao, {name}"
    if gender == "male":
        return f"Ciao, {name}"
    if gender == "non_binary":
        return f"Ciao, {name}"
    return f"Ciao, {username}"


def saved_config(*, gender: str) -> str:
    if gender == "female":
        return "Configurazione salvata."
    if gender == "male":
        return "Configurazione salvata."
    # Already gender-neutral in Italian; keep consistent flash.
    return "Configurazione salvata."
