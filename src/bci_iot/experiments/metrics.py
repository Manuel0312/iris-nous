"""Cross-validation metrics for thesis experiment reports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import LeaveOneGroupOut, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


@dataclass(frozen=True, slots=True)
class CvResult:
    scheme: str
    mean_accuracy: float
    std_accuracy: float
    fold_accuracies: list[float]
    labels: list[str]
    confusion: list[list[int]]
    n_samples: int
    n_folds: int


def _clf() -> Pipeline:
    return Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "clf",
                LogisticRegression(max_iter=2000, class_weight="balanced"),
            ),
        ]
    )


def leave_one_subject_out(
    features: NDArray[np.floating[Any]],
    labels: NDArray[Any],
    subjects: NDArray[np.int_],
    *,
    label_order: list[str],
) -> CvResult:
    """LOSO CV — standard in BCI papers (one subject held out)."""

    logo = LeaveOneGroupOut()
    fold_acc: list[float] = []
    y_true_all: list[Any] = []
    y_pred_all: list[Any] = []

    for train_idx, test_idx in logo.split(features, labels, subjects):
        model = _clf()
        model.fit(features[train_idx], labels[train_idx])
        pred = model.predict(features[test_idx])
        fold_acc.append(float(accuracy_score(labels[test_idx], pred)))
        y_true_all.extend(labels[test_idx].tolist())
        y_pred_all.extend(pred.tolist())

    cm = confusion_matrix(y_true_all, y_pred_all, labels=label_order)
    return CvResult(
        scheme="leave_one_subject_out",
        mean_accuracy=float(np.mean(fold_acc)),
        std_accuracy=float(np.std(fold_acc)),
        fold_accuracies=[round(a, 4) for a in fold_acc],
        labels=list(label_order),
        confusion=cm.astype(int).tolist(),
        n_samples=int(features.shape[0]),
        n_folds=len(fold_acc),
    )


def stratified_kfold(
    features: NDArray[np.floating[Any]],
    labels: NDArray[Any],
    *,
    label_order: list[str],
    n_splits: int = 5,
    seed: int = 0,
) -> CvResult:
    """Pooled stratified k-fold (optimistic vs LOSO; useful as upper bound)."""

    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    fold_acc: list[float] = []
    y_true_all: list[Any] = []
    y_pred_all: list[Any] = []

    for train_idx, test_idx in skf.split(features, labels):
        model = _clf()
        model.fit(features[train_idx], labels[train_idx])
        pred = model.predict(features[test_idx])
        fold_acc.append(float(accuracy_score(labels[test_idx], pred)))
        y_true_all.extend(labels[test_idx].tolist())
        y_pred_all.extend(pred.tolist())

    cm = confusion_matrix(y_true_all, y_pred_all, labels=label_order)
    return CvResult(
        scheme=f"stratified_{n_splits}fold",
        mean_accuracy=float(np.mean(fold_acc)),
        std_accuracy=float(np.std(fold_acc)),
        fold_accuracies=[round(a, 4) for a in fold_acc],
        labels=list(label_order),
        confusion=cm.astype(int).tolist(),
        n_samples=int(features.shape[0]),
        n_folds=len(fold_acc),
    )
