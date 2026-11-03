"""Dashboard helper components — KPI cards, badges, judge log panel. [REQ-4.6, 4.7]"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── LLM Provider constants ────────────────────────────────────────────────────

# Groq: verified Nov 2026 — only qwen3.8-27b supports JSON mode
_GROQ_MODELS: dict[str, str] = {
    "qwen3.8-27b  [JSON mode ✓ · ctx 131k]": "qwen/qwen3.8-27b",
    "gpt-oss-120b  [ctx 131k · no JSON mode]": "openai/gpt-oss-120b",
    "gpt-oss-20b   [ctx 131k · no JSON mode]": "openai/gpt-oss-20b",
}

# OpenRouter: verified Nov 2026, sorted by output price
_OPENROUTER_MODELS: dict[str, str] = {
    # Budget
    "mistral-small-3.2  · $0.075/$0.20 · 256k": "mistralai/mistral-small-3.2-24b-instruct",
    "claude-haiku-5.5   · $0.10/$0.50  · 1M":   "anthropic/claude-haiku-5.5",
    "qwen3-32b          · $0.08/$0.28  · 131k":  "qwen/qwen3-32b",
    "gpt-4.1-nano       · $0.10/$0.40  · 1M":    "openai/gpt-4.1-nano",
    # Mid-tier
    "llama-3.3-70b      · $0.20/$0.52  · 131k":  "meta-llama/llama-3.3-70b-instruct",
    "llama-4-maverick   · $0.19/$0.65  · 524k":  "meta-llama/llama-4-maverick",
    "gemini-2.5-flash   · $0.30/$2.50  · 1M":    "google/gemini-2.5-flash",
    "gpt-4o-mini        · $0.15/$0.60  · 128k":  "openai/gpt-4o-mini",
    "deepseek-chat      · $0.26/$1.03  · 163k":  "deepseek/deepseek-chat",
    # Premium
    "claude-haiku-4.5   · $1.00/$5.00  · 200k":  "anthropic/claude-haiku-4.5",
    "claude-sonnet-4.6  · $3.00/$15.00 · 1M":    "anthropic/claude-sonnet-4.6",
}


def synthetic_banner() -> None:
    st.warning(
        "⚠️ **Data Sintetis** — Dashboard ini menggunakan data telemetri dan SOP yang dibuat secara sintetis "
        "untuk keperluan proyek portofolio. **Bukan data operasional Telkom Indonesia.**",
        icon=None,
    )


def status_badge(status: str) -> str:
    colors = {
        "APPROVED": "🟢",
        "UNVERIFIED_ESCALATE_TO_HUMAN": "🟠",
        "ERROR": "🔴",
        "Normal": "🟢",
        "Warning": "🟡",
        "Critical": "🔴",
    }
    return f"{colors.get(status, '⚪')} {status}"


def kpi_cards(df: pd.DataFrame) -> None:
    counts = df["predicted_status"].value_counts().to_dict() if "predicted_status" in df.columns else {}
    for k in ["Normal", "Warning", "Critical"]:
        counts.setdefault(k, 0)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Perangkat", len(df))
    col2.metric("🟢 Normal", counts["Normal"])
    col3.metric("🟡 Warning", counts["Warning"])
    col4.metric("🔴 Critical", counts["Critical"])


def time_series_chart(df: pd.DataFrame, device_id: str, metric: str) -> go.Figure:
    dev_df = df[df["device_id"] == device_id].sort_values("timestamp")
    fig = px.line(
        dev_df,
        x="timestamp",
        y=metric,
        title=f"{metric} — {device_id}",
        color_discrete_sequence=["#1f77b4"],
    )
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20))
    return fig


def confusion_matrix_heatmap(cm_values: list[list[int]], labels: list[str]) -> go.Figure:
    fig = px.imshow(
        cm_values,
        x=labels,
        y=labels,
        text_auto=True,
        color_continuous_scale="Blues",
        title="Confusion Matrix",
        labels={"x": "Predicted", "y": "Actual"},
    )
    fig.update_layout(height=350)
    return fig


def feature_importance_chart(importance: dict[str, float]) -> go.Figure:
    sorted_items = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:15]
    names, vals = zip(*sorted_items) if sorted_items else ([], [])
    fig = px.bar(
        x=list(vals),
        y=list(names),
        orientation="h",
        title="Top Feature Importances",
        labels={"x": "Importance", "y": "Feature"},
        color_discrete_sequence=["#2196F3"],
    )
    fig.update_layout(height=400, yaxis={"autorange": "reversed"})
    return fig


def llm_provider_panel(current_settings) -> tuple[str, str | None, str]:
    """Render LLM provider selector in sidebar.

    Returns (llm_mode, api_key_override_or_None, selected_model).
    Must be called inside a ``with st.sidebar:`` block.
    """
    st.subheader("⚙️ LLM Provider")

    init_provider = "OpenRouter" if getattr(current_settings, "llm_mode", "groq") == "openrouter" else "Groq"
    if "sidebar_provider" not in st.session_state:
        st.session_state["sidebar_provider"] = init_provider

    provider = st.radio(
        "Provider",
        ["Groq", "OpenRouter"],
        key="sidebar_provider",
        horizontal=True,
    )

    st.markdown("**API Key** (isi untuk override `.env`)")

    if provider == "Groq":
        env_key = getattr(current_settings, "groq_api_key", "")
        if env_key:
            st.success("✅ Key aktif (dari `.env` / Secrets)", icon=None)
            with st.expander("Override API Key"):
                api_key = st.text_input(
                    "Groq API Key override",
                    type="password",
                    placeholder="gsk_…  (kosongkan untuk pakai key aktif)",
                    key="sidebar_groq_key",
                    label_visibility="collapsed",
                    help="Isi hanya jika ingin mengganti key yang sudah aktif.",
                )
        else:
            st.markdown("**API Key**")
            api_key = st.text_input(
                "Groq API Key",
                type="password",
                placeholder="gsk_…",
                key="sidebar_groq_key",
                label_visibility="collapsed",
                help="Dapatkan di console.groq.com → API Keys",
            )
            if not api_key:
                st.caption("⚠️ Key belum diisi · set di `.env`, Streamlit Secrets, atau di sini")

        groq_labels = list(_GROQ_MODELS.keys())
        default_model = getattr(current_settings, "groq_model", "qwen/qwen3.8-27b")
        default_label_idx = next(
            (i for i, (_, v) in enumerate(_GROQ_MODELS.items()) if v == default_model), 0
        )
        selected_label = st.selectbox(
            "Model Groq",
            groq_labels,
            index=default_label_idx,
            key="sidebar_groq_model",
        )
        if "no JSON mode" in selected_label:
            st.warning("Model ini tidak mendukung JSON mode — RCA kemungkinan gagal.", icon=None)

        return "groq", api_key or None, _GROQ_MODELS[selected_label]

    else:  # OpenRouter
        env_key = getattr(current_settings, "openrouter_api_key", "")
        if env_key:
            st.success("✅ Key aktif (dari `.env` / Secrets)", icon=None)
            with st.expander("Override API Key"):
                api_key = st.text_input(
                    "OpenRouter API Key override",
                    type="password",
                    placeholder="sk-or-v1-…  (kosongkan untuk pakai key aktif)",
                    key="sidebar_or_key",
                    label_visibility="collapsed",
                    help="Isi hanya jika ingin mengganti key yang sudah aktif.",
                )
        else:
            st.markdown("**API Key**")
            api_key = st.text_input(
                "OpenRouter API Key",
                type="password",
                placeholder="sk-or-v1-…",
                key="sidebar_or_key",
                label_visibility="collapsed",
                help="Dapatkan di openrouter.ai/keys",
            )
            if not api_key:
                st.caption("⚠️ Key belum diisi · set di `.env`, Streamlit Secrets, atau di sini")

        or_labels = list(_OPENROUTER_MODELS.keys())
        default_model = getattr(current_settings, "openrouter_model", "meta-llama/llama-3.3-70b-instruct")
        default_label_idx = next(
            (i for i, (_, v) in enumerate(_OPENROUTER_MODELS.items()) if v == default_model), 4
        )
        selected_label = st.selectbox(
            "Model OpenRouter",
            or_labels,
            index=default_label_idx,
            key="sidebar_or_model",
        )

        return "openrouter", api_key or None, _OPENROUTER_MODELS[selected_label]


def judge_log_panel(iterations: list) -> None:
    for i, rec in enumerate(iterations, start=1):
        j = rec["judge"]
        verdict_icon = "✅" if j["verdict"] == "APPROVED" else "⚠️"
        with st.expander(
            f"{verdict_icon} Iterasi {i} — Score: {j['sop_faithfulness_score']}/100 | {j['verdict']}",
            expanded=(i == len(iterations)),
        ):
            col1, col2 = st.columns(2)
            col1.metric("SOP Faithfulness", f"{j['sop_faithfulness_score']}/100")
            col2.metric("Telemetry Consistency", f"{j['telemetry_consistency_score']}/100")
            st.caption(f"Rationale: {j['rationale']}")

            if j.get("issues"):
                st.subheader("Issues")
                for issue in j["issues"]:
                    sev_icon = "🔴" if issue["severity"] == "HIGH" else ("🟡" if issue["severity"] == "MEDIUM" else "🟢")
                    st.markdown(f"{sev_icon} **{issue['type']}**: {issue['detail']}")

            if j.get("invalid_citations"):
                st.subheader("Invalid Citations")
                for ic in j["invalid_citations"]:
                    st.markdown(f"- `{ic['sop_id']}` Step {ic['step']}")

            if j.get("revision_instructions"):
                st.info(f"**Revision Instructions:** {j['revision_instructions']}")
