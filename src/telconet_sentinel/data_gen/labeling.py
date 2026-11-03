"""Vectorised label rules + 2% noise injection. [REQ-1.6]"""

from __future__ import annotations

import numpy as np
import pandas as pd

from telconet_sentinel.config import settings


def apply_labels(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Assign anomaly_status and flip 2% rows as label noise."""
    df = df.copy()

    optical_devices = df["device_type"].isin(["OLT", "ONT"])

    is_critical = (
        (optical_devices & (df["rx_optical_power_dbm"] <= settings.critical_rx))
        | (df["packet_loss_pct"] >= settings.critical_packet_loss)
        | (df["latency_ms"] >= settings.critical_latency)
        | (df["cpu_load_pct"] >= settings.critical_cpu)
        | (df["temperature_c"] >= settings.critical_temp)
    )

    is_warning = (
        ~is_critical
        & (
            (optical_devices & (df["rx_optical_power_dbm"] <= settings.warning_rx))
            | (df["packet_loss_pct"] >= settings.warning_packet_loss)
            | (df["latency_ms"] >= settings.warning_latency)
            | (df["cpu_load_pct"] >= settings.warning_cpu)
            | (df["temperature_c"] >= settings.warning_temp)
        )
    )

    df["anomaly_status"] = np.select(
        [is_critical, is_warning],
        ["Critical", "Warning"],
        default="Normal",
    )

    df = _inject_label_noise(df, rng)
    return df


def _inject_label_noise(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Flip 2% of rows to a neighbouring class."""
    n_flip = max(1, int(len(df) * settings.label_noise_pct))
    flip_idx = rng.choice(df.index, size=n_flip, replace=False)

    neighbours: dict[str, str] = {
        "Normal": "Warning",
        "Warning": "Critical",
        "Critical": "Warning",
    }
    df.loc[flip_idx, "anomaly_status"] = (
        df.loc[flip_idx, "anomaly_status"].map(neighbours)
    )
    return df
