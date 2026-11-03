"""Synthetic telemetry CSV generator. [REQ-1.1 – 1.5, 1.9, 1.10]

Run:
    python -m telconet_sentinel.data_gen.telemetry --seed 42 --overwrite
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from telconet_sentinel.config import settings
from telconet_sentinel.data_gen.labeling import apply_labels

# ── Baseline stats per device type (design.md §3.2) ──────────────────────────
BASELINE: dict[str, dict[str, tuple[float, float]]] = {
    "OLT": {
        "rx": (-12.0, 1.5),
        "latency": (5.0, 2.0),
        "pkt_loss": (0.02, 0.02),
        "cpu": (40.0, 10.0),
        "temp": (45.0, 4.0),
    },
    "ONT": {
        "rx": (-20.0, 1.5),
        "latency": (12.0, 4.0),
        "pkt_loss": (0.05, 0.05),
        "cpu": (25.0, 8.0),
        "temp": (40.0, 4.0),
    },
    "CORE_ROUTER": {
        "rx": (-5.0, 1.0),
        "latency": (2.0, 1.0),
        "pkt_loss": (0.01, 0.01),
        "cpu": (50.0, 12.0),
        "temp": (50.0, 5.0),
    },
}

# ── Fault scenarios (design.md §3.2) ─────────────────────────────────────────
SCENARIOS = {
    "FIBER_DEGRADATION": {
        "device_types": {"OLT", "ONT"},
        "duration_range": (6, 36),
        "prob": 0.04,
    },
    "CONGESTION": {
        "device_types": {"OLT", "ONT", "CORE_ROUTER"},
        "duration_range": (6, 24),
        "prob": 0.04,
    },
    "OVERHEATING": {
        "device_types": {"OLT", "CORE_ROUTER"},
        "duration_range": (6, 30),
        "prob": 0.03,
    },
    "CPU_SPIKE": {
        "device_types": {"OLT", "CORE_ROUTER"},
        "duration_range": (6, 18),
        "prob": 0.03,
    },
}


def _build_device_list(n_devices: int, rng: np.random.Generator) -> list[dict]:
    devices = []
    counts = {dt: settings.device_counts.get(dt, 0) for dt in ["OLT", "ONT", "CORE_ROUTER"]}
    # Scale counts proportionally if n_devices != 50
    if n_devices != 50:
        total = sum(counts.values())
        counts = {
            "OLT": max(1, round(n_devices * counts["OLT"] / total)),
            "CORE_ROUTER": max(1, round(n_devices * counts["CORE_ROUTER"] / total)),
        }
        counts["ONT"] = n_devices - counts["OLT"] - counts["CORE_ROUTER"]
        counts["ONT"] = max(1, counts["ONT"])

    prefix_map = {"OLT": "OLT", "ONT": "ONT", "CORE_ROUTER": "CR"}
    region_list = settings.regions
    region_abbr = settings.region_abbr
    idx = 0
    for dt, cnt in counts.items():
        for i in range(cnt):
            region = region_list[idx % len(region_list)]
            device_id = f"{prefix_map[dt]}-{region_abbr[region]}-{i+1:03d}"
            devices.append({"device_id": device_id, "device_type": dt, "region": region})
            idx += 1
    return devices


def _apply_episode(
    signals: dict[str, np.ndarray],
    scenario: str,
    device_type: str,
    start: int,
    end: int,
    severity: str,  # "warning" | "critical"
    rng: np.random.Generator,
) -> None:
    if scenario == "FIBER_DEGRADATION":
        if device_type == "OLT":
            drop = rng.uniform(13.5, 15.5) if severity == "warning" else rng.uniform(17, 22)
        else:  # ONT
            drop = rng.uniform(5.5, 7.5) if severity == "warning" else rng.uniform(8.5, 14)
        signals["rx"][start:end] -= drop
        pkt_inc = rng.uniform(0.5, 2.0) if severity == "warning" else rng.uniform(2.0, 5.5)
        signals["pkt_loss"][start:end] += pkt_inc
    elif scenario == "CONGESTION":
        # Use packet_loss as the primary trigger (more reliable cross-device)
        pkt_inc = rng.uniform(1.2, 3.5) if severity == "warning" else rng.uniform(5.5, 9.0)
        signals["pkt_loss"][start:end] += pkt_inc
        lat_factor = rng.uniform(5, 11) if severity == "warning" else rng.uniform(13, 22)
        signals["latency"][start:end] *= lat_factor
    elif scenario == "OVERHEATING":
        temp_inc = rng.uniform(21, 28) if severity == "warning" else rng.uniform(30, 42)
        signals["temp"][start:end] += temp_inc
        cpu_inc = rng.uniform(12, 25) if severity == "warning" else rng.uniform(28, 40)
        signals["cpu"][start:end] += cpu_inc
    elif scenario == "CPU_SPIKE":
        cpu_target = rng.uniform(86, 93) if severity == "warning" else rng.uniform(96, 100)
        signals["cpu"][start:end] = np.maximum(signals["cpu"][start:end], cpu_target)


def _inject_faults(
    signals: dict[str, np.ndarray],
    device_type: str,
    n_steps: int,
    rng: np.random.Generator,
) -> None:
    """Two-tier fault injection to hit Warning≈12-14%, Critical≈5-7% before noise."""
    applicable = [s for s, p in SCENARIOS.items() if device_type in p["device_types"]]
    if not applicable:
        return

    # Tier 1: Warning-level fault (prob 0.92, duration 35-55 steps)
    if rng.random() < 0.92:
        scenario = applicable[rng.integers(len(applicable))]
        dur = int(rng.integers(35, 55))
        start = int(rng.integers(0, max(1, n_steps - dur)))
        end = min(start + dur, n_steps)
        _apply_episode(signals, scenario, device_type, start, end, "warning", rng)

    # Tier 2: Critical-level fault (prob 0.68, duration 18-28 steps)
    if rng.random() < 0.68:
        scenario = applicable[rng.integers(len(applicable))]
        dur = int(rng.integers(18, 28))
        start = int(rng.integers(0, max(1, n_steps - dur)))
        end = min(start + dur, n_steps)
        _apply_episode(signals, scenario, device_type, start, end, "critical", rng)


def _clamp(arr: np.ndarray, lo: float, hi: float) -> np.ndarray:
    return np.clip(arr, lo, hi)


def generate_telemetry(
    seed: int = 42,
    n_devices: int = 50,
    n_steps: int = 288,
) -> pd.DataFrame:
    """Generate synthetic telemetry DataFrame."""
    rng = np.random.default_rng(seed)
    devices = _build_device_list(n_devices, rng)
    base_ts = datetime(2026, 1, 1, 0, 0, 0)

    rows = []
    for dev in devices:
        dt = dev["device_type"]
        bl = BASELINE[dt]

        # Base signals
        rx = rng.normal(bl["rx"][0], bl["rx"][1], n_steps)
        latency = np.abs(rng.normal(bl["latency"][0], bl["latency"][1], n_steps))
        pkt_loss = np.abs(rng.normal(bl["pkt_loss"][0], bl["pkt_loss"][1], n_steps))
        cpu = np.abs(rng.normal(bl["cpu"][0], bl["cpu"][1], n_steps))
        temp = np.abs(rng.normal(bl["temp"][0], bl["temp"][1], n_steps))

        signals = {"rx": rx, "latency": latency, "pkt_loss": pkt_loss, "cpu": cpu, "temp": temp}
        _inject_faults(signals, dt, n_steps, rng)

        rx = _clamp(signals["rx"], -40.0, 3.0)
        latency = _clamp(signals["latency"], 0.5, 1000.0)
        pkt_loss = _clamp(signals["pkt_loss"], 0.0, 100.0)
        cpu = _clamp(signals["cpu"], 0.0, 100.0)
        temp = _clamp(signals["temp"], 10.0, 100.0)

        for step in range(n_steps):
            ts = (base_ts + timedelta(minutes=5 * step)).isoformat()
            rows.append({
                "timestamp": ts,
                "device_id": dev["device_id"],
                "region": dev["region"],
                "device_type": dt,
                "rx_optical_power_dbm": round(float(rx[step]), 2),
                "latency_ms": round(float(latency[step]), 2),
                "packet_loss_pct": round(float(pkt_loss[step]), 3),
                "cpu_load_pct": round(float(cpu[step]), 1),
                "temperature_c": round(float(temp[step]), 1),
            })

    df = pd.DataFrame(rows)
    df = apply_labels(df, rng)
    return df


def validate_telemetry(df: pd.DataFrame) -> None:
    """Validate CSV schema before writing. [REQ-1.10]"""
    required = [
        "timestamp", "device_id", "region", "device_type",
        "rx_optical_power_dbm", "latency_ms", "packet_loss_pct",
        "cpu_load_pct", "temperature_c", "anomaly_status",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    if df.isnull().any().any():
        raise ValueError("Null values found in telemetry data")
    bounds = {
        "rx_optical_power_dbm": (-40.0, 3.0),
        "latency_ms": (0.5, 1000.0),
        "packet_loss_pct": (0.0, 100.0),
        "cpu_load_pct": (0.0, 100.0),
        "temperature_c": (10.0, 100.0),
    }
    for col, (lo, hi) in bounds.items():
        if (df[col] < lo).any() or (df[col] > hi).any():
            raise ValueError(f"Column {col} out of bounds [{lo}, {hi}]")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic telemetry CSV")
    parser.add_argument("--seed", type=int, default=settings.default_seed)
    parser.add_argument("--devices", type=int, default=settings.default_devices)
    parser.add_argument("--steps", type=int, default=settings.default_steps)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    out_path = settings.raw_csv
    if out_path.exists() and not args.overwrite:
        print(f"ERROR: {out_path} already exists. Use --overwrite to replace.", file=sys.stderr)
        sys.exit(1)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df = generate_telemetry(args.seed, args.devices, args.steps)
    validate_telemetry(df)
    df.to_csv(out_path, index=False)
    dist = df["anomaly_status"].value_counts(normalize=True).round(3)
    print(f"Written {len(df)} rows to {out_path}")
    print(dist.to_string())


if __name__ == "__main__":
    main()
