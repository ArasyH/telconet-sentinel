---
sop_id: SOP-OLT-002
domain: OLT
applies_to: ['OLT']
synthetic: true
---
# SOP-OLT-002 — Penanganan CPU Tinggi pada OLT

> **Dokumen sintetis** — dibuat untuk proyek portofolio TelcoNet-Sentinel. Bukan SOP resmi operator atau vendor mana pun.

## Gejala

- `cpu_load_pct` OLT ≥ 85% (Warning) atau ≥ 95% (Critical).
- Response time CLI/SNMP OLT melambat.
- Potensi packet drop pada control plane.

## Ambang Pemicu

| Kondisi | Ambang |
|---------|--------|
| cpu_load_pct ≥ 85% | Warning |
| cpu_load_pct ≥ 95% | Critical |

## Diagnosis

Step 1: Login ke CLI OLT, jalankan perintah `show process cpu` untuk identifikasi proses tertinggi.
Step 2: Cek apakah ada flooding ARP/MAC atau storm control yang aktif.
Step 3: Cek jumlah sesi SNMP polling; polling berlebihan dapat meningkatkan CPU.
Step 4: Cek log OLT untuk error atau exception yang berkorelasi dengan lonjakan CPU.

## Tindakan

Step 1: Kurangi interval SNMP polling dari NMS untuk OLT tersebut menjadi ≥ 5 menit.
Step 2: Nonaktifkan fitur debugging atau tracing yang mungkin aktif secara tidak sengaja.
Step 3: Terapkan rate-limiting ARP pada port yang terindikasi flooding.
Step 4: Jadwalkan cold reboot OLT di luar jam sibuk jika CPU tetap > 90% selama 30 menit.
Step 5: Upgrade firmware OLT jika ada patch untuk bug CPU spike yang diketahui.

## Eskalasi

Eskalasi ke Network Engineering jika CPU > 95% dan reboot tidak menyelesaikan masalah; lakukan capacity planning untuk mengurangi beban OLT.
