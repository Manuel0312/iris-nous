"""Per-user calibration: fit a personal sklearn head and save it."""

from __future__ import annotations

from pathlib import Path

from bci_iot.accounts.names import safe_username
from bci_iot.ml.sklearn_classifier import SklearnIntentClassifier
from bci_iot.ml.train import train_default_classifier


def calibrate_user_model(
    username: str,
    *,
    models_dir: Path | str = "models/users",
    n_samples: int = 300,
    seed: int = 42,
) -> tuple[Path, float]:
    """Train a user-specific classifier (synthetic labels until headset exists).

    Returns:
        Path to the saved model and cross-validated accuracy.
    """

    out = Path(models_dir) / f"{safe_username(username)}.joblib"
    _, accuracy = train_default_classifier(
        n_samples=n_samples,
        seed=seed,
        model_path=out,
    )
    # Ensure loadable
    loaded = SklearnIntentClassifier.load(out)
    if not loaded.is_fitted:
        raise RuntimeError("Calibration produced an unfitted model")
    return out, accuracy
