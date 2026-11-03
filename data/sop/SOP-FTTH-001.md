---
sop_id: SOP-FTTH-001
domain: FTTH
applies_to: ['ONT', 'OLT']
synthetic: true
---
# SOP-FTTH-001 — Penanganan Redaman Optik Tinggi di Sisi ONT

> **Dokumen sintetis** — dibuat untuk proyek portofolio TelcoNet-Sentinel. Bukan SOP resmi operator atau vendor mana pun.

## Gejala

- Nilai `rx_optical_power_dbm` ONT turun di bawah −25 dBm (Warning) atau −28 dBm (Critical).
- Pelanggan melaporkan putus koneksi atau kecepatan rendah.
- Packet loss meningkat bersamaan dengan penurunan rx power.

## Ambang Pemicu

| Kondisi | Ambang |
|---------|--------|
| rx_optical_power_dbm ≤ −25 dBm | Warning |
| rx_optical_power_dbm ≤ −28 dBm | Critical |

## Diagnosis

Step 1: Baca nilai rx power real-time dari NMS/EMS untuk ONT yang bersangkutan.
Step 2: Bandingkan dengan nilai baseline (−20 ± 3 dBm untuk ONT FTTH tipikal).
Step 3: Cek apakah ada alarm fiber cut atau degradasi di segmen ODC–ODP terkait.
Step 4: Verifikasi apakah perangkat ONT tetangga di splitter yang sama mengalami hal serupa.

## Tindakan

Step 1: Lakukan remote restart ONT melalui NMS jika rx masih di atas −32 dBm.
Step 2: Hubungi tim lapangan untuk inspeksi visual konektor SC/APC di ODP terdekat.
Step 3: Bersihkan konektor SC/APC di ODP dan ONT dengan fiber cleaning kit.
Step 4: Ukur loss dengan OTDR dari OLT port ke ONT; lokalisasi titik degradasi.
Step 5: Ganti patch cord atau splice closure yang defek berdasarkan hasil OTDR.

## Eskalasi

Eskalasi ke NOC Level 3 jika setelah Step 5 rx power masih di bawah −28 dBm, atau jika lebih dari 10 pelanggan terdampak di splitter yang sama.
