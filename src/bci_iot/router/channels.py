"""Context channels: sticky (music) vs ephemeral (call, message)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ChannelId(str, Enum):
    HOME = "home"
    MUSIC = "music"
    CALL = "call"
    MESSAGES = "messages"


class ChannelKind(str, Enum):
    """Lifecycle policy for a channel."""

    ALWAYS = "always"  # HOME: ambient, always available
    STICKY = "sticky"  # MUSIC: open while streaming, closes when playback stops
    EPHEMERAL = "ephemeral"  # CALL/MESSAGES: open on event, close when resolved


CHANNEL_KIND: dict[ChannelId, ChannelKind] = {
    ChannelId.HOME: ChannelKind.ALWAYS,
    ChannelId.MUSIC: ChannelKind.STICKY,
    ChannelId.CALL: ChannelKind.EPHEMERAL,
    ChannelId.MESSAGES: ChannelKind.EPHEMERAL,
}


@dataclass(slots=True)
class WorldState:
    """Observable world flags that open/close channels."""

    music_playing: bool = False
    incoming_call: bool = False
    caller_name: str = ""
    unread_message: bool = False
    message_app: str = ""
    message_from: str = ""
    home_devices: list[str] = field(
        default_factory=lambda: [
            "luce_salotto",
            "luce_cucina",
            "luce_camera",
            "tv_soggiorno",
            "presa_desk",
            "lampada_letto",
        ]
    )
    device_on: dict[str, bool] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in self.home_devices:
            self.device_on.setdefault(name, False)


class ChannelGate:
    """Compute which channels are open from the current world state."""

    def __init__(self, world: WorldState | None = None) -> None:
        self.world = world or WorldState()

    def open_channels(self) -> set[ChannelId]:
        open_set = {ChannelId.HOME}
        if self.world.music_playing:
            open_set.add(ChannelId.MUSIC)
        if self.world.incoming_call:
            open_set.add(ChannelId.CALL)
        if self.world.unread_message:
            open_set.add(ChannelId.MESSAGES)
        return open_set

    def close_call(self) -> None:
        """Ephemeral: call channel exists only while the ring is unresolved."""

        self.world.incoming_call = False
        self.world.caller_name = ""

    def close_messages(self) -> None:
        """Ephemeral: message channel closes after open or dismiss."""

        self.world.unread_message = False
        self.world.message_app = ""
        self.world.message_from = ""

    def close_music(self) -> None:
        """Sticky: music channel closes when playback stops."""

        self.world.music_playing = False

    def status(self) -> dict[str, Any]:
        opened = self.open_channels()
        return {
            "open_channels": sorted(ch.value for ch in opened),
            "channel_kinds": {
                ch.value: {
                    "kind": CHANNEL_KIND[ch].value,
                    "open": ch in opened,
                }
                for ch in ChannelId
            },
            "music_playing": self.world.music_playing,
            "incoming_call": self.world.incoming_call,
            "caller_name": self.world.caller_name,
            "unread_message": self.world.unread_message,
            "message_app": self.world.message_app,
            "message_from": self.world.message_from,
            "devices": [
                {"id": d, "on": bool(self.world.device_on.get(d, False))}
                for d in self.world.home_devices
            ],
        }
