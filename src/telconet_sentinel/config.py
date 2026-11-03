"""Settings — all constants, paths, and model names live here. [NFR-3]"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Settings:
    # LLM provider — "groq" | "openrouter" | "fake"
    llm_mode: str = os.getenv("LLM_MODE", "groq")
    llm_timeout_s: int = int(os.getenv("LLM_TIMEOUT_S", "30"))

    # Groq (active when llm_mode="groq")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

    # OpenRouter (active when llm_mode="openrouter")
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")
    openrouter_base_url: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    # Agent loop
    approval_threshold: int = int(os.getenv("APPROVAL_THRESHOLD", "80"))
    max_iterations: int = int(os.getenv("MAX_ITERATIONS", "2"))
    retrieval_k: int = int(os.getenv("RETRIEVAL_K", "4"))

    # Generator & Judge temperatures
    generator_temperature: float = 0.2
    judge_temperature: float = 0.0

    # Data root
    data_dir: Path = Path(os.getenv("DATA_DIR", "data"))

    # Derived paths
    @property
    def raw_csv(self) -> Path:
        return self.data_dir / "raw" / "telemetry.csv"

    @property
    def sop_dir(self) -> Path:
        return self.data_dir / "sop"

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma"

    @property
    def artifacts_dir(self) -> Path:
        return self.data_dir / "artifacts"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def model_path(self) -> Path:
        return self.artifacts_dir / "model.joblib"

    @property
    def ml_metrics_path(self) -> Path:
        return self.artifacts_dir / "ml_metrics.json"

    @property
    def agent_metrics_path(self) -> Path:
        return self.artifacts_dir / "agent_metrics.json"

    @property
    def rca_log_path(self) -> Path:
        return self.logs_dir / "rca_runs.jsonl"

    # Data-gen constants
    default_seed: int = 42
    default_devices: int = 50
    default_steps: int = 288  # 24 h × 12 samples/h (5-min interval)
    label_noise_pct: float = 0.02

    # Device composition
    device_counts: dict[str, int] = {"OLT": 10, "ONT": 35, "CORE_ROUTER": 5}
    regions: list[str] = ["JAKARTA", "BANDUNG", "SURABAYA", "MEDAN", "MAKASSAR"]
    region_abbr: dict[str, str] = {
        "JAKARTA": "JKT",
        "BANDUNG": "BDG",
        "SURABAYA": "SBY",
        "MEDAN": "MDN",
        "MAKASSAR": "MKS",
    }

    # Anomaly thresholds (design.md §3.2)
    critical_rx: float = -28.0   # dBm; for OLT, ONT only
    warning_rx: float = -25.0
    critical_packet_loss: float = 5.0    # %
    warning_packet_loss: float = 1.0
    critical_latency: float = 150.0      # ms
    warning_latency: float = 60.0
    critical_cpu: float = 95.0           # %
    warning_cpu: float = 85.0
    critical_temp: float = 75.0          # °C
    warning_temp: float = 65.0

    # ChromaDB collection name
    chroma_collection: str = "sop_docs"


settings = Settings()
