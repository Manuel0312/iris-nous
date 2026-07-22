"""International dialing prefixes with flag emoji and national-length ranges."""

from __future__ import annotations

from dataclasses import dataclass

from bci_iot.accounts.validators import digits_only, is_digits


@dataclass(frozen=True, slots=True)
class PhoneCountry:
    iso: str
    name: str
    dial: str  # e.g. "+39"
    flag: str
    min_len: int
    max_len: int


# Curated world list (ISO, Italian name, E.164 dial, flag, national digit range).
PHONE_COUNTRIES: tuple[PhoneCountry, ...] = (
    PhoneCountry("IT", "Italia", "+39", "🇮🇹", 9, 10),
    PhoneCountry("SM", "San Marino", "+378", "🇸🇲", 6, 10),
    PhoneCountry("VA", "Città del Vaticano", "+379", "🇻🇦", 6, 10),
    PhoneCountry("CH", "Svizzera", "+41", "🇨🇭", 9, 9),
    PhoneCountry("FR", "Francia", "+33", "🇫🇷", 9, 9),
    PhoneCountry("DE", "Germania", "+49", "🇩🇪", 6, 13),
    PhoneCountry("AT", "Austria", "+43", "🇦🇹", 7, 13),
    PhoneCountry("ES", "Spagna", "+34", "🇪🇸", 9, 9),
    PhoneCountry("PT", "Portogallo", "+351", "🇵🇹", 9, 9),
    PhoneCountry("GB", "Regno Unito", "+44", "🇬🇧", 10, 10),
    PhoneCountry("IE", "Irlanda", "+353", "🇮🇪", 7, 9),
    PhoneCountry("BE", "Belgio", "+32", "🇧🇪", 8, 9),
    PhoneCountry("NL", "Paesi Bassi", "+31", "🇳🇱", 9, 9),
    PhoneCountry("LU", "Lussemburgo", "+352", "🇱🇺", 8, 9),
    PhoneCountry("PL", "Polonia", "+48", "🇵🇱", 9, 9),
    PhoneCountry("CZ", "Cechia", "+420", "🇨🇿", 9, 9),
    PhoneCountry("SK", "Slovacchia", "+421", "🇸🇰", 9, 9),
    PhoneCountry("HU", "Ungheria", "+36", "🇭🇺", 8, 9),
    PhoneCountry("RO", "Romania", "+40", "🇷🇴", 9, 9),
    PhoneCountry("BG", "Bulgaria", "+359", "🇧🇬", 8, 9),
    PhoneCountry("GR", "Grecia", "+30", "🇬🇷", 10, 10),
    PhoneCountry("HR", "Croazia", "+385", "🇭🇷", 8, 9),
    PhoneCountry("SI", "Slovenia", "+386", "🇸🇮", 8, 8),
    PhoneCountry("RS", "Serbia", "+381", "🇷🇸", 8, 9),
    PhoneCountry("BA", "Bosnia ed Erzegovina", "+387", "🇧🇦", 8, 8),
    PhoneCountry("AL", "Albania", "+355", "🇦🇱", 8, 9),
    PhoneCountry("MK", "Macedonia del Nord", "+389", "🇲🇰", 8, 8),
    PhoneCountry("ME", "Montenegro", "+382", "🇲🇪", 8, 8),
    PhoneCountry("XK", "Kosovo", "+383", "🇽🇰", 8, 8),
    PhoneCountry("MT", "Malta", "+356", "🇲🇹", 8, 8),
    PhoneCountry("CY", "Cipro", "+357", "🇨🇾", 8, 8),
    PhoneCountry("SE", "Svezia", "+46", "🇸🇪", 7, 10),
    PhoneCountry("NO", "Norvegia", "+47", "🇳🇴", 8, 8),
    PhoneCountry("DK", "Danimarca", "+45", "🇩🇰", 8, 8),
    PhoneCountry("FI", "Finlandia", "+358", "🇫🇮", 6, 10),
    PhoneCountry("IS", "Islanda", "+354", "🇮🇸", 7, 7),
    PhoneCountry("EE", "Estonia", "+372", "🇪🇪", 7, 8),
    PhoneCountry("LV", "Lettonia", "+371", "🇱🇻", 8, 8),
    PhoneCountry("LT", "Lituania", "+370", "🇱🇹", 8, 8),
    PhoneCountry("UA", "Ucraina", "+380", "🇺🇦", 9, 9),
    PhoneCountry("MD", "Moldavia", "+373", "🇲🇩", 8, 8),
    PhoneCountry("BY", "Bielorussia", "+375", "🇧🇾", 9, 9),
    PhoneCountry("RU", "Russia", "+7", "🇷🇺", 10, 10),
    PhoneCountry("TR", "Turchia", "+90", "🇹🇷", 10, 10),
    PhoneCountry("US", "Stati Uniti", "+1", "🇺🇸", 10, 10),
    PhoneCountry("CA", "Canada", "+1", "🇨🇦", 10, 10),
    PhoneCountry("MX", "Messico", "+52", "🇲🇽", 10, 10),
    PhoneCountry("BR", "Brasile", "+55", "🇧🇷", 10, 11),
    PhoneCountry("AR", "Argentina", "+54", "🇦🇷", 10, 10),
    PhoneCountry("CL", "Cile", "+56", "🇨🇱", 9, 9),
    PhoneCountry("CO", "Colombia", "+57", "🇨🇴", 10, 10),
    PhoneCountry("PE", "Perù", "+51", "🇵🇪", 9, 9),
    PhoneCountry("VE", "Venezuela", "+58", "🇻🇪", 10, 10),
    PhoneCountry("UY", "Uruguay", "+598", "🇺🇾", 8, 8),
    PhoneCountry("AU", "Australia", "+61", "🇦🇺", 9, 9),
    PhoneCountry("NZ", "Nuova Zelanda", "+64", "🇳🇿", 8, 10),
    PhoneCountry("JP", "Giappone", "+81", "🇯🇵", 10, 10),
    PhoneCountry("KR", "Corea del Sud", "+82", "🇰🇷", 9, 10),
    PhoneCountry("CN", "Cina", "+86", "🇨🇳", 11, 11),
    PhoneCountry("HK", "Hong Kong", "+852", "🇭🇰", 8, 8),
    PhoneCountry("TW", "Taiwan", "+886", "🇹🇼", 9, 9),
    PhoneCountry("IN", "India", "+91", "🇮🇳", 10, 10),
    PhoneCountry("PK", "Pakistan", "+92", "🇵🇰", 10, 10),
    PhoneCountry("BD", "Bangladesh", "+880", "🇧🇩", 10, 10),
    PhoneCountry("ID", "Indonesia", "+62", "🇮🇩", 9, 12),
    PhoneCountry("MY", "Malaysia", "+60", "🇲🇾", 9, 10),
    PhoneCountry("SG", "Singapore", "+65", "🇸🇬", 8, 8),
    PhoneCountry("TH", "Thailandia", "+66", "🇹🇭", 9, 9),
    PhoneCountry("VN", "Vietnam", "+84", "🇻🇳", 9, 10),
    PhoneCountry("PH", "Filippine", "+63", "🇵🇭", 10, 10),
    PhoneCountry("AE", "Emirati Arabi Uniti", "+971", "🇦🇪", 9, 9),
    PhoneCountry("SA", "Arabia Saudita", "+966", "🇸🇦", 9, 9),
    PhoneCountry("IL", "Israele", "+972", "🇮🇱", 9, 9),
    PhoneCountry("EG", "Egitto", "+20", "🇪🇬", 10, 10),
    PhoneCountry("MA", "Marocco", "+212", "🇲🇦", 9, 9),
    PhoneCountry("TN", "Tunisia", "+216", "🇹🇳", 8, 8),
    PhoneCountry("DZ", "Algeria", "+213", "🇩🇿", 9, 9),
    PhoneCountry("ZA", "Sudafrica", "+27", "🇿🇦", 9, 9),
    PhoneCountry("NG", "Nigeria", "+234", "🇳🇬", 8, 10),
    PhoneCountry("KE", "Kenya", "+254", "🇰🇪", 9, 9),
    PhoneCountry("GH", "Ghana", "+233", "🇬🇭", 9, 9),
)


def country_by_iso(iso: str) -> PhoneCountry | None:
    key = (iso or "").strip().upper()
    for item in PHONE_COUNTRIES:
        if item.iso == key:
            return item
    return None


def country_by_dial(dial: str) -> PhoneCountry | None:
    key = (dial or "").strip()
    if not key.startswith("+"):
        key = f"+{digits_only(key)}"
    # Prefer Italy for +39; for +1 prefer US first in list order.
    for item in PHONE_COUNTRIES:
        if item.dial == key:
            return item
    return None


def normalize_phone(*, country_iso: str, national: str) -> tuple[PhoneCountry, str, str]:
    """Return (country, national_digits, e164). Raises ValueError on invalid input."""
    country = country_by_iso(country_iso)
    if country is None:
        raise ValueError("Seleziona un prefisso telefonico valido.")
    digits = digits_only(national)
    if not digits:
        raise ValueError("Inserisci il numero di telefono.")
    if not is_digits(digits):
        raise ValueError("Il numero può contenere solo cifre.")
    if len(digits) < country.min_len or len(digits) > country.max_len:
        raise ValueError(
            f"Per {country.name} ({country.dial}) il numero deve avere "
            f"da {country.min_len} a {country.max_len} cifre (senza prefisso)."
        )
    e164 = f"{country.dial}{digits}"
    return country, digits, e164


def format_phone_display(*, dial: str, national: str) -> str:
    dial = (dial or "").strip()
    national = digits_only(national)
    if dial and national:
        return f"{dial} {national}"
    return dial or national or ""
