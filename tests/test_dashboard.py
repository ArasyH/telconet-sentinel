"""Dashboard smoke test. [REQ-4.1]"""


def test_dashboard_imports():
    """Components module must import without error (app.py requires running Streamlit)."""
    import telconet_sentinel.dashboard.components  # noqa: F401


def test_status_badge():
    from telconet_sentinel.dashboard.components import status_badge
    assert "APPROVED" in status_badge("APPROVED")
    assert "🟢" in status_badge("APPROVED")
    assert "🔴" in status_badge("Critical")


def test_synthetic_banner_callable():
    from telconet_sentinel.dashboard.components import synthetic_banner
    assert callable(synthetic_banner)


def test_llm_provider_panel_callable():
    from telconet_sentinel.dashboard.components import llm_provider_panel
    assert callable(llm_provider_panel)


def test_provider_model_constants():
    """Groq and OpenRouter model dicts must have non-empty keys and valid model IDs."""
    from telconet_sentinel.dashboard.components import _GROQ_MODELS, _OPENROUTER_MODELS

    # All Groq model IDs should contain a slash (provider/model format)
    for label, model_id in _GROQ_MODELS.items():
        assert "/" in model_id, f"Groq model ID missing provider prefix: {model_id}"
        assert label.strip(), "Empty label in _GROQ_MODELS"

    # OpenRouter default must be present
    or_model_ids = list(_OPENROUTER_MODELS.values())
    assert "meta-llama/llama-3.3-70b-instruct" in or_model_ids

    # All entries must have non-empty labels
    for label in _OPENROUTER_MODELS:
        assert label.strip(), "Empty label in _OPENROUTER_MODELS"


def test_groq_default_model_valid():
    """Default Groq model must be qwen3.8-27b (JSON mode supported)."""
    from telconet_sentinel.config import settings
    assert settings.groq_model == "qwen/qwen3.8-27b"


def test_openrouter_default_model_valid():
    """Default OpenRouter model must be in the verified model list."""
    from telconet_sentinel.config import settings
    from telconet_sentinel.dashboard.components import _OPENROUTER_MODELS
    assert settings.openrouter_model in _OPENROUTER_MODELS.values()
