"""End-to-end pipeline orchestration."""

from __future__ import annotations

from bci_iot.pipeline.context_demo import ContextDemoEngine
from bci_iot.pipeline.dialogue_demo import DialogueDemoEngine
from bci_iot.pipeline.factory import build_pipeline
from bci_iot.pipeline.impulse_demo import ImpulseDemoEngine
from bci_iot.pipeline.macro_folders import MacroFolderEngine
from bci_iot.pipeline.runner import PipelineRunner

__all__ = [
    "ContextDemoEngine",
    "DialogueDemoEngine",
    "ImpulseDemoEngine",
    "MacroFolderEngine",
    "PipelineRunner",
    "build_pipeline",
]
