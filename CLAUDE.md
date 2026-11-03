# CLAUDE.md — TelcoNet-Sentinel

## Ringkasan Proyek

**TelcoNet-Sentinel: OSS Network Anomaly Prediction & Self-Verified Agentic RCA Assistant.**
Proyek portofolio (target: Divisi Digital Product Telkom Indonesia) yang mensimulasikan alur kerja NOC/OSS:

1. Generate telemetri jaringan **sintetis** (OLT, ONT, Core Router) + dokumen SOP troubleshooting **sintetis**.
2. Prediksi status perangkat (`Normal` / `Warning` / `Critical`) dengan Scikit-Learn RandomForest.
3. Root Cause Analysis oleh **Generator Agent** berbasis RAG (ChromaDB), lalu divalidasi **Judge/Critic Agent** terhadap SOP (skor SOP Faithfulness 1–100, `APPROVED` / `REVISION_NEEDED`, maks 2 iterasi).
4. Dashboard Streamlit: metrik jaringan, prediksi ML, panel RCA + log Judge, metrik evaluasi.

Stack: Python 3.10+, scikit-learn, ChromaDB (lokal), Groq API (`llama-3.3-70b-versatile`) via Groq Python SDK, Pydantic, Streamlit, pytest, ruff.

## Sumber Kebenaran: folder `specs/`

Sebelum menulis atau mengubah kode, **selalu baca**:

| File | Isi |
|---|---|
| `specs/requirements.md` | Requirement format EARS (ID `REQ-x.y`, `NFR-x`) dan daftar asumsi A1–A5 |
| `specs/design.md` | Arsitektur Mermaid, struktur direktori, skema CSV, skema JSON agen, konfigurasi, error handling |
| `specs/tasks.md` | Checklist task berurutan + command verifikasi |

## Aturan Kerja untuk Claude Code

1. **Ikuti `specs/tasks.md` secara berurutan.** Kerjakan satu task sampai command verifikasinya lulus sebelum pindah ke task berikutnya.
2. **Perbarui checklist** setelah setiap task lulus: ubah `- [ ]` menjadi `- [x]` di `specs/tasks.md`, dan tambahkan sub-bullet `Catatan:` jika implementasi menyimpang dari spec atau jika ada angka hasil aktual (metrik ML / agen).
3. **Jangan menyimpang dari spec diam-diam.** Jika spec salah, ambigu, atau tidak bisa diimplementasi, berhenti, jelaskan masalahnya ke user, usulkan perubahan, lalu perbarui `requirements.md` / `design.md` setelah disetujui.
4. **Rujuk ID requirement** di docstring modul dan di pesan commit (contoh: `feat(agents): add judge citation check [REQ-3.10, REQ-3.11]`).
5. **Jangan mengarang fakta.** Jangan menulis angka metrik, versi library, atau ketersediaan model yang belum diverifikasi. Angka di README harus berasal dari `data/artifacts/*.json` hasil run aktual. Jika asumsi A1–A5 terbukti salah, catat di `specs/requirements.md` §0.2.
6. **Data sintetis harus diberi label sintetis** (REQ-0.1, 0.2). Jangan memakai logo, nama sistem internal, atau klaim bahwa SOP adalah milik Telkom.
7. **Jangan pernah commit `.env` atau API key.** Baca key hanya lewat `config.py`.
8. **Test tidak boleh memanggil jaringan.** Semua test berjalan dengan `LLM_MODE=fake`. Jangan skip atau hapus test untuk membuatnya lulus.
9. **Semua konstanta** (path, ambang batas, nama model, `MAX_ITERATIONS`, `APPROVAL_THRESHOLD`) hanya didefinisikan di `src/telconet_sentinel/config.py`.
10. Gunakan type hints, Pydantic untuk semua output LLM, dan jalankan `ruff check src tests` sebelum menyatakan task selesai.

## Setup Environment

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
cp .env.example .env        # lalu isi GROQ_API_KEY
```

Windows (PowerShell): ganti `source .venv/bin/activate` dengan `.venv\Scripts\Activate.ps1` dan `cp` dengan `copy`.

Variabel `.env`:

| Variabel | Contoh | Wajib |
|---|---|---|
| `GROQ_API_KEY` | (key dari console Groq) | Ya, untuk `LLM_MODE=groq` |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Tidak (default) |
| `LLM_MODE` | `groq` atau `fake` | Tidak (default `groq`) |

## Quick Start (pipeline lengkap)

```bash
python -m telconet_sentinel.data_gen.telemetry --seed 42 --overwrite
python -m telconet_sentinel.data_gen.sop --overwrite
python -m telconet_sentinel.ml.train
python -m telconet_sentinel.rag.ingest
python -m telconet_sentinel.eval.evaluate_agents --n 10
streamlit run src/telconet_sentinel/dashboard/app.py
```

## Test & Quality Gate

```bash
LLM_MODE=fake pytest -q            # seluruh test, offline
pytest tests/test_judge.py -q      # satu modul
ruff check src tests               # lint
```

Definisi "task selesai": command verifikasi task di `specs/tasks.md` lulus **dan** `ruff check src tests` bersih **dan** `LLM_MODE=fake pytest -q` tetap hijau.

## Peta Kode

| Path | Tanggung jawab |
|---|---|
| `src/telconet_sentinel/config.py` | Settings & path |
| `src/telconet_sentinel/schemas.py` | Skema Pydantic (telemetri, GeneratorOutput, JudgeOutput, RcaResult) |
| `src/telconet_sentinel/data_gen/` | Modul 1: generator telemetri, aturan label, generator SOP |
| `src/telconet_sentinel/ml/` | Modul 2: fitur, training, prediksi |
| `src/telconet_sentinel/rag/` | Modul 3: chunking, ingest Chroma, retriever |
| `src/telconet_sentinel/agents/` | Modul 3: LLM client, prompt, konteks, Generator, Judge, orchestrator |
| `src/telconet_sentinel/eval/` | Modul 3: evaluasi batch agen |
| `src/telconet_sentinel/dashboard/` | Modul 4: Streamlit |
| `data/` | CSV, SOP, Chroma, artefak model & metrik, log RCA |
| `tests/` | pytest (offline, `LLM_MODE=fake`) |

## Hal yang Tidak Boleh Dilakukan

- Menambah dependensi besar di luar `requirements.txt` tanpa menjelaskan alasannya ke user.
- Mengganti RandomForest, ChromaDB, Groq, atau Streamlit dengan alternatif lain (stack ini wajib).
- Menaikkan `MAX_ITERATIONS` di atas 2 atau menurunkan `APPROVAL_THRESHOLD` untuk "membuat angka bagus".
- Menulis hasil metrik ke README sebelum metrik itu benar-benar dihasilkan.
