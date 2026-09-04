"""Local SVG flags so language/phone pickers work without flagcdn (often blocked)."""

from __future__ import annotations

from pathlib import Path

W, H = 40, 30


def flag_url(iso: str) -> str:
    """Public path for a flag SVG (generated route, no disk required)."""
    return f"/flags/{_code(iso)}.svg"


def _code(iso: str) -> str:
    raw = (iso or "").strip().lower()
    if raw in {"uk", "gb"}:
        return "gb"
    if raw in {"un", ""}:
        return "un"
    return raw or "un"


def _svg(body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}" preserveAspectRatio="xMidYMid slice">{body}</svg>'
    )


def _rect(x: float, y: float, w: float, h: float, fill: str) -> str:
    return f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" fill="{fill}"/>'


def _h(*colors: str) -> str:
    n = max(len(colors), 1)
    band = H / n
    return _svg("".join(_rect(0, i * band, W, band + 0.08, c) for i, c in enumerate(colors)))


def _v(*colors: str) -> str:
    n = max(len(colors), 1)
    band = W / n
    return _svg("".join(_rect(i * band, 0, band + 0.08, H, c) for i, c in enumerate(colors)))


def _hw(pairs: list[tuple[str, float]]) -> str:
    total = sum(weight for _, weight in pairs) or 1.0
    y = 0.0
    parts: list[str] = []
    for color, weight in pairs:
        h = H * (weight / total)
        parts.append(_rect(0, y, W, h + 0.08, color))
        y += h
    return _svg("".join(parts))


def _vw(pairs: list[tuple[str, float]]) -> str:
    total = sum(weight for _, weight in pairs) or 1.0
    x = 0.0
    parts: list[str] = []
    for color, weight in pairs:
        w = W * (weight / total)
        parts.append(_rect(x, 0, w + 0.08, H, color))
        x += w
    return _svg("".join(parts))


def _cross(*, bg: str, cross: str, fimbriation: str | None = None, offset: float = 0.32) -> str:
    cx = W * offset
    cy = H / 2
    outer = 7.2 if fimbriation else 4.6
    parts = [_rect(0, 0, W, H, bg)]
    if fimbriation:
        parts.append(_rect(cx - outer, 0, outer * 2, H, fimbriation))
        parts.append(_rect(0, cy - outer, W, outer * 2, fimbriation))
        inner = 3.2
        parts.append(_rect(cx - inner, 0, inner * 2, H, cross))
        parts.append(_rect(0, cy - inner, W, inner * 2, cross))
    else:
        parts.append(_rect(cx - outer / 2, 0, outer, H, cross))
        parts.append(_rect(0, cy - outer / 2, W, outer, cross))
    return _svg("".join(parts))


def _circle(cx: float, cy: float, r: float, fill: str) -> str:
    return f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="{fill}"/>'


def _poly(points: str, fill: str) -> str:
    return f'<polygon points="{points}" fill="{fill}"/>'


def _star(cx: float, cy: float, r: float, fill: str) -> str:
    return (
        f'<polygon points="{cx:.1f},{cy - r:.1f} {cx + r * 0.7:.1f},{cy:.1f} '
        f'{cx:.1f},{cy + r:.1f} {cx - r * 0.7:.1f},{cy:.1f}" fill="{fill}"/>'
    )


def _letter(iso: str, bg: str, fg: str = "#fff") -> str:
    label = _code(iso).upper()[:3]
    return _svg(
        _rect(0, 0, W, H, bg)
        + f'<text x="20" y="20" text-anchor="middle" fill="{fg}" '
        f'font-size="11" font-family="Segoe UI, Arial, sans-serif" font-weight="700">{label}</text>'
    )


def _jack() -> str:
    return _svg(
        _rect(0, 0, W, H, "#012169")
        + '<path d="M0 0 L40 30 M40 0 L0 30" stroke="#fff" stroke-width="6"/>'
        + '<path d="M0 0 L40 30 M40 0 L0 30" stroke="#c8102e" stroke-width="2.4"/>'
        + '<path d="M20 0 V30 M0 15 H40" stroke="#fff" stroke-width="10"/>'
        + '<path d="M20 0 V30 M0 15 H40" stroke="#c8102e" stroke-width="6"/>'
    )


def _usa() -> str:
    parts = [_rect(0, 0, W, H, "#bf0a30")]
    stripe = H / 13
    for i in range(13):
        if i % 2 == 1:
            parts.append(_rect(0, i * stripe, W, stripe + 0.05, "#fff"))
    parts.append(_rect(0, 0, 16, stripe * 7, "#002868"))
    return _svg("".join(parts))


def _japan() -> str:
    return _svg(_rect(0, 0, W, H, "#fff") + _circle(20, 15, 7.2, "#bc002d"))


def _swiss() -> str:
    return _svg(
        _rect(0, 0, W, H, "#da291c")
        + _rect(16.4, 6.2, 7.2, 17.6, "#fff")
        + _rect(11.2, 11.4, 17.6, 7.2, "#fff")
    )


def _china() -> str:
    parts = [_rect(0, 0, W, H, "#de2910"), _star(8, 8, 4.2, "#ffde00")]
    for cx, cy in ((16, 4.5), (19, 8), (19, 12.5), (16, 16)):
        parts.append(_star(cx, cy, 1.6, "#ffde00"))
    return _svg("".join(parts))


def _un() -> str:
    return _svg(
        _rect(0, 0, W, H, "#5b92e5")
        + '<circle cx="20" cy="15" r="8" fill="none" stroke="#fff" stroke-width="1.4"/>'
        + '<path d="M12 15 H28 M20 7 V23 M14 10 Q20 18 26 10 M14 20 Q20 12 26 20" '
        'fill="none" stroke="#fff" stroke-width="1"/>'
    )


def _greece() -> str:
    parts = []
    band = H / 9
    for i in range(9):
        parts.append(_rect(0, i * band, W, band + 0.05, "#0d5eaf" if i % 2 == 0 else "#fff"))
    parts.append(_rect(0, 0, 13.3, band * 5, "#0d5eaf"))
    parts.append(_rect(5.3, 0, 2.7, band * 5, "#fff"))
    parts.append(_rect(0, band * 2.5 - 1.35, 13.3, 2.7, "#fff"))
    return _svg("".join(parts))


def _south_africa() -> str:
    return _svg(
        _rect(0, 0, W, H, "#007a4d")
        + _rect(0, 0, W, 10, "#de3831")
        + _rect(0, 20, W, 10, "#002395")
        + _poly("0,0 14,15 0,30", "#000")
        + _poly("0,4 10,15 0,26", "#ffb612")
        + _poly("0,8 7,15 0,22", "#000")
    )


def _brazil() -> str:
    return _svg(
        _rect(0, 0, W, H, "#009b3a")
        + _poly("20,3 37,15 20,27 3,15", "#fedd00")
        + _circle(20, 15, 6, "#002776")
    )


def _czechia() -> str:
    return _svg(
        _rect(0, 0, W, H / 2, "#fff")
        + _rect(0, H / 2, W, H / 2, "#d7141a")
        + _poly("0,0 16,15 0,30", "#11457e")
    )


def _turkey() -> str:
    return _svg(
        _rect(0, 0, W, H, "#e30a17")
        + _circle(16, 15, 7, "#fff")
        + _circle(18.2, 15, 5.5, "#e30a17")
        + _star(24.5, 15, 3.4, "#fff")
    )


def _israel() -> str:
    return _svg(
        _rect(0, 0, W, H, "#fff")
        + _rect(0, 3.5, W, 4, "#0038b8")
        + _rect(0, 22.5, W, 4, "#0038b8")
        + '<polygon points="20,9 24.5,17 15.5,17" fill="none" stroke="#0038b8" stroke-width="1.4"/>'
        + '<polygon points="20,21 24.5,13 15.5,13" fill="none" stroke="#0038b8" stroke-width="1.4"/>'
    )


def _korea() -> str:
    return _svg(
        _rect(0, 0, W, H, "#fff")
        + _circle(20, 13.5, 7, "#cd2e3a")
        + _circle(20, 16.5, 7, "#0047a0")
        + _circle(20, 15, 3.2, "#fff")
    )


def _uae() -> str:
    return _svg(
        _rect(10, 0, 30, 10, "#00732f")
        + _rect(10, 10, 30, 10, "#fff")
        + _rect(10, 20, 30, 10, "#000")
        + _rect(0, 0, 10, 30, "#ff0000")
    )


_RECIPES: dict[str, str] = {
    "un": _un(),
    "it": _v("#009246", "#fff", "#ce2b37"),
    "en": _jack(),
    "gb": _jack(),
    "fr": _v("#002395", "#fff", "#ed2939"),
    "de": _h("#000", "#dd0000", "#ffce00"),
    "pt": _vw([("#006600", 2), ("#ff0000", 3)]),
    "zh": _china(),
    "cn": _china(),
    "ja": _japan(),
    "jp": _japan(),
    "ie": _v("#169b62", "#fff", "#ff883e"),
    "be": _v("#000", "#fade4b", "#ed2939"),
    "nl": _h("#ae1c28", "#fff", "#21468b"),
    "lu": _h("#ed2939", "#fff", "#00a1de"),
    "at": _h("#ed2939", "#fff", "#ed2939"),
    "ch": _swiss(),
    "es": _hw([("#aa151b", 1), ("#f1bf00", 2), ("#aa151b", 1)]),
    "pl": _h("#fff", "#dc143c"),
    "cz": _czechia(),
    "sk": _h("#fff", "#0b4ea2", "#ee1c25"),
    "hu": _h("#ce2939", "#fff", "#477050"),
    "ro": _v("#002b7f", "#fcd116", "#ce1126"),
    "bg": _h("#fff", "#00966e", "#d62612"),
    "gr": _greece(),
    "hr": _h("#ff0000", "#fff", "#171796"),
    "si": _h("#fff", "#0000ff", "#ff0000"),
    "rs": _h("#c6363c", "#0c4076", "#fff"),
    "ba": _svg(_rect(0, 0, W, H, "#002395") + _poly("6,0 26,0 26,30", "#fecb00")),
    "al": _svg(_rect(0, 0, W, H, "#e41e20") + _star(20, 15, 8, "#000")),
    "mk": _svg(_rect(0, 0, W, H, "#d82126") + _circle(20, 15, 5, "#f8e205")),
    "me": _svg(_rect(0, 0, W, H, "#c40308") + _rect(3, 3, 34, 24, "#d4af37")),
    "xk": _svg(
        _rect(0, 0, W, H, "#244aa5")
        + _star(20, 18, 4, "#d0a650")
        + _star(12, 10, 2, "#d0a650")
        + _star(28, 10, 2, "#d0a650")
        + _star(16, 8, 2, "#d0a650")
        + _star(24, 8, 2, "#d0a650")
    ),
    "mt": _v("#fff", "#cf142b"),
    "cy": _svg(_rect(0, 0, W, H, "#fff") + _poly("8,18 20,10 32,18 20,22", "#d57800")),
    "sm": _h("#fff", "#5eb6e4"),
    "va": _v("#ffe000", "#fff"),
    "se": _cross(bg="#006aa7", cross="#fecc00"),
    "no": _cross(bg="#ba0c2f", cross="#00205b", fimbriation="#fff"),
    "dk": _cross(bg="#c8102e", cross="#fff"),
    "fi": _cross(bg="#fff", cross="#003580"),
    "is": _cross(bg="#02529c", cross="#dc1e35", fimbriation="#fff"),
    "ee": _h("#0072ce", "#000", "#fff"),
    "lv": _hw([("#9e3039", 2), ("#fff", 1), ("#9e3039", 2)]),
    "lt": _h("#fdb913", "#006a44", "#c1272d"),
    "ua": _h("#005bbb", "#ffd500"),
    "md": _v("#0046ae", "#ffd200", "#cc092f"),
    "by": _hw([("#c8313e", 2), ("#4aa657", 1)]),
    "ru": _h("#fff", "#0039a6", "#d52b1e"),
    "tr": _turkey(),
    "us": _usa(),
    "ca": _vw([("#ff0000", 1), ("#fff", 2), ("#ff0000", 1)]),
    "mx": _v("#006847", "#fff", "#ce1126"),
    "br": _brazil(),
    "ar": _h("#74acdf", "#fff", "#74acdf"),
    "cl": _svg(
        _rect(0, 10, W, 20, "#d52b1e")
        + _rect(0, 0, W, 10, "#fff")
        + _rect(0, 0, 12, 10, "#0039a6")
        + _star(6, 5, 3, "#fff")
    ),
    "co": _hw([("#fcd116", 2), ("#003893", 1), ("#ce1126", 1)]),
    "pe": _v("#d91023", "#fff", "#d91023"),
    "ve": _h("#ffcc00", "#00247d", "#cf142b"),
    "uy": _svg(
        _rect(0, 0, W, H, "#fff")
        + "".join(_rect(0, i * (H / 9), W, H / 9, "#0038a8") for i in range(1, 9, 2))
        + _rect(0, 0, 14, 14, "#fff")
        + _circle(7, 7, 4, "#fcd116")
    ),
    "au": _svg(
        _rect(0, 0, W, H, "#012169")
        + _rect(0, 0, 18, 15, "#012169")
        + '<path d="M9 0 V15 M0 7.5 H18" stroke="#fff" stroke-width="3"/>'
        + '<path d="M9 0 V15 M0 7.5 H18" stroke="#c8102e" stroke-width="1.6"/>'
        + _star(28, 10, 2.2, "#fff")
        + _star(33, 18, 1.8, "#fff")
    ),
    "nz": _svg(
        _rect(0, 0, W, H, "#012169")
        + '<path d="M9 0 V15 M0 7.5 H18" stroke="#fff" stroke-width="3"/>'
        + '<path d="M9 0 V15 M0 7.5 H18" stroke="#c8102e" stroke-width="1.6"/>'
        + _star(28, 8, 2.4, "#c8102e")
        + _star(32, 14, 2, "#c8102e")
        + _star(26, 16, 1.6, "#c8102e")
        + _star(30, 22, 2.2, "#c8102e")
    ),
    "kr": _korea(),
    "hk": _svg(_rect(0, 0, W, H, "#de2910") + _star(20, 15, 7, "#fff")),
    "tw": _svg(
        _rect(0, 0, W, H, "#fe0000")
        + _rect(0, 0, 18, 16, "#000095")
        + _star(9, 8, 4, "#fff")
    ),
    "in": _h("#ff9933", "#fff", "#138808"),
    "pk": _svg(
        _rect(0, 0, 8, H, "#fff")
        + _rect(8, 0, 32, H, "#01411c")
        + _circle(24, 15, 7, "#fff")
        + _circle(26.5, 14, 5.6, "#01411c")
        + _star(30, 12, 2.4, "#fff")
    ),
    "bd": _svg(_rect(0, 0, W, H, "#006a4e") + _circle(17, 15, 8, "#f42a41")),
    "id": _h("#ff0000", "#fff"),
    "my": _svg(
        "".join(
            _rect(0, i * (H / 14), W, H / 14 + 0.05, "#cc0001" if i % 2 == 0 else "#fff")
            for i in range(14)
        )
        + _rect(0, 0, 18, 15, "#010066")
    ),
    "sg": _svg(
        _rect(0, 0, W, H / 2, "#ef3340")
        + _rect(0, H / 2, W, H / 2, "#fff")
        + _circle(10, 8, 5, "#fff")
    ),
    "th": _hw([("#a51931", 1), ("#fff", 1), ("#2d2a4a", 2), ("#fff", 1), ("#a51931", 1)]),
    "vn": _svg(_rect(0, 0, W, H, "#da251d") + _star(20, 15, 8, "#ff0")),
    "ph": _svg(
        _rect(0, 0, W, H / 2, "#0038a8")
        + _rect(0, H / 2, W, H / 2, "#ce1126")
        + _poly("0,0 16,15 0,30", "#fff")
        + _star(6, 15, 3, "#fcd116")
    ),
    "ae": _uae(),
    "sa": _svg(_rect(0, 0, W, H, "#006c35")),
    "il": _israel(),
    "eg": _h("#ce1126", "#fff", "#000"),
    "ma": _svg(_rect(0, 0, W, H, "#c1272d") + _star(20, 15, 6, "#006233")),
    "tn": _svg(
        _rect(0, 0, W, H, "#e70013")
        + _circle(20, 15, 8, "#fff")
        + _circle(20, 15, 6, "#e70013")
        + _circle(18.5, 15, 4.4, "#fff")
    ),
    "dz": _svg(
        _rect(0, 0, W / 2, H, "#006233")
        + _rect(W / 2, 0, W / 2, H, "#fff")
        + _circle(20, 15, 6, "#d21034")
    ),
    "za": _south_africa(),
    "ng": _v("#008751", "#fff", "#008751"),
    "ke": _hw([("#000", 2), ("#fff", 0.4), ("#bb0000", 2), ("#fff", 0.4), ("#006600", 2)]),
    "gh": _h("#ce1126", "#fcd116", "#006b3f"),
}


def render_flag_svg(iso: str) -> str:
    """Return a compact SVG for an ISO 3166-1 alpha-2 code (or 'un')."""
    code = _code(iso)
    svg = _RECIPES.get(code)
    if svg:
        return svg
    palette = ("#1a7a5c", "#0d5eaf", "#c8102e", "#f4c430", "#2d2a4a", "#006233")
    bg = palette[sum(ord(ch) for ch in code) % len(palette)]
    return _letter(code, bg)


def ensure_flag_svgs(static_dir: Path | str) -> Path:
    """Write SVG files under ``static/flags`` (idempotent)."""
    dest = Path(static_dir) / "flags"
    dest.mkdir(parents=True, exist_ok=True)
    codes = {"un", "gb", *_RECIPES.keys()}
    try:
        from bci_iot.accounts.phone_countries import PHONE_COUNTRIES
        from bci_iot.web.i18n import LANGUAGES

        codes.update(_code(item.iso) for item in PHONE_COUNTRIES)
        codes.update(_code(lang.flag_iso) for lang in LANGUAGES)
        codes.update(_code(lang.code) for lang in LANGUAGES)
    except Exception:
        pass
    for code in sorted(codes):
        path = dest / f"{code}.svg"
        svg = render_flag_svg(code)
        if not path.exists() or path.read_text(encoding="utf-8") != svg:
            path.write_text(svg, encoding="utf-8")
    gb = dest / "gb.svg"
    uk = dest / "uk.svg"
    if gb.exists():
        text = gb.read_text(encoding="utf-8")
        if not uk.exists() or uk.read_text(encoding="utf-8") != text:
            uk.write_text(text, encoding="utf-8")
    return dest
