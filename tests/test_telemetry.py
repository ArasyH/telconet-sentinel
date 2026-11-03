"""Tests for telemetry generator. [REQ-1.1–1.5, 1.9, 1.10]"""

import pandas as pd
import pytest

from telconet_sentinel.data_gen.telemetry import generate_telemetry, validate_telemetry

REQUIRED_COLUMNS = [
    "timestamp", "device_id", "region", "device_type",
    "rx_optical_power_dbm", "latency_ms", "packet_loss_pct",
    "cpu_load_pct", "temperature_c", "anomaly_status",
]


def test_default_shape():
    df = generate_telemetry(seed=42, n_devices=50, n_steps=288)
    assert df.shape == (14400, 10)


def test_required_columns():
    df = generate_telemetry(seed=42, n_devices=10, n_steps=10)
    for col in REQUIRED_COLUMNS:
        assert col in df.columns, f"Missing column: {col}"


def test_no_nulls():
    df = generate_telemetry(seed=42, n_devices=10, n_steps=10)
    assert not df.isnull().any().any()


def test_value_ranges():
    df = generate_telemetry(seed=42, n_devices=10, n_steps=20)
    assert df["rx_optical_power_dbm"].between(-40.0, 3.0).all()
    assert df["latency_ms"].between(0.5, 1000.0).all()
    assert df["packet_loss_pct"].between(0.0, 100.0).all()
    assert df["cpu_load_pct"].between(0.0, 100.0).all()
    assert df["temperature_c"].between(10.0, 100.0).all()


def test_determinism():
    df1 = generate_telemetry(seed=7, n_devices=5, n_steps=10)
    df2 = generate_telemetry(seed=7, n_devices=5, n_steps=10)
    pd.testing.assert_frame_equal(df1, df2)


def test_different_seeds_differ():
    df1 = generate_telemetry(seed=1, n_devices=5, n_steps=10)
    df2 = generate_telemetry(seed=2, n_devices=5, n_steps=10)
    assert not df1.equals(df2)


def test_anomaly_status_values():
    df = generate_telemetry(seed=42, n_devices=10, n_steps=20)
    assert set(df["anomaly_status"].unique()).issubset({"Normal", "Warning", "Critical"})


def test_device_types():
    df = generate_telemetry(seed=42, n_devices=50, n_steps=5)
    assert set(df["device_type"].unique()) == {"OLT", "ONT", "CORE_ROUTER"}


def test_regions():
    df = generate_telemetry(seed=42, n_devices=50, n_steps=5)
    regions = set(df["region"].unique())
    assert regions.issubset({"JAKARTA", "BANDUNG", "SURABAYA", "MEDAN", "MAKASSAR"})


def test_validate_raises_on_missing_column():
    df = generate_telemetry(seed=42, n_devices=5, n_steps=5).drop(columns=["timestamp"])
    with pytest.raises(ValueError, match="Missing columns"):
        validate_telemetry(df)


def test_overwrite_protection(tmp_path, monkeypatch):
    """Without --overwrite, CLI must not overwrite existing file."""
    import sys

    from telconet_sentinel import config as cfg_mod
    from telconet_sentinel.data_gen.telemetry import main

    out = tmp_path / "telemetry.csv"
    out.write_text("existing")

    monkeypatch.setattr(cfg_mod.settings, "data_dir", tmp_path)
    monkeypatch.setattr(type(cfg_mod.settings), "raw_csv",
                        property(lambda self: out))
    monkeypatch.setattr(sys, "argv", ["telemetry"])
    with pytest.raises(SystemExit):
        main()
