# Requirements — TelcoNet-Sentinel

**Nama lengkap:** TelcoNet-Sentinel: OSS Network Anomaly Prediction & Self-Verified Agentic RCA Assistant
**Tujuan:** MVP portofolio (target: Divisi Digital Product / DDP Telkom Indonesia) yang bisa dibangun dalam 1 hari kerja dan dijalankan sepenuhnya di laptop, kecuali panggilan LLM ke provider eksternal (Groq atau OpenRouter).
**Format:** EARS (Easy Approach to Requirements Syntax).

---

## 0. Konvensi & Batasan

### 0.1 Pola EARS yang dipakai

| Pola | Template |
|---|---|
| Ubiquitous | THE SYSTEM SHALL `<response>` |
| Event-driven | WHEN `<trigger>` THE SYSTEM SHALL `<response>` |
| State-driven | WHILE `<state>` THE SYSTEM SHALL `<response>` |
| Unwanted behaviour | IF `<kondisi tidak diinginkan>` THEN THE SYSTEM SHALL `<response>` |
| Optional feature | WHERE `<fitur aktif>` THE SYSTEM SHALL `<response>` |

ID requirement: `REQ-<modul>.<nomor>`. Setiap task di `specs/tasks.md` wajib merujuk minimal satu ID ini.

### 0.2 Fakta, keputusan desain, dan asumsi

- **Fakta (dari permintaan user):** stack wajib Python 3.10+, Scikit-Learn RandomForest, LLM provider eksternal (Groq sebagai default, OpenRouter sebagai alternatif), pola Generator–Critic/Judge maks 2 iterasi, ChromaDB lokal, Streamlit.
- **Keputusan desain (dibuat di spec ini, boleh diubah):** model default `llama-3.3-70b-versatile` (dapat diganti via env var), ambang batas label sintetis, ambang skor `APPROVED` (≥ 80), jumlah baris data, nama region, isi SOP.
- **Asumsi yang WAJIB diverifikasi saat implementasi (belum dicek):**
  - A1. Model yang dikonfigurasi tersedia di provider yang dipilih (`LLM_MODE`). **Diverifikasi Nov 2026:** `llama-3.3-70b-versatile` sudah **deprecated di Groq** — model default Groq diganti ke `qwen/qwen3.8-27b` (ctx=131k, JSON mode ✓). Default OpenRouter tetap `meta-llama/llama-3.3-70b-instruct` (ctx=131k, JSON mode ✓). Ganti model via `GROQ_MODEL` / `OPENROUTER_MODEL` tanpa ubah kode.
  - A2. Groq `qwen/qwen3.8-27b` mendukung JSON mode (`response_format={"type": "json_object"}`). OpenRouter meneruskan parameter ini ke model yang mendukung; beberapa model (mis. Claude) dapat membungkus JSON dalam markdown — `_strip_markdown_json()` di `llm_client.py` menangani ini secara otomatis.
  - A3. Fungsi embedding default ChromaDB berjalan lokal (model ONNX kecil yang diunduh sekali saat pertama dipakai). Unduhan pertama butuh internet.
  - A4. Versi library terbaru kompatibel dengan Python 3.10+. Versi persis dikunci di `requirements.txt` setelah instalasi pertama berhasil, bukan ditebak di spec.
  - A5. Batas rate limit / kuota free tier Groq cukup untuk evaluasi batch kecil (≤ 20 kasus). Belum diverifikasi.
  - A6. OpenRouter mendukung OpenAI-compatible API (`/chat/completions` endpoint) sehingga dapat dipakai via `openai` Python SDK dengan `base_url="https://openrouter.ai/api/v1"`. Perlu diverifikasi bahwa model yang dipilih tersedia dan kuota free tier mencukupi evaluasi batch.

### 0.3 Batasan kejujuran data (wajib untuk portofolio)

- **REQ-0.1** THE SYSTEM SHALL menandai seluruh data telemetri dan dokumen SOP sebagai **sintetis** di README, dashboard, dan header setiap file SOP.
- **REQ-0.2** THE SYSTEM SHALL tidak mengklaim bahwa dokumen SOP, ambang batas, atau topologi merupakan milik / standar internal Telkom Indonesia.
- **REQ-0.3** THE SYSTEM SHALL menyimpan API key hanya di file `.env` yang masuk `.gitignore`.

---

## Modul 1 — Synthetic Telco Telemetry & SOP Data Generator

- **REQ-1.1** WHEN user menjalankan `python -m telconet_sentinel.data_gen.telemetry` THE SYSTEM SHALL menghasilkan file `data/raw/telemetry.csv` sesuai skema di `specs/design.md` §3.
- **REQ-1.2** THE SYSTEM SHALL menghasilkan data secara deterministik berdasarkan parameter `--seed` (default `42`), sehingga dua kali eksekusi dengan seed sama menghasilkan file identik.
- **REQ-1.3** THE SYSTEM SHALL menghasilkan default 50 perangkat × 288 timestamp (interval 5 menit, 24 jam) = 14.400 baris, dapat diubah via `--devices` dan `--steps`.
- **REQ-1.4** THE SYSTEM SHALL menghasilkan tiga `device_type`: `OLT`, `ONT`, `CORE_ROUTER`, dan lima `region`: `JAKARTA`, `BANDUNG`, `SURABAYA`, `MEDAN`, `MAKASSAR`.
- **REQ-1.5** THE SYSTEM SHALL menyuntikkan skenario gangguan sintetis (fiber degradation, congestion, overheating, CPU spike) sehingga distribusi kelas mendekati Normal ≈ 80%, Warning ≈ 14%, Critical ≈ 6% (toleransi ±3 poin persentase).
- **REQ-1.6** THE SYSTEM SHALL menentukan `anomaly_status` dengan aturan ambang batas yang tertulis di `specs/design.md` §3.2, lalu membalik label sebanyak 2% baris secara acak (label noise) agar model tidak sekadar menghafal aturan.
- **REQ-1.7** WHEN user menjalankan `python -m telconet_sentinel.data_gen.sop` THE SYSTEM SHALL menulis minimal 6 dokumen SOP Markdown sintetis ke `data/sop/` yang mencakup domain FTTH/ONT, OLT, dan Core.
- **REQ-1.8** THE SYSTEM SHALL memberi setiap dokumen SOP sebuah `sop_id` unik (format `SOP-<DOMAIN>-<NNN>`) dan setiap langkah tindakan nomor langkah (`Step 1`, `Step 2`, …) agar dapat dikutip oleh agen.
- **REQ-1.9** IF file output sudah ada THEN THE SYSTEM SHALL menimpanya hanya jika flag `--overwrite` diberikan, dan sebaliknya keluar dengan pesan error yang jelas tanpa mengubah file.
- **REQ-1.10** THE SYSTEM SHALL memvalidasi CSV hasil generate (kolom lengkap, tidak ada nilai null, rentang nilai sesuai `specs/design.md` §3.1) sebelum menulis file.

---

## Modul 2 — Predictive Anomaly Model

- **REQ-2.1** WHEN user menjalankan `python -m telconet_sentinel.ml.train` THE SYSTEM SHALL melatih `RandomForestClassifier` untuk memprediksi `anomaly_status` ∈ {`Normal`, `Warning`, `Critical`}.
- **REQ-2.2** THE SYSTEM SHALL memakai fitur numerik (`rx_optical_power_dbm`, `latency_ms`, `packet_loss_pct`, `cpu_load_pct`, `temperature_c`) ditambah `device_type` dan `region` yang di-one-hot-encode, di dalam satu `sklearn.pipeline.Pipeline`.
- **REQ-2.3** THE SYSTEM SHALL membagi data train/test berdasarkan `device_id` (group split, 80/20) untuk mencegah kebocoran data antar-timestamp dari perangkat yang sama.
- **REQ-2.4** THE SYSTEM SHALL memakai `class_weight="balanced"` dan `random_state=42`.
- **REQ-2.5** THE SYSTEM SHALL menyimpan model ke `data/artifacts/model.joblib` dan metrik ke `data/artifacts/ml_metrics.json` (macro-F1, recall per kelas, confusion matrix, feature importance).
- **REQ-2.6** THE SYSTEM SHALL memenuhi ambang kualitas MVP pada test set: macro-F1 ≥ 0.80 dan recall kelas `Critical` ≥ 0.85. Ambang ini adalah target desain, bukan klaim hasil.
- **REQ-2.7** IF metrik di bawah ambang REQ-2.6 THEN THE SYSTEM SHALL tetap menyimpan model, mencetak peringatan, dan menulis `"quality_gate": "FAILED"` di `ml_metrics.json`.
- **REQ-2.8** WHEN fungsi prediksi menerima satu atau banyak baris telemetri THE SYSTEM SHALL mengembalikan label prediksi beserta probabilitas tiap kelas.
- **REQ-2.9** IF input prediksi kehilangan kolom wajib THEN THE SYSTEM SHALL menolak input dengan error yang menyebut nama kolom yang hilang.
- **REQ-2.10** IF metrik test sempurna (macro-F1 = 1.0) THEN THE SYSTEM SHALL mencetak peringatan kemungkinan kebocoran label, karena label berasal dari aturan deterministik.

---

## Modul 3 — Agentic RAG with Judge & Critic Verification

### 3A. Ingest & Retrieval

- **REQ-3.1** WHEN user menjalankan `python -m telconet_sentinel.rag.ingest` THE SYSTEM SHALL memecah dokumen di `data/sop/` menjadi chunk per section/langkah dan menyimpannya ke koleksi ChromaDB persisten `sop_docs` di `data/chroma/`.
- **REQ-3.2** THE SYSTEM SHALL menyimpan metadata `sop_id`, `domain`, `section`, dan `source_file` di setiap chunk.
- **REQ-3.3** WHEN ingest dijalankan ulang THE SYSTEM SHALL menghasilkan jumlah chunk yang sama (idempoten, memakai ID chunk deterministik).
- **REQ-3.4** WHEN agen meminta konteks untuk satu insiden THE SYSTEM SHALL mengembalikan top-k chunk (default k = 4) yang difilter berdasarkan `domain` sesuai `device_type`.

### 3B. Generator Agent

- **REQ-3.5** WHEN user memicu RCA untuk satu perangkat berstatus prediksi `Warning` atau `Critical` THE SYSTEM SHALL membangun konteks insiden berisi ringkasan telemetri 12 timestamp terakhir, hasil prediksi ML + probabilitas, dan chunk SOP hasil retrieval.
- **REQ-3.6** THE SYSTEM SHALL meminta Generator Agent menghasilkan JSON sesuai skema `GeneratorOutput` (`specs/design.md` §4.1) berisi root cause, bukti telemetri, action plan, dan kutipan `sop_id` + nomor langkah.
- **REQ-3.7** THE SYSTEM SHALL menginstruksikan Generator untuk hanya merekomendasikan tindakan yang ada di chunk SOP yang diberikan, dan menulis `"INSUFFICIENT_SOP_CONTEXT"` jika tidak ada SOP yang relevan.

### 3C. Judge/Critic Agent

- **REQ-3.8** WHEN Generator menghasilkan draft THE SYSTEM SHALL mengirim draft, konteks telemetri, dan chunk SOP yang sama ke Judge Agent.
- **REQ-3.9** THE SYSTEM SHALL meminta Judge mengembalikan JSON sesuai skema `JudgeOutput` (`specs/design.md` §4.2) dengan `sop_faithfulness_score` bilangan bulat 1–100 dan `verdict` ∈ {`APPROVED`, `REVISION_NEEDED`}.
- **REQ-3.10** THE SYSTEM SHALL menjalankan pemeriksaan deterministik (non-LLM) sebelum Judge: setiap `sop_id` + langkah yang dikutip harus ada di chunk yang di-retrieve. Kutipan yang tidak ada dicatat sebagai `invalid_citations`.
- **REQ-3.11** IF `invalid_citations` tidak kosong THEN THE SYSTEM SHALL memaksa `verdict = REVISION_NEEDED` apa pun skor dari Judge.
- **REQ-3.12** THE SYSTEM SHALL menetapkan `verdict = APPROVED` hanya jika `sop_faithfulness_score ≥ 80` dan tidak ada `invalid_citations`.

### 3D. Loop Orkestrasi

- **REQ-3.13** WHEN `verdict = REVISION_NEEDED` dan iterasi < 2 THE SYSTEM SHALL mengirim `revision_instructions` dari Judge ke Generator untuk membuat draft revisi.
- **REQ-3.14** THE SYSTEM SHALL membatasi loop maksimal 2 iterasi (1 iterasi = 1 draft Generator + 1 penilaian Judge).
- **REQ-3.15** IF setelah iterasi ke-2 verdict masih `REVISION_NEEDED` THEN THE SYSTEM SHALL mengembalikan draft terakhir dengan `final_status = "UNVERIFIED_ESCALATE_TO_HUMAN"` dan dashboard SHALL menampilkannya dengan peringatan, bukan sebagai rekomendasi final.
- **REQ-3.16** THE SYSTEM SHALL mencatat setiap iterasi (draft, skor, verdict, alasan, latensi, jumlah token jika tersedia dari respons API) ke `data/logs/rca_runs.jsonl`.
- **REQ-3.17** IF respons LLM bukan JSON valid atau gagal validasi skema THEN THE SYSTEM SHALL mencoba ulang sekali dengan pesan perbaikan, lalu jika tetap gagal menandai run sebagai `ERROR` tanpa crash.
- **REQ-3.18** IF API key yang diperlukan (berdasarkan `LLM_MODE`) tidak tersedia, atau terjadi API error / timeout (30 detik), THEN THE SYSTEM SHALL menampilkan pesan error yang jelas dan dashboard tetap berjalan untuk modul 1–2. Pesan error harus menyebut provider mana yang gagal dan cara mengaturnya.
- **REQ-3.19** WHERE `LLM_MODE=fake` THE SYSTEM SHALL memakai LLM palsu deterministik (respons JSON tetap) sehingga seluruh test berjalan tanpa API key dan tanpa internet.
- **REQ-3.24** WHERE `LLM_MODE=openrouter` THE SYSTEM SHALL mengirim permintaan ke OpenRouter API menggunakan OpenAI-compatible SDK (`base_url` OpenRouter, `OPENROUTER_API_KEY` sebagai bearer token) sehingga pergantian provider tidak mengubah logika Generator/Judge/Orchestrator.
- **REQ-3.25** THE SYSTEM SHALL membaca model yang dipakai dari env var sesuai provider: `GROQ_MODEL` untuk `LLM_MODE=groq`, `OPENROUTER_MODEL` untuk `LLM_MODE=openrouter`. Nilai default masing-masing didefinisikan di `config.py`.
- **REQ-3.26** IF `LLM_MODE` berisi nilai selain `groq`, `openrouter`, atau `fake` THEN THE SYSTEM SHALL gagal dengan pesan error konfigurasi yang eksplisit saat startup, bukan saat panggilan LLM pertama.
- **REQ-3.20** THE SYSTEM SHALL memakai `temperature = 0.2` untuk Generator dan `temperature = 0.0` untuk Judge.

### 3E. Evaluasi Sistem Agen

- **REQ-3.21** WHEN user menjalankan `python -m telconet_sentinel.eval.evaluate_agents` THE SYSTEM SHALL menjalankan loop RCA pada set evaluasi tetap (default 10 insiden dari test set, seed 42) dan menulis `data/artifacts/agent_metrics.json`.
- **REQ-3.22** THE SYSTEM SHALL menghitung: approval rate iterasi-1, approval rate final, rata-rata `sop_faithfulness_score`, rata-rata jumlah iterasi, citation validity rate, escalation rate, dan latensi p50/p95.
- **REQ-3.23** THE SYSTEM SHALL mendokumentasikan di README bahwa skor faithfulness berasal dari LLM-as-judge dan bukan ground truth manusia.

---

## Modul 4 — Interactive Streamlit OSS Dashboard

- **REQ-4.1** WHEN user menjalankan `streamlit run src/telconet_sentinel/dashboard/app.py` THE SYSTEM SHALL menampilkan dashboard dengan 4 tab: **Network Overview**, **Anomaly Prediction**, **Agentic RCA**, **System Evaluation**.
- **REQ-4.2** THE SYSTEM SHALL menampilkan banner "Data sintetis — bukan data operasional Telkom" di setiap halaman.
- **REQ-4.3** WHILE tab Network Overview aktif THE SYSTEM SHALL menampilkan KPI ringkas (jumlah perangkat per status) dan grafik time-series metrik terpilih dengan filter `region`, `device_type`, dan `device_id`.
- **REQ-4.4** WHILE tab Anomaly Prediction aktif THE SYSTEM SHALL menampilkan tabel perangkat dengan prediksi terbaru, probabilitas tiap kelas, dan diurutkan dari probabilitas `Critical` tertinggi.
- **REQ-4.5** WHEN user memilih satu perangkat `Warning`/`Critical` dan menekan tombol "Run Agentic RCA" THE SYSTEM SHALL menjalankan loop REQ-3.13–3.15 dan menampilkan hasilnya.
- **REQ-4.6** THE SYSTEM SHALL menampilkan panel log Judge/Critic per iterasi: skor, verdict, daftar `issues`, `invalid_citations`, dan `revision_instructions`.
- **REQ-4.7** THE SYSTEM SHALL menampilkan action plan final beserta kutipan SOP (`sop_id` + langkah) dan badge status (`APPROVED` hijau, `UNVERIFIED_ESCALATE_TO_HUMAN` oranye, `ERROR` merah).
- **REQ-4.8** WHILE tab System Evaluation aktif THE SYSTEM SHALL menampilkan isi `ml_metrics.json` (macro-F1, recall per kelas, confusion matrix, feature importance) dan `agent_metrics.json`.
- **REQ-4.9** IF artefak model atau metrik belum ada THEN THE SYSTEM SHALL menampilkan instruksi command yang perlu dijalankan, bukan stack trace.
- **REQ-4.10** THE SYSTEM SHALL meng-cache pemuatan CSV dan model (`st.cache_data` / `st.cache_resource`) agar interaksi filter terasa < 2 detik pada data default (target, belum diukur).

---

## Non-Functional Requirements

- **NFR-1** THE SYSTEM SHALL dapat dijalankan dari environment yang sudah ter-setup (venv + dependensi + `.env`) hingga dashboard terbuka dengan ≤ 6 command pipeline (lihat "Quick Start" di `CLAUDE.md`).
- **NFR-2** THE SYSTEM SHALL lulus `pytest` dan `ruff check` tanpa error dengan `LLM_MODE=fake`.
- **NFR-3** THE SYSTEM SHALL memusatkan semua path, ambang batas, dan nama model di `src/telconet_sentinel/config.py` (dibaca dari `.env` bila ada).
- **NFR-4** THE SYSTEM SHALL memakai type hints dan validasi skema Pydantic untuk semua output LLM.
- **NFR-5** THE SYSTEM SHALL tidak memakai layanan cloud selain LLM provider yang dikonfigurasi (`LLM_MODE=groq` → Groq API; `LLM_MODE=openrouter` → OpenRouter API). Semua komponen lain (ChromaDB, ML model, dashboard) berjalan lokal.

---

## Out of Scope (MVP 1 hari)

- Integrasi ke sistem OSS/NMS nyata, SNMP, atau streaming real-time.
- Autentikasi user dashboard, multi-tenant, deployment ke cloud.
- Fine-tuning LLM, hyperparameter search ekstensif, model time-series (LSTM, dll.).
- Evaluasi faithfulness oleh anotator manusia (dicatat sebagai pekerjaan lanjutan di README).
