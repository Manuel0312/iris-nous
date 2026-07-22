"""Optional real MoABB dataset loader (heavy; not required for CI)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class MoabbStatus:
    available: bool
    detail: str
    dataset_hint: str = "Pressel2016 (imagined speech) — see MOABB docs"


def moabb_status() -> MoabbStatus:
    """Check whether the optional MoABB stack is importable."""

    try:
        import moabb  # noqa: F401
    except ImportError:
        return MoabbStatus(
            available=False,
            detail=(
                "Pacchetto moabb non installato. "
                'Installa con: pip install -e ".[experiments]" '
                "(download dataset al primo uso; può richiedere tempo/spazio)."
            ),
        )
    return MoabbStatus(
        available=True,
        detail=(
            f"moabb importabile. Il loader epoch completo è intenzionalmente "
            f"manuale: scaricare i dati pubblici e adattare "
            f"``load_moabb_feature_bundle`` al protocollo della tesi."
        ),
    )


def load_moabb_feature_bundle(**_kwargs: Any) -> None:
    """Placeholder for a future real-MoABB path.

    Raises
    ------
    NotImplementedError
        Always, until a concrete dataset + montage mapping is chosen for the
        thesis chapter. Use ``run_surrogate_experiment`` for the reproducible
        baseline already wired into the Voilà pipeline.
    """

    status = moabb_status()
    if not status.available:
        raise ImportError(status.detail)
    raise NotImplementedError(
        "Loader MoABB reale non ancora collegato: scegli il dataset (es. "
        "Pressel2016), mappa i canali al BandPowerExtractor e sostituisci "
        "questo stub. Nel frattempo usa --mode surrogate."
    )
