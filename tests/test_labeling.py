"""Tests for labeling rules. [REQ-1.6]"""

import numpy as np
import pandas as pd

from telconet_sentinel.data_gen.labeling import apply_labels


def _base_row(**overrides) -> dict:
    row = {
        "device_type": "OLT",
        "rx_optical_power_dbm": -12.0,
        "latency_ms": 5.0,
        "packet_loss_pct": 0.02,
        "cpu_load_pct": 40.0,
        "temperature_c": 45.0,
    }
    row.update(overrides)
    return row


def make_df(*rows) -> pd.DataFrame:
    return pd.DataFrame(list(rows))


def rng():
    return np.random.default_rng(0)


def test_rx_at_critical_threshold_for_olt():
    df = make_df(_base_row(rx_optical_power_dbm=-28.0))
    # Disable noise by using a seeded rng that won't flip this single row
    # (flip_idx chosen from 0..0 with 2% of 1 row = 0 rows, max 1)
    # With n=1, n_flip=1 always → the one row gets flipped.
    # We need to test the raw label before noise, so use a large df.
    rows = [_base_row(rx_optical_power_dbm=-28.0)] * 100
    df = make_df(*rows)
    result = apply_labels(df, np.random.default_rng(42))
    # Most rows should be Critical (a few will be flipped to Warning)
    assert (result["anomaly_status"] == "Critical").sum() >= 95


def test_rx_at_warning_threshold_for_olt():
    rows = [_base_row(rx_optical_power_dbm=-25.0)] * 100
    df = make_df(*rows)
    result = apply_labels(df, np.random.default_rng(42))
    assert (result["anomaly_status"] == "Warning").sum() >= 95


def test_core_router_rx_does_not_trigger_optical_label():
    """CORE_ROUTER with low rx should not be penalised by optical rules."""
    rows = [_base_row(device_type="CORE_ROUTER", rx_optical_power_dbm=-28.0)] * 100
    df = make_df(*rows)
    result = apply_labels(df, np.random.default_rng(42))
    assert (result["anomaly_status"] == "Normal").sum() >= 95


def test_normal_row_stays_normal():
    rows = [_base_row()] * 100
    df = make_df(*rows)
    result = apply_labels(df, np.random.default_rng(42))
    assert (result["anomaly_status"] == "Normal").sum() >= 95


def test_packet_loss_critical():
    rows = [_base_row(packet_loss_pct=5.0)] * 100
    df = make_df(*rows)
    result = apply_labels(df, np.random.default_rng(42))
    assert (result["anomaly_status"] == "Critical").sum() >= 95


def test_noise_flips_about_two_percent():
    rows = [_base_row()] * 1000
    df = make_df(*rows)
    result = apply_labels(df, np.random.default_rng(42))
    flipped = (result["anomaly_status"] != "Normal").sum()
    assert 10 <= flipped <= 30  # 2% ± tolerance
