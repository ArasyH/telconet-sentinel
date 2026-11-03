---
sop_id: SOP-OLT-001
domain: OLT
applies_to: ['OLT']
synthetic: true
---
# SOP-OLT-001 — Penanganan Overheating Shelf OLT

> **Dokumen sintetis** — dibuat untuk proyek portofolio TelcoNet-Sentinel. Bukan SOP resmi operator atau vendor mana pun.

## Gejala

- `temperature_c` OLT ≥ 65 °C (Warning) atau ≥ 75 °C (Critical).
- Fan alarm aktif di NMS.
- CPU load meningkat bersamaan dengan suhu.

## Ambang Pemicu

| Kondisi | Ambang |
|---------|--------|
| temperature_c ≥ 65 °C | Warning |
| temperature_c ≥ 75 °C | Critical |

## Diagnosis

Step 1: Akses NMS dan baca suhu real-time semua card di shelf OLT tersebut.
Step 2: Cek status fan unit; verifikasi apakah ada fan yang gagal berputar.
Step 3: Cek suhu ruangan data center atau shelter tempat OLT terpasang.
Step 4: Bandingkan suhu card dengan baseline operasional (45 ± 5 °C).

## Tindakan

Step 1: Aktifkan pendingin tambahan di ruangan jika suhu ruangan > 30 °C.
Step 2: Ganti fan unit yang rusak dengan spare part sesuai part number OLT.
Step 3: Pindahkan beban traffic ke OLT lain di cluster yang sama jika memungkinkan.
Step 4: Nonaktifkan card OLT yang paling panas secara bertahap jika suhu > 78 °C.
Step 5: Hubungi vendor untuk RMA jika penggantian fan tidak menurunkan suhu.

## Eskalasi

Eskalasi ke Facility Management jika suhu ruangan > 35 °C; eskalasi ke vendor jika suhu card > 80 °C setelah semua langkah dilakukan.
