"""Aggiorna src/bci_iot/web/static/mobile/build-manifest.json con SHA-256 APK/IPA."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "src" / "bci_iot" / "web" / "static" / "mobile" / "build-manifest.json"


def sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest(), path.stat().st_size


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apk", type=Path, default=None)
    parser.add_argument("--ipa", type=Path, default=None)
    parser.add_argument("--apk-run", default="")
    parser.add_argument("--ipa-run", default="")
    args = parser.parse_args()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data: dict = {
        "updated_at": now,
        "official_hosts": ["iris-nous.onrender.com"],
        "note_it": (
            "Confronta lo SHA-256 solo da questo sito. "
            "Un hash diverso significa che il file non e la build ufficiale Iris."
        ),
        "android": {
            "filename": "IrisNous.apk",
            "sha256": "",
            "size_bytes": 0,
            "package_id": "com.irisnous.mobile",
            "built_at": "",
            "run_id": "",
        },
        "ios": {
            "filename": "IrisNous-unsigned.ipa",
            "sha256": "",
            "size_bytes": 0,
            "built_at": "",
            "run_id": "",
        },
    }
    if MANIFEST.is_file():
        try:
            old = json.loads(MANIFEST.read_text(encoding="utf-8"))
            for key in ("android", "ios"):
                if isinstance(old.get(key), dict):
                    data[key].update({k: old[key].get(k, data[key].get(k)) for k in data[key]})
        except Exception:
            pass

    if args.apk and args.apk.is_file():
        digest, size = sha256_file(args.apk)
        data["android"].update(
            sha256=digest, size_bytes=size, built_at=now, run_id=args.apk_run or data["android"].get("run_id", "")
        )
        print(f"MANIFEST_APK {digest} {size}")
    if args.ipa and args.ipa.is_file():
        digest, size = sha256_file(args.ipa)
        data["ios"].update(
            sha256=digest, size_bytes=size, built_at=now, run_id=args.ipa_run or data["ios"].get("run_id", "")
        )
        print(f"MANIFEST_IPA {digest} {size}")

    data["updated_at"] = now
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(data, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(f"MANIFEST_OK {MANIFEST}")


if __name__ == "__main__":
    main()
