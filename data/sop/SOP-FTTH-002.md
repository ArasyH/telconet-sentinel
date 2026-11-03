---
sop_id: SOP-FTTH-002
domain: FTTH
applies_to: ['ONT', 'OLT']
synthetic: true
---
# SOP-FTTH-002 — Penanganan Packet Loss Pelanggan FTTH

> **Dokumen sintetis** — dibuat untuk proyek portofolio TelcoNet-Sentinel. Bukan SOP resmi operator atau vendor mana pun.

## Gejala

- `packet_loss_pct` ≥ 1% (Warning) atau ≥ 5% (Critical).
- Pelanggan melaporkan koneksi tidak stabil atau video call terputus-putus.

## Ambang Pemicu

| Kondisi | Ambang |
|---------|--------|
| packet_loss_pct ≥ 1% | Warning |
| packet_loss_pct ≥ 5% | Critical |

## Diagnosis

Step 1: Konfirmasi nilai packet loss dari counter NMS untuk port OLT terkait.
Step 2: Cek apakah packet loss hanya pada satu ONT atau seluruh port di OLT card.
Step 3: Periksa utilisasi bandwidth uplink OLT; kongesti dapat menyebabkan loss.
Step 4: Lakukan ping test dari NMS ke IP management ONT sebanyak 100 paket.

## Tindakan

Step 1: Jika loss terisolasi ke satu ONT, lakukan restart layanan via NMS.
Step 2: Jika seluruh port OLT card terdampak, cek link uplink OLT ke aggregation switch.
Step 3: Kurangi beban traffic dengan load-balancing antar OLT card jika tersedia.
Step 4: Dispatch teknisi lapangan untuk cek kabel pigtail ONT dan konektor di ODP.
Step 5: Ganti ONT jika hardware fault terdeteksi (LED indikator tidak normal).

## Eskalasi

Eskalasi ke tim Transport jika packet loss berasal dari link uplink dengan utilisasi > 90%.
