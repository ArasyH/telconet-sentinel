---
sop_id: SOP-CORE-001
domain: CORE
applies_to: ['CORE_ROUTER']
synthetic: true
---
# SOP-CORE-001 — Penanganan Kongesti Link Core

> **Dokumen sintetis** — dibuat untuk proyek portofolio TelcoNet-Sentinel. Bukan SOP resmi operator atau vendor mana pun.

## Gejala

- `packet_loss_pct` Core Router ≥ 1% (Warning) atau ≥ 5% (Critical).
- `latency_ms` ≥ 60 ms (Warning) atau ≥ 150 ms (Critical).
- Utilisasi interface core > 80% pada traffic report.

## Ambang Pemicu

| Kondisi | Ambang |
|---------|--------|
| packet_loss_pct ≥ 1% OR latency_ms ≥ 60 ms | Warning |
| packet_loss_pct ≥ 5% OR latency_ms ≥ 150 ms | Critical |

## Diagnosis

Step 1: Cek utilisasi link core di traffic monitoring (target < 70% sustained).
Step 2: Identifikasi top-talker/flow menggunakan NetFlow atau sFlow.
Step 3: Verifikasi routing table; pastikan tidak ada loop atau flapping.
Step 4: Cek QoS queue statistics untuk drop per class-of-service.

## Tindakan

Step 1: Redirect traffic menggunakan traffic engineering / policy routing ke link alternatif.
Step 2: Terapkan rate-limit pada top-talker yang melebihi SLA bandwidth.
Step 3: Aktifkan ECMP jika tersedia link paralel dengan kapasitas serupa.
Step 4: Koordinasi dengan tim IP Planning untuk augmentasi kapasitas link jika utilisasi > 85% sustained.
Step 5: Implementasikan shaping pada traffic non-real-time untuk membebaskan kapasitas.

## Eskalasi

Eskalasi ke tim IP Transport jika utilisasi link > 90% dan tidak ada link alternatif; buka tiket capacity planning dengan timeline < 30 hari.
