"""Application settings loaded from environment and YAML configs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AcquisitionSettings(BaseModel):
    source: str = "synthetic"
    sample_rate_hz: float = 250.0
    n_channels: int = 8
    window_seconds: float = 1.0
    window_overlap: float = 0.5


class PreprocessingSettings(BaseModel):
    bandpass_hz: tuple[float, float] = (1.0, 40.0)
    notch_hz: float | None = 50.0
    alpha_band_hz: tuple[float, float] = (8.0, 12.0)
    beta_band_hz: tuple[float, float] = (13.0, 30.0)


class MLSettings(BaseModel):
    model_path: str = "models/baseline.joblib"
    confidence_threshold: float = 0.55


class RouterSettings(BaseModel):
    debounce_windows: int = 3
    default_context: str = "idle"


class IntegrationsSettings(BaseModel):
    dry_run: bool = True
    home_assistant_url: str = ""
    spotify_enabled: bool = False


class AccountsSettings(BaseModel):
    require_login: bool = True
    data_dir: str = "data/profiles"


class AppConfig(BaseModel):
    """Full structured config for one runtime profile."""

    acquisition: AcquisitionSettings = Field(default_factory=AcquisitionSettings)
    preprocessing: PreprocessingSettings = Field(default_factory=PreprocessingSettings)
    ml: MLSettings = Field(default_factory=MLSettings)
    router: RouterSettings = Field(default_factory=RouterSettings)
    integrations: IntegrationsSettings = Field(default_factory=IntegrationsSettings)
    accounts: AccountsSettings = Field(default_factory=AccountsSettings)


class EnvSettings(BaseSettings):
    """Environment overlays (secrets and quick toggles)."""

    model_config = SettingsConfigDict(env_prefix="BCI_IOT_", env_file=".env", extra="ignore")

    env: str = "dev"
    sample_rate_hz: float | None = None
    window_seconds: float | None = None
    window_overlap: float | None = None
    home_assistant_url: str | None = None
    home_assistant_token: str | None = None
    spotify_client_id: str | None = None
    spotify_client_secret: str | None = None
    spotify_redirect_uri: str | None = None


def load_yaml_config(path: Path | str) -> dict[str, Any]:
    """Load a YAML config file into a plain dictionary."""

    config_path = Path(path)
    with config_path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config root must be a mapping: {config_path}")
    return data


def load_app_config(path: Path | str | None = None) -> AppConfig:
    """Build :class:`AppConfig` from YAML plus optional environment overrides."""

    root = Path(__file__).resolve().parents[2]
    config_path = Path(path) if path is not None else root / "configs" / "default.yaml"
    raw = load_yaml_config(config_path)
    config = AppConfig.model_validate(raw)

    env = EnvSettings()
    acquisition = config.acquisition.model_copy(
        update={
            k: v
            for k, v in {
                "sample_rate_hz": env.sample_rate_hz,
                "window_seconds": env.window_seconds,
                "window_overlap": env.window_overlap,
            }.items()
            if v is not None
        }
    )
    integrations = config.integrations.model_copy(
        update={
            k: v
            for k, v in {"home_assistant_url": env.home_assistant_url}.items()
            if v is not None
        }
    )
    return config.model_copy(update={"acquisition": acquisition, "integrations": integrations})
