"""Model loading and prediction utilities. [REQ-2.8, 2.9]"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

from telconet_sentinel.config import settings
from telconet_sentinel.ml.features import CATEGORICAL_FEATURES, NUMERIC_FEATURES

REQUIRED_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
CLASSES = ["Normal", "Warning", "Critical"]


@lru_cache(maxsize=1)
def load_model(path: Path | None = None):
    p = path or settings.model_path
    if not p.exists():
        raise FileNotFoundError(f"Model not found at {p}. Run ml.train first.")
    return joblib.load(p)


def predict(df: pd.DataFrame, model_path: Path | None = None) -> pd.DataFrame:
    """Return predictions + per-class probabilities for each input row."""
    missing = [c for c in REQUIRED_FEATURES if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    pipeline = load_model(model_path)
    X = df[REQUIRED_FEATURES]
    labels = pipeline.predict(X)
    probas = pipeline.predict_proba(X)
    pipeline_classes = list(pipeline.classes_)

    result = df.copy()
    result["predicted_status"] = labels
    for cls in CLASSES:
        idx = pipeline_classes.index(cls) if cls in pipeline_classes else None
        result[f"proba_{cls}"] = probas[:, idx] if idx is not None else 0.0
    return result


def predict_latest(df: pd.DataFrame, model_path: Path | None = None) -> pd.DataFrame:
    """Return one prediction per device_id using its most recent row."""
    latest = (
        df.sort_values("timestamp")
        .groupby("device_id", as_index=False)
        .last()
    )
    return predict(latest, model_path)
