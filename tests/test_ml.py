"""Tests for ML training and prediction. [REQ-2.3, 2.8, 2.9]"""


import pandas as pd
import pytest

from telconet_sentinel.data_gen.telemetry import generate_telemetry
from telconet_sentinel.ml.features import CATEGORICAL_FEATURES, NUMERIC_FEATURES


def _small_df(n_devices=10, n_steps=50, seed=42) -> pd.DataFrame:
    return generate_telemetry(seed=seed, n_devices=n_devices, n_steps=n_steps)


def test_train_produces_model_and_metrics(tmp_path, monkeypatch):
    from telconet_sentinel import config as cfg
    monkeypatch.setattr(type(cfg.settings), "raw_csv",
                        property(lambda self: tmp_path / "telemetry.csv"))
    monkeypatch.setattr(type(cfg.settings), "model_path",
                        property(lambda self: tmp_path / "model.joblib"))
    monkeypatch.setattr(type(cfg.settings), "ml_metrics_path",
                        property(lambda self: tmp_path / "metrics.json"))
    monkeypatch.setattr(type(cfg.settings), "artifacts_dir",
                        property(lambda self: tmp_path))

    df = _small_df()
    (tmp_path / "telemetry.csv").parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(tmp_path / "telemetry.csv", index=False)

    from telconet_sentinel.ml.train import train
    metrics = train(csv_path=tmp_path / "telemetry.csv")

    assert (tmp_path / "model.joblib").exists()
    assert (tmp_path / "metrics.json").exists()
    assert "macro_f1" in metrics
    assert "quality_gate" in metrics


def test_no_device_id_leak(tmp_path):
    """No device_id should appear in both train and test sets."""
    from sklearn.model_selection import GroupShuffleSplit

    df = _small_df(n_devices=10, n_steps=50)
    groups = df["device_id"]
    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y = df["anomaly_status"]

    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(gss.split(X, y, groups))

    train_devices = set(groups.iloc[train_idx])
    test_devices = set(groups.iloc[test_idx])
    assert train_devices.isdisjoint(test_devices)


def test_predict_proba_sum_to_one(tmp_path):
    from telconet_sentinel.ml.predict import load_model, predict
    from telconet_sentinel.ml.train import train

    df = _small_df(n_devices=10, n_steps=50)
    csv = tmp_path / "telemetry.csv"
    df.to_csv(csv, index=False)

    import telconet_sentinel.config as cfg

    train(csv_path=csv)
    load_model.cache_clear()

    result = predict(df.head(5), model_path=cfg.settings.model_path)
    for _, row in result.iterrows():
        total = row["proba_Normal"] + row["proba_Warning"] + row["proba_Critical"]
        assert abs(total - 1.0) < 1e-6, f"Proba sum != 1: {total}"


def test_missing_column_raises():
    from telconet_sentinel.ml.predict import predict

    df = _small_df(n_devices=5, n_steps=5).drop(columns=["latency_ms"])
    with pytest.raises(ValueError, match="latency_ms"):
        predict(df)
