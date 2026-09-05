"""Run thesis experiments and write JSON + Markdown reports."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bci_iot.experiments.metrics import CvResult, leave_one_subject_out, stratified_kfold
from bci_iot.experiments.moabb_loader import moabb_status
from bci_iot.experiments.surrogate import build_surrogate_bundle, intent_order


@dataclass
class ExperimentReport:
    mode: str
    created_at: str
    note: str
    moabb: dict[str, Any]
    loso: dict[str, Any]
    kfold: dict[str, Any]
    colour_mapping: dict[str, str] = field(
        default_factory=lambda: {
            "ROSSO/Video": "FOCUS (ACCENDI prior)",
            "VERDE/Chat": "ACCEPT (RISPONDI prior)",
            "BLU/Social": "REJECT (RIFIUTA prior)",
            "GIALLO/Casa": "RELAX (SPEGNI prior)",
        }
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _cv_to_dict(cv: CvResult) -> dict[str, Any]:
    return {
        "scheme": cv.scheme,
        "mean_accuracy": round(cv.mean_accuracy, 4),
        "std_accuracy": round(cv.std_accuracy, 4),
        "fold_accuracies": cv.fold_accuracies,
        "labels": cv.labels,
        "confusion": cv.confusion,
        "n_samples": cv.n_samples,
        "n_folds": cv.n_folds,
    }


def run_surrogate_experiment(
    *,
    n_subjects: int = 8,
    windows_per_class: int = 12,
    seed: int = 42,
    out_dir: Path | str | None = "results/experiments",
) -> ExperimentReport:
    """Evaluate band-power → LR on the MoABB-paradigm surrogate dataset."""

    bundle = build_surrogate_bundle(
        n_subjects=n_subjects,
        windows_per_class=windows_per_class,
        seed=seed,
    )
    order = [lab.value for lab in intent_order()]
    loso = leave_one_subject_out(
        bundle.features,
        bundle.labels,
        bundle.subjects,
        label_order=order,
    )
    kfold = stratified_kfold(
        bundle.features,
        bundle.labels,
        label_order=order,
        n_splits=5,
        seed=seed,
    )
    status = moabb_status()
    report = ExperimentReport(
        mode="surrogate",
        created_at=datetime.now(timezone.utc).isoformat(),
        note=bundle.note,
        moabb={"available": status.available, "detail": status.detail},
        loso=_cv_to_dict(loso),
        kfold=_cv_to_dict(kfold),
    )

    if out_dir is not None:
        _write_report(Path(out_dir), report)
    return report


def _write_report(out_dir: Path, report: ExperimentReport) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"surrogate_{stamp}.json"
    md_path = out_dir / f"surrogate_{stamp}.md"
    latest_json = out_dir / "latest.json"
    latest_md = out_dir / "latest.md"

    payload = report.to_dict()
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    latest_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    md = _format_markdown(report)
    md_path.write_text(md, encoding="utf-8")
    latest_md.write_text(md, encoding="utf-8")
    return json_path, md_path


def _format_markdown(report: ExperimentReport) -> str:
    loso = report.loso
    kfold = report.kfold
    lines = [
        "# Report esperimento Voilà (surrogate MoABB-paradigm)",
        "",
        f"- Creato: `{report.created_at}`",
        f"- Mode: **{report.mode}**",
        f"- Nota: {report.note}",
        "",
        "## MoABB reale",
        "",
        f"- Disponibile: `{report.moabb.get('available')}`",
        f"- Dettaglio: {report.moabb.get('detail')}",
        "",
        "## Mapping colori Voilà → intent",
        "",
    ]
    for k, v in report.colour_mapping.items():
        lines.append(f"- **{k}** → {v}")
    lines.extend(
        [
            "",
            "## Leave-one-subject-out (LOSO)",
            "",
            f"- Accuratezza media: **{loso['mean_accuracy']:.1%}** "
            f"(± {loso['std_accuracy']:.1%})",
            f"- Fold: {loso['fold_accuracies']}",
            f"- Campioni: {loso['n_samples']}",
            "",
            "## Stratified 5-fold (pooled)",
            "",
            f"- Accuratezza media: **{kfold['mean_accuracy']:.1%}** "
            f"(± {kfold['std_accuracy']:.1%})",
            f"- Fold: {kfold['fold_accuracies']}",
            "",
            "## Confusion matrix (LOSO, ordine label)",
            "",
            f"Labels: `{loso['labels']}`",
            "",
            "```",
            f"{loso['confusion']}",
            "```",
            "",
            "## Uso in tesi",
            "",
            "Cita questo report come *baseline software* sulla catena "
            "feature→classificatore. Non presentarlo come accuratezza su "
            "soggetti Pressel finché non colleghi il loader MoABB reale.",
            "",
        ]
    )
    return "\n".join(lines)
