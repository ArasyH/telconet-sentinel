"""Feature definitions and preprocessor factory. [REQ-2.2]"""

from __future__ import annotations

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder

NUMERIC_FEATURES: list[str] = [
    "rx_optical_power_dbm",
    "latency_ms",
    "packet_loss_pct",
    "cpu_load_pct",
    "temperature_c",
]

CATEGORICAL_FEATURES: list[str] = ["device_type", "region"]

TARGET: str = "anomaly_status"


def build_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("num", "passthrough", NUMERIC_FEATURES),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
        ],
        remainder="drop",
    )
