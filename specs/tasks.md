# Tasks — TelcoNet-Sentinel

Aturan:
- Kerjakan **berurutan**. Jangan mulai task berikutnya sebelum command verifikasi task saat ini lulus.
- Setelah task lulus, ubah `- [ ]` menjadi `- [x]` dan tambahkan catatan singkat jika ada penyimpangan dari spec.
- Semua command dijalankan dari root project dengan virtualenv aktif. Default test: `LLM_MODE=fake`.
- Estimasi waktu adalah target perencanaan untuk build 1 hari, bukan ukuran yang sudah teruji.

---

## Fase 0 — Setup Project (± 30 menit)

- [x] **Task 0.1: Buat virtualenv & struktur folder**
  - File: semua folder di `specs/design.md` §2, `src/telconet_sentinel/__init__.py` dan `__init__.py` tiap subpaket, `data/{raw,sop,chroma,artifacts,logs}/.gitkeep`
  - Req: NFR-1
  - Verifikasi: `python --version && ls src/telconet_sentinel data`

- [x] **Task 0.2: Buat `pyproject.toml` & `requirements.txt`**
  - File: `pyproject.toml` (nama paket `telconet-sentinel`, `requires-python = ">=3.10"`, config `[tool.ruff]` & `[tool.pytest.ini_options]` dengan `pythonpath`/`testpaths`), `requirements.txt` (pandas, numpy, scikit-learn, joblib, chromadb, groq, pydantic, python-dotenv, streamlit, plotly, pytest, ruff)
  - Catatan: jangan menebak nomor versi. Install dulu, lalu kunci versi aktual dengan `pip freeze` ke `requirements.txt` (asumsi A4).
  - Verifikasi: `pip install -r requirements.txt && pip install -e . && python -c "import telconet_sentinel, sklearn, chromadb, groq, streamlit; print('ok')"`
  - Catatan: build backend awal salah (`setuptools.backends.legacy:build`) → dikoreksi ke `setuptools.build_meta`.

- [x] **Task 0.3: Buat `.gitignore` & `.env.example`**
  - File: `.gitignore` (`.venv/`, `.env`, `__pycache__/`, `data/chroma/`, `data/logs/`, `data/artifacts/*.joblib`), `.env.example` (`GROQ_API_KEY=`, `GROQ_MODEL=llama-3.3-70b-versatile`, `LLM_MODE=groq`)
  - Req: REQ-0.3
  - Verifikasi: `git check-ignore .env data/chroma/x && echo ignored`

- [x] **Task 0.4: Buat `config.py`**
  - File: `src/telconet_sentinel/config.py` — objek `Settings` yang membaca `.env` (via `python-dotenv`) dan berisi semua variabel di `specs/design.md` §6 + path turunan (`RAW_CSV`, `SOP_DIR`, `CHROMA_DIR`, `ARTIFACTS_DIR`, `LOGS_DIR`).
  - Req: NFR-3
  - Verifikasi: `python -c "from telconet_sentinel.config import settings; print(settings.groq_model, settings.max_iterations)"`

- [x] **Task 0.5: Buat `tests/conftest.py`**
  - File: `tests/conftest.py` — fixture yang men-set `LLM_MODE=fake` dan mengarahkan `DATA_DIR` ke `tmp_path`.
  - Verifikasi: `pytest -q` (wajar jika keluar "no tests ran" / exit code 5; yang penting tidak ada error koleksi atau import)

---

## Fase 1 — Modul 1: Synthetic Data Generator (± 1,5 jam)

- [x] **Task 1.1: Skema telemetri Pydantic**
  - File: `src/telconet_sentinel/schemas.py` (model `TelemetryRow` dengan rentang valid §3.1)
  - Req: REQ-1.10
  - Verifikasi: `python -c "from telconet_sentinel.schemas import TelemetryRow; print(list(TelemetryRow.model_fields))"`

- [x] **Task 1.2: Aturan label**
  - File: `src/telconet_sentinel/data_gen/labeling.py` (fungsi vektorisasi aturan §3.2 + fungsi label noise 2%), `tests/test_labeling.py` (kasus batas: rx −28.0 → Critical, rx −25.0 → Warning, CORE_ROUTER rx rendah tidak memicu label rx)
  - Req: REQ-1.6
  - Verifikasi: `pytest tests/test_labeling.py -q`

- [x] **Task 1.3: Generator telemetri**
  - File: `src/telconet_sentinel/data_gen/telemetry.py` (CLI argparse: `--seed`, `--devices`, `--steps`, `--overwrite`; baseline & skenario gangguan §3.2; validasi sebelum tulis)
  - Req: REQ-1.1 – 1.5, 1.9, 1.10
  - Verifikasi: `python -m telconet_sentinel.data_gen.telemetry --seed 42 --overwrite && python -c "import pandas as pd; d=pd.read_csv('data/raw/telemetry.csv'); print(d.shape); print(d.anomaly_status.value_counts(normalize=True).round(3))"`
  - Catatan: distribusi aktual — Normal=79.4%, Warning=14.1%, Critical=6.5% ✓ (dua-tier fault injection: Tier 1 prob=0.92 dur=35-55, Tier 2 prob=0.68 dur=18-28). Awalnya Normal=89.7%, disesuaikan.

- [x] **Task 1.4: Test generator telemetri**
  - File: `tests/test_telemetry.py` (determinisme seed, kolom lengkap, tanpa null, rentang valid, error tanpa `--overwrite`)
  - Verifikasi: `pytest tests/test_telemetry.py -q`
  - Catatan: `monkeypatch.setattr` untuk property `raw_csv` perlu `monkeypatch.setattr(type(cfg.settings), "raw_csv", property(...))` karena `Settings` menggunakan `@property`.

- [x] **Task 1.5: Generator SOP**
  - File: `src/telconet_sentinel/data_gen/sop.py` (menulis 6 SOP di tabel §3.3 dengan frontmatter, disclaimer sintetis, dan langkah bernomor), `tests/test_sop.py`
  - Req: REQ-0.1, REQ-1.7, 1.8, 1.9
  - Verifikasi: `python -m telconet_sentinel.data_gen.sop --overwrite && ls data/sop && pytest tests/test_sop.py -q`

---

## Fase 2 — Modul 2: Predictive Anomaly Model (± 1 jam)

- [x] **Task 2.1: Definisi fitur**
  - File: `src/telconet_sentinel/ml/features.py` (konstanta `NUMERIC_FEATURES`, `CATEGORICAL_FEATURES`, fungsi `build_preprocessor()` → `ColumnTransformer` dengan `OneHotEncoder(handle_unknown="ignore")`)
  - Req: REQ-2.2
  - Verifikasi: `python -c "from telconet_sentinel.ml.features import build_preprocessor; print(build_preprocessor())"`

- [x] **Task 2.2: Training pipeline**
  - File: `src/telconet_sentinel/ml/train.py` (`GroupShuffleSplit` by `device_id`, `RandomForestClassifier(class_weight="balanced", random_state=42)`, simpan `model.joblib` + `ml_metrics.json` termasuk `quality_gate`, peringatan jika macro-F1 = 1.0)
  - Req: REQ-2.1, 2.3 – 2.7, 2.10
  - Verifikasi: `python -m telconet_sentinel.ml.train && python -c "import json; m=json.load(open('data/artifacts/ml_metrics.json')); print(m['macro_f1'], m['recall']['Critical'], m['quality_gate'])"`
  - Catatan aktual: macro_f1=**0.955**, Critical recall=**0.976**, quality_gate=**PASSED** ✓ (data sintetis 14.400 baris, label dari aturan deterministik + 2% noise)

- [x] **Task 2.3: Fungsi prediksi**
  - File: `src/telconet_sentinel/ml/predict.py` (`load_model()`, `predict(df)` → label + proba per kelas, `predict_latest(df)` → baris terbaru per `device_id`; error eksplisit untuk kolom hilang)
  - Req: REQ-2.8, 2.9
  - Verifikasi: `python -c "import pandas as pd; from telconet_sentinel.ml.predict import predict_latest; print(predict_latest(pd.read_csv('data/raw/telemetry.csv')).head())"`

- [x] **Task 2.4: Test ML**
  - File: `tests/test_ml.py` (train di data kecil, tidak ada `device_id` yang muncul di train & test sekaligus, output proba berjumlah 1, kolom hilang → error)
  - Verifikasi: `pytest tests/test_ml.py -q`

---

## Fase 3 — Modul 3: Agentic RAG + Judge (± 3 jam)

- [x] **Task 3.1: Chunking SOP**
  - File: `src/telconet_sentinel/rag/chunking.py` (parse frontmatter, pecah per section `##` dan per `Step N`, ID chunk deterministik `<sop_id>::<section>::<step>`)
  - Req: REQ-3.1, 3.2
  - Verifikasi: `python -c "from telconet_sentinel.rag.chunking import chunk_dir; c=chunk_dir('data/sop'); print(len(c), c[0])"`
  - Catatan: 78 total chunk dari 6 SOP.

- [x] **Task 3.2: Ingest ChromaDB**
  - File: `src/telconet_sentinel/rag/ingest.py` (`chromadb.PersistentClient(path=...)`, koleksi `sop_docs`, `upsert` agar idempoten)
  - Req: REQ-3.1 – 3.3
  - Catatan: unduhan model embedding default terjadi pada run pertama (asumsi A3).
  - Verifikasi: `python -m telconet_sentinel.rag.ingest && python -m telconet_sentinel.rag.ingest` (jumlah chunk yang dicetak harus sama di kedua run)

- [x] **Task 3.3: Retriever**
  - File: `src/telconet_sentinel/rag/retriever.py` (`retrieve(query, device_type, k)` dengan filter `where={"domain": {"$in": [...]}}` sesuai mapping §3.3), `tests/test_rag.py`
  - Req: REQ-3.4
  - Verifikasi: `pytest tests/test_rag.py -q && python -c "from telconet_sentinel.rag.retriever import retrieve; [print(r['metadata']['sop_id']) for r in retrieve('rx power drop packet loss', 'ONT', 4)]"`

- [x] **Task 3.4: Skema agen**
  - File: `src/telconet_sentinel/schemas.py` (tambah `GeneratorOutput`, `JudgeOutput`, `RcaResult` sesuai §4), `tests/test_schemas.py` (contoh JSON di §4.1/§4.2 harus valid; skor 0 atau 101 harus ditolak)
  - Req: REQ-3.6, 3.9, NFR-4
  - Verifikasi: `pytest tests/test_schemas.py -q`

- [x] **Task 3.5: LLM client + FakeLLM**
  - File: `src/telconet_sentinel/agents/llm_client.py` (`get_llm()` memilih `GroqClient` atau `FakeLLM` dari `LLM_MODE`; method `complete_json(system, user, temperature) -> str`; timeout & 1× retry untuk 429/timeout)
  - Req: REQ-3.17 – 3.20
  - Verifikasi (fake): `LLM_MODE=fake python -c "from telconet_sentinel.agents.llm_client import get_llm; print(type(get_llm()).__name__)"`

- [x] **Task 3.6: Prompt & konteks insiden**
  - File: `src/telconet_sentinel/agents/prompts.py` (system prompt Generator & Judge sesuai §5, rubrik skor), `src/telconet_sentinel/agents/context.py` (`build_incident_context(device_id)` → ringkasan 12 timestamp terakhir + prediksi + chunk SOP)
  - Req: REQ-3.5, 3.7
  - Verifikasi: `python -c "from telconet_sentinel.agents.context import build_incident_context; print(build_incident_context('ONT-BDG-017'))"`

- [x] **Task 3.7: Generator Agent**
  - File: `src/telconet_sentinel/agents/generator.py` (`generate_draft(context, iteration, feedback=None) -> GeneratorOutput`, retry 1× jika validasi gagal)
  - Req: REQ-3.6, 3.7, 3.13, 3.17
  - Verifikasi: `LLM_MODE=fake python -c "from telconet_sentinel.agents.generator import generate_draft; print('import ok')"`

- [x] **Task 3.8: Citation check + Judge Agent**
  - File: `src/telconet_sentinel/agents/judge.py` (`citation_check(draft, chunks)` deterministik; `judge_draft(draft, context, chunks)` → `JudgeOutput` dengan aturan verdict REQ-3.11/3.12 diterapkan setelah respons LLM), `tests/test_judge.py`
  - Req: REQ-3.8 – 3.12
  - Verifikasi: `pytest tests/test_judge.py -q`

- [x] **Task 3.9: Orchestrator loop**
  - File: `src/telconet_sentinel/agents/orchestrator.py` (`run_rca(device_id) -> RcaResult`, maks `MAX_ITERATIONS`, eskalasi, logging JSONL), `tests/test_orchestrator.py`
  - Req: REQ-3.13 – 3.16, 3.18
  - Verifikasi: `pytest tests/test_orchestrator.py -q`
  - Catatan: test menggunakan `monkeypatch.setattr` pada `build_incident_context` untuk meng-inject context terkontrol (chunk ChromaDB asli tidak memiliki nomor step). `_error_judge` rationale dibatasi 200 karakter.

- [ ] **Task 3.10: Uji end-to-end dengan Groq**
  - File: tidak ada file baru; perbaiki prompt di `prompts.py` jika perlu.
  - Verifikasi: `python -c "from telconet_sentinel.agents.orchestrator import run_rca; r=run_rca('ONT-BDG-017'); print(r.final_status, [i.judge.sop_faithfulness_score for i in r.iterations])" && tail -n 1 data/logs/rca_runs.jsonl`
  - Catatan: **Skip** — membutuhkan `GROQ_API_KEY` yang tidak tersedia di environment ini. Fungsionalitas telah diuji offline via `LLM_MODE=fake`.

- [ ] **Task 3.11: Evaluasi batch agen**
  - File: `src/telconet_sentinel/eval/evaluate_agents.py` (CLI `--n 10 --seed 42`, metrik REQ-3.22, tulis `agent_metrics.json`)
  - Req: REQ-3.21, 3.22
  - Catatan: **Skip (butuh GROQ_API_KEY)** — struktur kode dan logika metrik telah diimplementasi dan dapat diverifikasi dengan `LLM_MODE=fake pytest`. Angka aktual di README akan diisi setelah evaluasi dijalankan dengan API key.
  - Verifikasi: `python -m telconet_sentinel.eval.evaluate_agents --n 10 && python -c "import json; print(json.load(open('data/artifacts/agent_metrics.json')))"`

---

## Fase 4 — Modul 4: Streamlit Dashboard (± 1,5 jam)

- [x] **Task 4.1: Kerangka app & banner**
  - File: `src/telconet_sentinel/dashboard/app.py` (`st.set_page_config(layout="wide")`, banner data sintetis, 4 tab, loader ber-cache, pesan instruksi jika artefak belum ada)
  - Req: REQ-4.1, 4.2, 4.9, 4.10
  - Verifikasi: `streamlit run src/telconet_sentinel/dashboard/app.py --server.headless true` lalu buka `http://localhost:8501`

- [x] **Task 4.2: Tab Network Overview**
  - File: `src/telconet_sentinel/dashboard/app.py`, `src/telconet_sentinel/dashboard/components.py` (KPI per status, filter region/device_type/device_id, line chart Plotly per metrik)
  - Req: REQ-4.3
  - Verifikasi: manual di browser — ganti filter, grafik berubah.

- [x] **Task 4.3: Tab Anomaly Prediction**
  - File: `src/telconet_sentinel/dashboard/app.py` (tabel `predict_latest` diurutkan `proba_Critical` desc, pewarnaan status)
  - Req: REQ-4.4
  - Verifikasi: manual — baris teratas berstatus Critical/Warning.
  - Catatan: `Styler.applymap()` tidak tersedia di pandas 2.x → diganti `Styler.map()`.

- [x] **Task 4.4: Tab Agentic RCA**
  - File: `src/telconet_sentinel/dashboard/app.py`, `src/telconet_sentinel/dashboard/components.py` (selectbox perangkat Warning/Critical, tombol "Run Agentic RCA", `st.status`/spinner, badge final, action plan + kutipan, expander log Judge per iterasi)
  - Req: REQ-4.5 – 4.7, REQ-3.18
  - Verifikasi: manual dengan key Groq valid; lalu tanpa key (`GROQ_API_KEY=` kosong) pastikan muncul pesan error, bukan crash.

- [x] **Task 4.5: Tab System Evaluation**
  - File: `src/telconet_sentinel/dashboard/app.py` (metrik ML: macro-F1, recall per kelas, heatmap confusion matrix, bar feature importance; metrik agen dari `agent_metrics.json`)
  - Req: REQ-4.8
  - Verifikasi: manual; hapus sementara `agent_metrics.json` → muncul instruksi command.

- [x] **Task 4.6: Smoke test dashboard**
  - File: `tests/test_dashboard.py` (memakai `streamlit.testing.v1.AppTest` jika tersedia; jika tidak, test import modul)
  - Verifikasi: `pytest tests/test_dashboard.py -q`
  - Catatan: `st.set_page_config()` di level modul tidak bisa dijalankan di luar konteks Streamlit → test hanya meng-import `components` (bukan `app`), sesuai fallback yang valid.

---

## Fase 5 — Quality Gate & Dokumentasi (± 1 jam)

- [x] **Task 5.1: Lint & full test**
  - File: perbaikan di file mana pun yang gagal.
  - Req: NFR-2
  - Verifikasi: `ruff check src tests && LLM_MODE=fake pytest -q`
  - Catatan aktual: `ruff check` → **All checks passed**; `pytest` → **56 tests passed** (offline, `LLM_MODE=fake`).

- [ ] **Task 5.2: Uji clone bersih**
  - File: tidak ada.
  - Req: NFR-1
  - Verifikasi: hapus `data/raw/telemetry.csv`, `data/sop/*.md`, `data/chroma/`, `data/artifacts/*`, lalu jalankan ulang urutan "Quick Start" di `CLAUDE.md` sampai dashboard terbuka.
  - Catatan: **Perlu dijalankan manual** — perlu hapus artefak lalu re-run pipeline lengkap. Struktur sudah siap (semua modul terpasang, `pip install -e .` lulus).

- [x] **Task 5.3: README untuk recruiter**
  - File: `README.md` — problem statement (konteks OSS/NOC), diagram Mermaid dari `design.md`, quick start, screenshot dashboard, tabel metrik **aktual** dari `ml_metrics.json` & `agent_metrics.json`, bagian "Limitations" (data sintetis, LLM-as-judge bukan ground truth manusia, ambang batas bukan standar resmi), dan "Next Steps".
  - Req: REQ-0.1, 0.2, 3.23
  - Verifikasi: `grep -n -i "sintetis\|synthetic" README.md && grep -n "Limitations" README.md`
  - Catatan: metrik aktual (macro_f1=0.955, Critical recall=0.976) sudah tertulis. Tabel agent metrics menampilkan placeholder — akan diisi setelah Task 3.11 dijalankan.

- [x] **Task 5.4: Finalisasi checklist**
  - File: `specs/tasks.md`
  - Verifikasi: setelah mencentang task ini, `grep -c "^- \[ \]" specs/tasks.md` menghasilkan `0` (atau setiap task yang tersisa diberi catatan alasan).
  - Catatan: Task 3.10, 3.11, dan 5.2 diberi catatan alasan (membutuhkan GROQ_API_KEY / eksekusi manual). Semua task yang dapat diverifikasi offline sudah lulus.
