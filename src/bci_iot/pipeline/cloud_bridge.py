"""Bridge local BCI worker (PC) → Iris cloud hub.

The CLI pipeline (`bci-iot run`) and the Render FastAPI process are separate.
When the cuffia / SyntheticBoard runs on the PC, classified SÌ/NO must be POSTed
to the cloud so the phone site and companion see the same decision.

Env / CLI:
  BCI_IOT_PUBLIC_URL   e.g. https://iris-nous.onrender.com
  BCI_IOT_WORKER_TOKEN companion device token (from /api/companion/pair)
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from bci_iot.types import IntentLabel

log = logging.getLogger(__name__)

# Map ML labels used by the local pipeline to product SÌ/NO.
_LABEL_TO_YN: dict[str, str] = {
    IntentLabel.ACCEPT.value: "SI",
    IntentLabel.REJECT.value: "NO",
    "ACCEPT": "SI",
    "REJECT": "NO",
    "SI": "SI",
    "NO": "NO",
    "YES": "SI",
}


def intent_label_to_yes_no(label: str | IntentLabel) -> str | None:
    key = label.value if isinstance(label, IntentLabel) else str(label or "").strip().upper()
    return _LABEL_TO_YN.get(key)


def cloud_base_url(explicit: str | None = None) -> str:
    raw = (explicit or os.environ.get("BCI_IOT_PUBLIC_URL") or "").strip().rstrip("/")
    return raw


def worker_token(explicit: str | None = None) -> str:
    return (explicit or os.environ.get("BCI_IOT_WORKER_TOKEN") or "").strip()


def post_local_intent(
    *,
    answer: str,
    base_url: str | None = None,
    token: str | None = None,
    meta: dict[str, Any] | None = None,
    timeout_s: float = 12.0,
) -> dict[str, Any]:
    """POST a pre-classified SÌ/NO from the PC worker to the cloud hub."""

    base = cloud_base_url(base_url)
    tok = worker_token(token)
    if not base:
        raise ValueError("Manca BCI_IOT_PUBLIC_URL (hub cloud).")
    if not tok:
        raise ValueError("Manca BCI_IOT_WORKER_TOKEN (token companion dopo /api/companion/pair).")

    yn = intent_label_to_yes_no(answer) or str(answer).strip().upper()
    if yn not in {"SI", "NO"}:
        raise ValueError(f"Serve SÌ/NO, ricevuto: {answer!r}")

    url = f"{base}/api/companion/intent"
    headers = {
        "Authorization": f"Bearer {tok}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    body = {"answer": yn, "source": "local_worker", "meta": dict(meta or {})}
    with httpx.Client(timeout=timeout_s) as client:
        res = client.post(url, headers=headers, json=body)
        try:
            data = res.json()
        except Exception:
            data = {"detail": res.text}
        if res.status_code >= 400:
            detail = data.get("detail") if isinstance(data, dict) else data
            raise RuntimeError(f"cloud intent HTTP {res.status_code}: {detail}")
        return data if isinstance(data, dict) else {"raw": data}


def maybe_bridge_pipeline_results(
    results: list[Any],
    *,
    base_url: str | None = None,
    token: str | None = None,
) -> list[dict[str, Any]]:
    """For each pipeline step with ACCEPT/REJECT, push SÌ/NO to cloud (best-effort)."""

    base = cloud_base_url(base_url)
    tok = worker_token(token)
    if not base or not tok:
        log.info("cloud bridge skipped (set BCI_IOT_PUBLIC_URL + BCI_IOT_WORKER_TOKEN)")
        return []

    out: list[dict[str, Any]] = []
    for step in results:
        intent = getattr(step, "intent", None)
        if intent is None:
            continue
        label = getattr(intent, "label", None)
        yn = intent_label_to_yes_no(label) if label is not None else None
        if yn is None:
            continue
        conf = float(getattr(intent, "confidence", 0.0) or 0.0)
        meta = {
            "confidence": conf,
            "label": getattr(label, "value", str(label)),
            "latency_ms": getattr(step, "latency_ms", None),
        }
        try:
            payload = post_local_intent(answer=yn, base_url=base, token=tok, meta=meta)
            out.append({"ok": True, "answer": yn, "response": payload})
            log.info("cloud bridge pushed %s → %s", yn, payload.get("decision", {}).get("action"))
        except Exception as exc:
            log.warning("cloud bridge failed for %s: %s", yn, exc)
            out.append({"ok": False, "answer": yn, "error": str(exc)})
    return out
