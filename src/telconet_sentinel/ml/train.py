"""Training pipeline for anomaly classification. [REQ-2.1, 2.3–2.7, 2.10]

Run:
    python -m telconet_sentinel.ml.train
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    recall_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline

from telconet_sentinel.config import settings
from telconet_sentinel.ml.features import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    TARGET,
    build_preprocessor,
)

QUALITY_MACRO_F1 = 0.80
QUALITY_CRITICAL_RECALL = 0.85
CLASSES = ["Normal", "Warning", "Critical"]


def build_pipeline() -> Pipeline:
    return Pipeline(
        steps=[
            ("preprocessor", build_preprocessor()),
            (
                "classifier",
                RandomForestClassifier(
                    class_weight="balanced",
                    random_state=42,
                    n_estimators=200,
                ),
            ),
        ]
    )


def train(csv_path: Path | None = None) -> dict:
    csv_path = csv_path or settings.raw_csv
    if not csv_path.exists():
        print(f"ERROR: {csv_path} not found. Run data_gen.telemetry first.", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(csv_path)
    feature_cols = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    X = df[feature_cols]
    y = df[TARGET]
    groups = df["device_id"]

    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(gss.split(X, y, groups))

    # Verify no device_id leaks between train and test
    train_devices = set(groups.iloc[train_idx])
    test_devices = set(groups.iloc[test_idx])
    assert train_devices.isdisjoint(test_devices), "device_id leak detected"

    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)

    macro_f1 = float(f1_score(y_test, y_pred, average="macro", zero_division=0))
    if macro_f1 == 1.0:
        print("WARNING: macro-F1 = 1.0 — possible label leakage (labels derived from rules).")

    recall_per_class = {
        cls: float(recall_score(
            y_test == cls, y_pred == cls, zero_division=0,
        ))
        for cls in CLASSES
    }

    cm = confusion_matrix(y_test, y_pred, labels=CLASSES).tolist()

    rf = pipeline.named_steps["classifier"]
    pre = pipeline.named_steps["preprocessor"]
    try:
        ohe = pre.named_transformers_["cat"]
        cat_names = list(ohe.get_feature_names_out(CATEGORICAL_FEATURES))
    except Exception:
        cat_names = []
    feature_names = NUMERIC_FEATURES + cat_names
    importance = {
        name: float(imp)
        for name, imp in zip(feature_names, rf.feature_importances_)
    }

    quality_gate = "PASSED"
    if macro_f1 < QUALITY_MACRO_F1 or recall_per_class.get("Critical", 0) < QUALITY_CRITICAL_RECALL:
        quality_gate = "FAILED"
        print(
            f"WARNING: Quality gate FAILED — macro-F1={macro_f1:.3f} "
            f"(need ≥{QUALITY_MACRO_F1}), "
            f"Critical recall={recall_per_class['Critical']:.3f} "
            f"(need ≥{QUALITY_CRITICAL_RECALL})"
        )

    metrics = {
        "macro_f1": macro_f1,
        "recall": recall_per_class,
        "precision": {
            cls: float(
                classification_report(y_test, y_pred, output_dict=True, zero_division=0)
                .get(cls, {})
                .get("precision", 0.0)
            )
            for cls in CLASSES
        },
        "confusion_matrix": {"labels": CLASSES, "values": cm},
        "feature_importance": importance,
        "quality_gate": quality_gate,
        "train_size": len(train_idx),
        "test_size": len(test_idx),
    }

    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, settings.model_path)
    settings.ml_metrics_path.write_text(json.dumps(metrics, indent=2))
    print(f"macro-F1={macro_f1:.3f}  Critical recall={recall_per_class['Critical']:.3f}  quality_gate={quality_gate}")
    print(f"Model saved to {settings.model_path}")
    return metrics


def main() -> None:
    train()


if __name__ == "__main__":
    main()
