---
sop_id: SOP-CORE-002
domain: CORE
applies_to: ['CORE_ROUTER']
synthetic: true
---
# SOP-CORE-002 — Penanganan Lonjakan Latensi Core Router

> **Dokumen sintetis** — dibuat untuk proyek portofolio TelcoNet-Sentinel. Bukan SOP resmi operator atau vendor mana pun.

## Gejala

- `latency_ms` Core Router ≥ 60 ms (Warning) atau ≥ 150 ms (Critical).
- Keluhan pengguna terkait lambatnya akses layanan real-time (VoIP, gaming).

## Ambang Pemicu

| Kondisi | Ambang |
|---------|--------|
| latency_ms ≥ 60 ms | Warning |
| latency_ms ≥ 150 ms | Critical |

## Diagnosis

Step 1: Jalankan traceroute dari core router ke destination yang terdampak.
Step 2: Identifikasi hop dengan latensi tertinggi dalam path.
Step 3: Cek CPU dan memory utilization pada hop yang bermasalah.
Step 4: Verifikasi apakah ada maintenance window atau planned change yang sedang aktif.

## Tindakan

Step 1: Reroute traffic melalui path alternatif jika tersedia (BGP local-preference / OSPF cost).
Step 2: Clear BGP/OSPF neighbor jika flapping terdeteksi pada log.
Step 3: Nonaktifkan fitur hardware yang menyebabkan latency (mis. deep packet inspection) secara sementara.
Step 4: Turunkan MTU di interface yang mengalami fragmentasi berlebih.
Step 5: Buka tiket eskalasi ke upstream provider jika latensi berasal dari link transit.

## Eskalasi

Eskalasi ke NOC Level 3 dan tim IP Transport jika latensi > 200 ms selama > 5 menit; aktifkan prosedur major incident jika SLA pelanggan enterprise terdampak.
