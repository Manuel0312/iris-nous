"""Macro-folders UX: 4 colored sections → apps inside → short confirm.

Product idea for Voilà: the user does not learn hundreds of words. They learn
four mental colours / folder images. Inside a folder, a short confirm picks
the app (dry-run until OS bridges exist).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FolderId(str, Enum):
    VIDEO = "video"  # rosso
    CHAT = "chat"  # verde
    SOCIAL = "social"  # blu
    CASA = "casa"  # giallo


FOLDER_META: dict[FolderId, dict[str, str]] = {
    FolderId.VIDEO: {
        "label": "Video",
        "color": "#c62828",
        "color_name": "rosso",
        "cue": "Pensa al rosso / cartella video",
    },
    FolderId.CHAT: {
        "label": "Chat",
        "color": "#2e7d32",
        "color_name": "verde",
        "cue": "Pensa al verde / cartella chat",
    },
    FolderId.SOCIAL: {
        "label": "Social",
        "color": "#1565c0",
        "color_name": "blu",
        "cue": "Pensa al blu / cartella social",
    },
    FolderId.CASA: {
        "label": "Casa",
        "color": "#f9a825",
        "color_name": "giallo",
        "cue": "Pensa al giallo / cartella casa",
    },
}


FOLDER_APPS: dict[FolderId, list[dict[str, str]]] = {
    FolderId.VIDEO: [
        {"id": "youtube", "name": "YouTube"},
        {"id": "twitch", "name": "Twitch"},
        {"id": "netflix", "name": "Netflix"},
    ],
    FolderId.CHAT: [
        {"id": "whatsapp", "name": "WhatsApp"},
        {"id": "facebook", "name": "Facebook"},
        {"id": "messages", "name": "Messaggi"},
    ],
    FolderId.SOCIAL: [
        {"id": "tiktok", "name": "TikTok"},
        {"id": "instagram", "name": "Instagram"},
        {"id": "telegram", "name": "Telegram"},
    ],
    FolderId.CASA: [
        {"id": "luci", "name": "Luci"},
        {"id": "spotify", "name": "Spotify"},
        {"id": "tv", "name": "TV"},
    ],
}


class FolderPhase(str, Enum):
    IDLE = "idle"
    FOLDER = "folder"
    CONFIRM = "confirm"


@dataclass
class MacroFolderEngine:
    """Two-level navigation: colour folder → app → SÌ/NO."""

    phase: FolderPhase = FolderPhase.IDLE
    active_folder: FolderId | None = None
    cursor: int = 0
    pending_app_id: str | None = None
    last_opened: str | None = None
    message: str = "Pensa un colore (rosso / verde / blu / giallo)."
    log: list[dict[str, Any]] = field(default_factory=list)

    def status(self) -> dict[str, Any]:
        apps = []
        if self.active_folder is not None:
            apps = FOLDER_APPS[self.active_folder]
        return {
            "phase": self.phase.value,
            "active_folder": self.active_folder.value if self.active_folder else None,
            "folder_meta": (
                FOLDER_META[self.active_folder] if self.active_folder else None
            ),
            "apps": apps,
            "cursor": self.cursor,
            "pending_app_id": self.pending_app_id,
            "pending_app_name": self._pending_name(),
            "last_opened": self.last_opened,
            "message": self.message,
            "folders": [
                {
                    "id": fid.value,
                    **FOLDER_META[fid],
                    "apps": [a["name"] for a in FOLDER_APPS[fid]],
                }
                for fid in FolderId
            ],
            "log": list(self.log[-12:]),
        }

    def _pending_name(self) -> str | None:
        if self.active_folder is None or not self.pending_app_id:
            return None
        for app in FOLDER_APPS[self.active_folder]:
            if app["id"] == self.pending_app_id:
                return app["name"]
        return None

    def _push(self, event: str, **extra: Any) -> None:
        self.log.append({"event": event, **extra})

    def open_folder(self, folder: str | FolderId) -> dict[str, Any]:
        fid = FolderId(folder) if not isinstance(folder, FolderId) else folder
        self.active_folder = fid
        self.phase = FolderPhase.FOLDER
        self.cursor = 0
        self.pending_app_id = None
        meta = FOLDER_META[fid]
        self.message = (
            f"Cartella {meta['label']} ({meta['color_name']}) aperta. "
            f"Scegli un’app con AVANTI / indietro, poi APRI."
        )
        self._push("folder_open", folder=fid.value)
        return self.status()

    def next_app(self) -> dict[str, Any]:
        if self.active_folder is None or self.phase == FolderPhase.IDLE:
            self.message = "Prima apri una cartella colore."
            return self.status()
        apps = FOLDER_APPS[self.active_folder]
        self.cursor = (self.cursor + 1) % len(apps)
        self.phase = FolderPhase.FOLDER
        self.pending_app_id = None
        self.message = f"Evidenziata: {apps[self.cursor]['name']}"
        self._push("cursor", app=apps[self.cursor]["id"])
        return self.status()

    def prev_app(self) -> dict[str, Any]:
        if self.active_folder is None or self.phase == FolderPhase.IDLE:
            self.message = "Prima apri una cartella colore."
            return self.status()
        apps = FOLDER_APPS[self.active_folder]
        self.cursor = (self.cursor - 1) % len(apps)
        self.phase = FolderPhase.FOLDER
        self.pending_app_id = None
        self.message = f"Evidenziata: {apps[self.cursor]['name']}"
        return self.status()

    def ask_open(self) -> dict[str, Any]:
        if self.active_folder is None:
            self.message = "Prima apri una cartella colore."
            return self.status()
        apps = FOLDER_APPS[self.active_folder]
        app = apps[self.cursor]
        self.pending_app_id = app["id"]
        self.phase = FolderPhase.CONFIRM
        self.message = f"Aprire {app['name']}? SÌ / NO"
        self._push("confirm", app=app["id"])
        return self.status()

    def confirm_yes(self) -> dict[str, Any]:
        if self.phase != FolderPhase.CONFIRM or not self.pending_app_id:
            self.message = "Nessuna conferma in corso."
            return self.status()
        name = self._pending_name() or self.pending_app_id
        self.last_opened = name
        self._push("opened", app=self.pending_app_id, dry_run=True)
        self.message = f"Aperta (simulazione): {name}. Cartella chiusa."
        self.phase = FolderPhase.IDLE
        self.active_folder = None
        self.pending_app_id = None
        self.cursor = 0
        return self.status()

    def confirm_no(self) -> dict[str, Any]:
        if self.phase != FolderPhase.CONFIRM:
            self.close()
            return self.status()
        self.phase = FolderPhase.FOLDER
        self.pending_app_id = None
        self.message = "Annullato. Scegli un’altra app o chiudi."
        self._push("confirm_no")
        return self.status()

    def close(self) -> dict[str, Any]:
        self.phase = FolderPhase.IDLE
        self.active_folder = None
        self.pending_app_id = None
        self.cursor = 0
        self.message = "Pensa un colore (rosso / verde / blu / giallo)."
        self._push("close")
        return self.status()

    def fire(self, command: str) -> dict[str, Any]:
        """Map demo buttons / mental cues to engine actions."""

        cmd = command.strip().upper()
        color_map = {
            "ROSSO": FolderId.VIDEO,
            "VIDEO": FolderId.VIDEO,
            "VERDE": FolderId.CHAT,
            "CHAT": FolderId.CHAT,
            "BLU": FolderId.SOCIAL,
            "SOCIAL": FolderId.SOCIAL,
            "GIALLO": FolderId.CASA,
            "CASA": FolderId.CASA,
        }
        if cmd in color_map:
            return self.open_folder(color_map[cmd])
        if cmd in {"NEXT", "AVANTI"}:
            return self.next_app()
        if cmd in {"PREV", "INDIETRO"}:
            return self.prev_app()
        if cmd in {"APRI", "OPEN"}:
            return self.ask_open()
        if cmd in {"SI", "SÌ", "YES"}:
            return self.confirm_yes()
        if cmd in {"NO"}:
            return self.confirm_no()
        if cmd in {"CHIUDI", "CLOSE", "ESC"}:
            return self.close()
        raise KeyError(f"Unknown command: {command}")


def list_folder_commands() -> list[str]:
    return [
        "ROSSO",
        "VERDE",
        "BLU",
        "GIALLO",
        "NEXT",
        "PREV",
        "APRI",
        "SI",
        "NO",
        "CHIUDI",
    ]
