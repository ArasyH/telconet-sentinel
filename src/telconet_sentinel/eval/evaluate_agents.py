"""Batch agent evaluation. [REQ-3.21, 3.22]

Run:
    python -m telconet_sentinel.eval.evaluate_agents --n 10 --seed 42
"""

from __future__ import annotations

import argparse
import json
from statistics import mean

import numpy as np
import pandas as pd

from telconet_sentinel.agents.orchestrator import run_rca
from telconet_sentinel.config import settings
from telconet_sentinel.ml.predict import predict_latest
from telconet_sentinel.schemas import FinalStatus


def evaluate(n: int = 10, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)

    df = pd.read_csv(settings.raw_csv)
    latest = predict_latest(df)
    wc = latest[latest["predicted_status"].isin(["Warning", "Critical"])]
    if len(wc) == 0:
        print("No Warning/Critical devices found — using all devices.")
        wc = latest

    n_actual = min(n, len(wc))
    sample = wc.sample(n=n_actual, random_state=int(rng.integers(0, 9999)))
    device_ids = sample["device_id"].tolist()

    results = []
    faithfulness_scores = []
    latencies_ms = []
    n_iterations_list = []
    approved_iter1 = 0
    approved_final = 0
    escalated = 0
    errors = 0
    invalid_cit_total = 0
    valid_cit_total = 0

    for did in device_ids:
        print(f"  RCA → {did}", end=" ", flush=True)
        result = run_rca(did)
        results.append(result)
        latencies_ms.append(result.total_latency_ms)
        n_iter = len(result.iterations)
        n_iterations_list.append(n_iter)

        if result.final_status == FinalStatus.ERROR:
            errors += 1
            print("ERROR")
            continue

        if result.final_status == FinalStatus.UNVERIFIED_ESCALATE_TO_HUMAN:
            escalated += 1

        if result.final_status == FinalStatus.APPROVED:
            approved_final += 1
            if n_iter == 1:
                approved_iter1 += 1

        for rec in result.iterations:
            faithfulness_scores.append(rec.judge.sop_faithfulness_score)
            n_invalid = len(rec.judge.invalid_citations)
            n_action = len(rec.draft.action_plan)
            invalid_cit_total += n_invalid
            valid_cit_total += (n_action - n_invalid)

        print(f"{result.final_status.value} ({n_iter} iter)")

    n_run = n_actual - errors
    total_citations = invalid_cit_total + valid_cit_total
    metrics = {
        "n_evaluated": n_actual,
        "n_errors": errors,
        "approval_rate_iter1": approved_iter1 / n_run if n_run else 0,
        "approval_rate_final": approved_final / n_run if n_run else 0,
        "escalation_rate": escalated / n_run if n_run else 0,
        "avg_faithfulness_score": mean(faithfulness_scores) if faithfulness_scores else 0,
        "avg_iterations": mean(n_iterations_list) if n_iterations_list else 0,
        "citation_validity_rate": valid_cit_total / total_citations if total_citations else 0,
        "latency_p50_ms": sorted(latencies_ms)[len(latencies_ms) // 2] if latencies_ms else 0,
        "latency_p95_ms": sorted(latencies_ms)[int(len(latencies_ms) * 0.95)] if latencies_ms else 0,
        "faithfulness_disclaimer": (
            "sop_faithfulness_score is LLM-as-judge self-assessment, not ground-truth human evaluation."
        ),
    }

    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
    settings.agent_metrics_path.write_text(json.dumps(metrics, indent=2))
    print(f"\nAgent metrics written to {settings.agent_metrics_path}")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch agent evaluation")
    parser.add_argument("--n", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    metrics = evaluate(args.n, args.seed)
    print(json.dumps({k: v for k, v in metrics.items() if k != "faithfulness_disclaimer"}, indent=2))


if __name__ == "__main__":
    main()
