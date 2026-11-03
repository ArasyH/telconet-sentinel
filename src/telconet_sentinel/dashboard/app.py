"""Streamlit OSS Dashboard — 4 tabs. [REQ-4.1–4.10]

Run:
    streamlit run src/telconet_sentinel/dashboard/app.py
"""

from __future__ import annotations

import json
import os

import pandas as pd
import streamlit as st

import telconet_sentinel.config as _cfg_mod
from telconet_sentinel.config import settings
from telconet_sentinel.dashboard.components import (
    confusion_matrix_heatmap,
    feature_importance_chart,
    judge_log_panel,
    kpi_cards,
    llm_provider_panel,
    synthetic_banner,
    time_series_chart,
)

st.set_page_config(
    page_title="TelcoNet-Sentinel OSS Dashboard",
    page_icon="📡",
    layout="wide",
)

# ── Streamlit Secrets (Streamlit Cloud hosting) ───────────────────────────────
# Keys set in the Streamlit Cloud dashboard (Settings → Secrets) are loaded here
# so the app runs without a .env file. Local .env still takes priority on dev.
_SECRET_VARS = [
    "LLM_MODE", "GROQ_API_KEY", "GROQ_MODEL",
    "OPENROUTER_API_KEY", "OPENROUTER_MODEL", "OPENROUTER_BASE_URL",
]
for _k in _SECRET_VARS:
    if _k in st.secrets:
        _v = str(st.secrets[_k])
        os.environ.setdefault(_k, _v)          # don't override if .env already set it
        _attr = _k.lower()
        if hasattr(_cfg_mod.settings, _attr) and not getattr(_cfg_mod.settings, _attr):
            setattr(_cfg_mod.settings, _attr, _v)


# ── Cached loaders ────────────────────────────────────────────────────────────

@st.cache_data
def load_telemetry() -> pd.DataFrame | None:
    if not settings.raw_csv.exists():
        return None
    return pd.read_csv(settings.raw_csv)


@st.cache_resource
def load_pipeline():
    if not settings.model_path.exists():
        return None
    import joblib
    return joblib.load(settings.model_path)


@st.cache_data
def load_ml_metrics() -> dict | None:
    if not settings.ml_metrics_path.exists():
        return None
    return json.loads(settings.ml_metrics_path.read_text())


@st.cache_data
def load_agent_metrics() -> dict | None:
    if not settings.agent_metrics_path.exists():
        return None
    return json.loads(settings.agent_metrics_path.read_text())


@st.cache_data
def get_predictions(df_hash: int) -> pd.DataFrame | None:
    df = load_telemetry()
    if df is None:
        return None
    pipeline = load_pipeline()
    if pipeline is None:
        return None
    from telconet_sentinel.ml.predict import predict_latest
    return predict_latest(df)


# ── App ────────────────────────────────────────────────────────────────────────

synthetic_banner()
st.title("📡 TelcoNet-Sentinel — OSS Anomaly Prediction & Agentic RCA")

# ── Sidebar: LLM Provider (global — visible from all tabs) ───────────────────
with st.sidebar:
    _llm_mode, _key_override, _selected_model = llm_provider_panel(_cfg_mod.settings)
    st.divider()

# Apply provider settings to the shared Settings instance so get_llm() picks
# them up without requiring a module reload (same object referenced everywhere).
_cfg_mod.settings.llm_mode = _llm_mode
if _llm_mode == "groq":
    if _key_override:
        _cfg_mod.settings.groq_api_key = _key_override
        os.environ["GROQ_API_KEY"] = _key_override
    _cfg_mod.settings.groq_model = _selected_model
else:
    if _key_override:
        _cfg_mod.settings.openrouter_api_key = _key_override
        os.environ["OPENROUTER_API_KEY"] = _key_override
    _cfg_mod.settings.openrouter_model = _selected_model

tab_overview, tab_prediction, tab_rca, tab_eval = st.tabs([
    "🌐 Network Overview",
    "🔍 Anomaly Prediction",
    "🤖 Agentic RCA",
    "📊 System Evaluation",
])

# ─── Tab 1: Network Overview ─────────────────────────────────────────────────
with tab_overview:
    st.header("Network Overview")
    df = load_telemetry()
    if df is None:
        st.error(
            "Telemetry CSV not found. Run:\n"
            "```bash\npython -m telconet_sentinel.data_gen.telemetry --seed 42 --overwrite\n```"
        )
    else:
        pred_df = get_predictions(hash(str(df.shape)))
        if pred_df is not None:
            kpi_cards(pred_df)
        else:
            st.info("Model not trained yet. Run: `python -m telconet_sentinel.ml.train`")

        with st.sidebar:
            st.header("Filters")
            regions = ["(all)"] + sorted(df["region"].unique().tolist())
            sel_region = st.selectbox("Region", regions)
            device_types = ["(all)"] + sorted(df["device_type"].unique().tolist())
            sel_type = st.selectbox("Device Type", device_types)

        filtered = df.copy()
        if sel_region != "(all)":
            filtered = filtered[filtered["region"] == sel_region]
        if sel_type != "(all)":
            filtered = filtered[filtered["device_type"] == sel_type]

        devices = sorted(filtered["device_id"].unique().tolist())
        sel_device = st.selectbox("Device ID", devices if devices else ["(none)"])
        metric_cols = ["rx_optical_power_dbm", "latency_ms", "packet_loss_pct", "cpu_load_pct", "temperature_c"]
        sel_metric = st.selectbox("Metric", metric_cols)

        if sel_device and sel_device != "(none)":
            fig = time_series_chart(filtered, sel_device, sel_metric)
            st.plotly_chart(fig, use_container_width=True)

# ─── Tab 2: Anomaly Prediction ────────────────────────────────────────────────
with tab_prediction:
    st.header("Anomaly Prediction (Latest per Device)")
    df = load_telemetry()
    if df is None:
        st.error("Telemetry CSV not found.")
    else:
        pred_df = get_predictions(hash(str(df.shape)))
        if pred_df is None:
            st.error(
                "Model not trained. Run:\n"
                "```bash\npython -m telconet_sentinel.ml.train\n```"
            )
        else:
            display_cols = [
                "device_id", "device_type", "region", "predicted_status",
                "proba_Normal", "proba_Warning", "proba_Critical",
            ]
            table = pred_df[display_cols].sort_values("proba_Critical", ascending=False).reset_index(drop=True)

            def _color_status(val):
                colors = {"Normal": "background-color:#d4edda", "Warning": "background-color:#fff3cd", "Critical": "background-color:#f8d7da"}
                return colors.get(val, "")

            styled = table.style.map(_color_status, subset=["predicted_status"])
            st.dataframe(styled, use_container_width=True, height=500)

# ─── Tab 3: Agentic RCA ──────────────────────────────────────────────────────
with tab_rca:
    st.header("Agentic RCA — Self-Verified with Judge/Critic")
    df = load_telemetry()
    pred_df = get_predictions(hash(str(df.shape))) if df is not None else None

    if pred_df is None:
        st.error("Run telemetry generator and train model first.")
    else:
        wc_devices = pred_df[pred_df["predicted_status"].isin(["Warning", "Critical"])]["device_id"].tolist()
        if not wc_devices:
            st.info("No Warning/Critical devices detected.")
        else:
            sel_device = st.selectbox("Select Warning/Critical Device", wc_devices)
            if st.button("🚀 Run Agentic RCA", type="primary"):
                _mode = _cfg_mod.settings.llm_mode
                _missing_key = (
                    _mode == "groq" and not _cfg_mod.settings.groq_api_key
                ) or (
                    _mode == "openrouter" and not _cfg_mod.settings.openrouter_api_key
                )
                if _mode != "fake" and _missing_key:
                    _provider_name = "Groq" if _mode == "groq" else "OpenRouter"
                    _env_var = "GROQ_API_KEY" if _mode == "groq" else "OPENROUTER_API_KEY"
                    st.error(
                        f"{_env_var} belum diisi untuk provider **{_provider_name}**. "
                        f"Masukkan key di sidebar atau set di `.env`. "
                        f"Untuk demo offline, set `LLM_MODE=fake` di `.env`."
                    )
                    st.stop()

                with st.status(f"Running RCA for {sel_device}...", expanded=True) as status_widget:
                    st.write("Building incident context...")
                    from telconet_sentinel.agents.orchestrator import run_rca
                    try:
                        result = run_rca(sel_device)
                    except Exception as exc:
                        st.error(f"RCA failed: {exc}")
                        st.stop()
                    status_widget.update(label=f"RCA complete — {result.final_status.value}", state="complete")

                st.subheader("Final Status")
                fs = result.final_status.value
                if fs == "APPROVED":
                    st.success(f"✅ {fs}")
                elif fs == "UNVERIFIED_ESCALATE_TO_HUMAN":
                    st.warning(f"⚠️ {fs} — Manual review required")
                else:
                    st.error(f"❌ {fs}: {result.error}")
                st.caption(
                    f"Provider: **{_cfg_mod.settings.llm_mode.upper()}** · "
                    f"Model: `{result.model}` · "
                    f"Latency: {result.total_latency_ms:.0f} ms"
                )

                if result.final_draft:
                    st.subheader("Action Plan")
                    for step in result.final_draft.action_plan:
                        ref = step.sop_reference
                        st.markdown(
                            f"**Step {step.step_no}** [{step.priority}]: {step.action}  \n"
                            f"*SOP Reference: {ref.sop_id} Step {ref.step}*"
                        )

                    with st.expander("Root Cause Details"):
                        d = result.final_draft
                        st.write(f"**Hypothesis:** {d.root_cause_hypothesis}")
                        st.write(f"**Category:** {d.root_cause_category.value}")
                        st.write(f"**Confidence:** {d.confidence:.0%}")
                        if d.telemetry_evidence:
                            st.write("**Telemetry Evidence:**")
                            for ev in d.telemetry_evidence:
                                st.write(f"  - {ev.metric}: {ev.observed_value} (threshold: {ev.threshold})")

                st.subheader("Judge Log")
                iter_dicts = [rec.model_dump() for rec in result.iterations]
                judge_log_panel(iter_dicts)

# ─── Tab 4: System Evaluation ────────────────────────────────────────────────
with tab_eval:
    st.header("System Evaluation Metrics")

    ml_metrics = load_ml_metrics()
    if ml_metrics is None:
        st.warning(
            "ML metrics not found. Run:\n"
            "```bash\npython -m telconet_sentinel.ml.train\n```"
        )
    else:
        st.subheader("ML Model Metrics")
        col1, col2, col3 = st.columns(3)
        col1.metric("Macro-F1", f"{ml_metrics.get('macro_f1', 0):.3f}")
        col2.metric("Critical Recall", f"{ml_metrics.get('recall', {}).get('Critical', 0):.3f}")
        col3.metric("Quality Gate", ml_metrics.get("quality_gate", "N/A"))

        st.subheader("Confusion Matrix")
        cm = ml_metrics.get("confusion_matrix", {})
        if cm:
            st.plotly_chart(
                confusion_matrix_heatmap(cm["values"], cm["labels"]),
                use_container_width=True,
            )

        st.subheader("Feature Importance")
        fi = ml_metrics.get("feature_importance", {})
        if fi:
            st.plotly_chart(feature_importance_chart(fi), use_container_width=True)

    agent_metrics = load_agent_metrics()
    if agent_metrics is None:
        st.warning(
            "Agent metrics not found. Run:\n"
            "```bash\npython -m telconet_sentinel.eval.evaluate_agents --n 10\n```"
        )
    else:
        st.subheader("Agent Evaluation Metrics")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Approval Rate (iter 1)", f"{agent_metrics.get('approval_rate_iter1', 0):.1%}")
        c2.metric("Approval Rate (final)", f"{agent_metrics.get('approval_rate_final', 0):.1%}")
        c3.metric("Avg Faithfulness", f"{agent_metrics.get('avg_faithfulness_score', 0):.1f}/100")
        c4.metric("Citation Validity", f"{agent_metrics.get('citation_validity_rate', 0):.1%}")
        c5, c6 = st.columns(2)
        c5.metric("Latency p50", f"{agent_metrics.get('latency_p50_ms', 0):.0f} ms")
        c6.metric("Latency p95", f"{agent_metrics.get('latency_p95_ms', 0):.0f} ms")
        st.caption(
            "⚠️ " + agent_metrics.get("faithfulness_disclaimer", "")
        )
