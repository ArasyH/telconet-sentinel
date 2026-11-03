"""Incident context builder. [REQ-3.5]"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from telconet_sentinel.config import settings
from telconet_sentinel.ml.predict import predict
from telconet_sentinel.rag.retriever import retrieve


def build_incident_context(
    device_id: str,
    csv_path: str | None = None,
    chroma_dir: str | None = None,
    k: int | None = None,
) -> dict[str, Any]:
    """Build full incident context dict for device_id."""
    csv_path = csv_path or str(settings.raw_csv)
    df = pd.read_csv(csv_path)

    device_df = df[df["device_id"] == device_id].sort_values("timestamp")
    if device_df.empty:
        raise ValueError(f"device_id '{device_id}' not found in telemetry.")

    device_type = device_df["device_type"].iloc[0]
    last_12 = device_df.tail(12)

    pred_df = predict(device_df.tail(1))
    predicted_status = pred_df["predicted_status"].iloc[0]
    proba = {
        "Normal": float(pred_df["proba_Normal"].iloc[0]),
        "Warning": float(pred_df["proba_Warning"].iloc[0]),
        "Critical": float(pred_df["proba_Critical"].iloc[0]),
    }

    latest = last_12.iloc[-1]
    query = (
        f"device {device_type} predicted_status={predicted_status} "
        f"rx={latest.rx_optical_power_dbm:.2f} dBm "
        f"packet_loss={latest.packet_loss_pct:.3f}% "
        f"latency={latest.latency_ms:.1f}ms "
        f"cpu={latest.cpu_load_pct:.1f}% "
        f"temp={latest.temperature_c:.1f}C"
    )

    sop_chunks = retrieve(query, device_type, k=k, chroma_dir=chroma_dir)

    telemetry_summary = last_12[
        ["timestamp", "rx_optical_power_dbm", "latency_ms", "packet_loss_pct",
         "cpu_load_pct", "temperature_c", "anomaly_status"]
    ].to_dict(orient="records")

    return {
        "device_id": device_id,
        "device_type": device_type,
        "region": device_df["region"].iloc[0],
        "predicted_status": predicted_status,
        "ml_probabilities": proba,
        "telemetry_last_12": telemetry_summary,
        "sop_chunks": sop_chunks,
    }


def format_context_for_prompt(ctx: dict[str, Any]) -> str:
    """Render incident context dict as structured text for LLM prompt."""
    lines = [
        "<INCIDENT_CONTEXT>",
        f"device_id: {ctx['device_id']}",
        f"device_type: {ctx['device_type']}",
        f"region: {ctx['region']}",
        f"predicted_status: {ctx['predicted_status']}",
        f"ml_probabilities: {json.dumps(ctx['ml_probabilities'])}",
        "",
        "## Last 12 Telemetry Readings",
    ]
    for row in ctx["telemetry_last_12"]:
        lines.append(
            f"  {row['timestamp']} | rx={row['rx_optical_power_dbm']} dBm "
            f"| latency={row['latency_ms']} ms | pkt_loss={row['packet_loss_pct']}% "
            f"| cpu={row['cpu_load_pct']}% | temp={row['temperature_c']}°C "
            f"| status={row['anomaly_status']}"
        )
    lines.append("</INCIDENT_CONTEXT>")
    lines.append("")
    lines.append("<SOP_CONTEXT>")
    for chunk in ctx["sop_chunks"]:
        lines.append(f"[{chunk['metadata']['sop_id']} / {chunk['metadata']['section']} / {chunk['metadata']['step']}]")
        lines.append(chunk["text"])
        lines.append("")
    lines.append("</SOP_CONTEXT>")
    return "\n".join(lines)
