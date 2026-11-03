"""Synthetic SOP Markdown generator. [REQ-0.1, REQ-1.7, 1.8, 1.9]

Run:
    python -m telconet_sentinel.data_gen.sop --overwrite
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from telconet_sentinel.config import settings

DISCLAIMER = (
    "> **Dokumen sintetis** — dibuat untuk proyek portofolio TelcoNet-Sentinel. "
    "Bukan SOP resmi operator atau vendor mana pun.\n"
)

SOP_DOCS: list[dict] = [
    {
        "sop_id": "SOP-FTTH-001",
        "domain": "FTTH",
        "applies_to": ["ONT", "OLT"],
        "title": "Penanganan Redaman Optik Tinggi di Sisi ONT",
        "symptoms": (
            "- Nilai `rx_optical_power_dbm` ONT turun di bawah −25 dBm (Warning) "
            "atau −28 dBm (Critical).\n"
            "- Pelanggan melaporkan putus koneksi atau kecepatan rendah.\n"
            "- Packet loss meningkat bersamaan dengan penurunan rx power."
        ),
        "trigger": (
            "| Kondisi | Ambang |\n"
            "|---------|--------|\n"
            "| rx_optical_power_dbm ≤ −25 dBm | Warning |\n"
            "| rx_optical_power_dbm ≤ −28 dBm | Critical |"
        ),
        "diagnosis": [
            "Step 1: Baca nilai rx power real-time dari NMS/EMS untuk ONT yang bersangkutan.",
            "Step 2: Bandingkan dengan nilai baseline (−20 ± 3 dBm untuk ONT FTTH tipikal).",
            "Step 3: Cek apakah ada alarm fiber cut atau degradasi di segmen ODC–ODP terkait.",
            "Step 4: Verifikasi apakah perangkat ONT tetangga di splitter yang sama mengalami hal serupa.",
        ],
        "actions": [
            "Step 1: Lakukan remote restart ONT melalui NMS jika rx masih di atas −32 dBm.",
            "Step 2: Hubungi tim lapangan untuk inspeksi visual konektor SC/APC di ODP terdekat.",
            "Step 3: Bersihkan konektor SC/APC di ODP dan ONT dengan fiber cleaning kit.",
            "Step 4: Ukur loss dengan OTDR dari OLT port ke ONT; lokalisasi titik degradasi.",
            "Step 5: Ganti patch cord atau splice closure yang defek berdasarkan hasil OTDR.",
        ],
        "escalation": (
            "Eskalasi ke NOC Level 3 jika setelah Step 5 rx power masih di bawah −28 dBm, "
            "atau jika lebih dari 10 pelanggan terdampak di splitter yang sama."
        ),
    },
    {
        "sop_id": "SOP-FTTH-002",
        "domain": "FTTH",
        "applies_to": ["ONT", "OLT"],
        "title": "Penanganan Packet Loss Pelanggan FTTH",
        "symptoms": (
            "- `packet_loss_pct` ≥ 1% (Warning) atau ≥ 5% (Critical).\n"
            "- Pelanggan melaporkan koneksi tidak stabil atau video call terputus-putus."
        ),
        "trigger": (
            "| Kondisi | Ambang |\n"
            "|---------|--------|\n"
            "| packet_loss_pct ≥ 1% | Warning |\n"
            "| packet_loss_pct ≥ 5% | Critical |"
        ),
        "diagnosis": [
            "Step 1: Konfirmasi nilai packet loss dari counter NMS untuk port OLT terkait.",
            "Step 2: Cek apakah packet loss hanya pada satu ONT atau seluruh port di OLT card.",
            "Step 3: Periksa utilisasi bandwidth uplink OLT; kongesti dapat menyebabkan loss.",
            "Step 4: Lakukan ping test dari NMS ke IP management ONT sebanyak 100 paket.",
        ],
        "actions": [
            "Step 1: Jika loss terisolasi ke satu ONT, lakukan restart layanan via NMS.",
            "Step 2: Jika seluruh port OLT card terdampak, cek link uplink OLT ke aggregation switch.",
            "Step 3: Kurangi beban traffic dengan load-balancing antar OLT card jika tersedia.",
            "Step 4: Dispatch teknisi lapangan untuk cek kabel pigtail ONT dan konektor di ODP.",
            "Step 5: Ganti ONT jika hardware fault terdeteksi (LED indikator tidak normal).",
        ],
        "escalation": (
            "Eskalasi ke tim Transport jika packet loss berasal dari link uplink "
            "dengan utilisasi > 90%."
        ),
    },
    {
        "sop_id": "SOP-OLT-001",
        "domain": "OLT",
        "applies_to": ["OLT"],
        "title": "Penanganan Overheating Shelf OLT",
        "symptoms": (
            "- `temperature_c` OLT ≥ 65 °C (Warning) atau ≥ 75 °C (Critical).\n"
            "- Fan alarm aktif di NMS.\n"
            "- CPU load meningkat bersamaan dengan suhu."
        ),
        "trigger": (
            "| Kondisi | Ambang |\n"
            "|---------|--------|\n"
            "| temperature_c ≥ 65 °C | Warning |\n"
            "| temperature_c ≥ 75 °C | Critical |"
        ),
        "diagnosis": [
            "Step 1: Akses NMS dan baca suhu real-time semua card di shelf OLT tersebut.",
            "Step 2: Cek status fan unit; verifikasi apakah ada fan yang gagal berputar.",
            "Step 3: Cek suhu ruangan data center atau shelter tempat OLT terpasang.",
            "Step 4: Bandingkan suhu card dengan baseline operasional (45 ± 5 °C).",
        ],
        "actions": [
            "Step 1: Aktifkan pendingin tambahan di ruangan jika suhu ruangan > 30 °C.",
            "Step 2: Ganti fan unit yang rusak dengan spare part sesuai part number OLT.",
            "Step 3: Pindahkan beban traffic ke OLT lain di cluster yang sama jika memungkinkan.",
            "Step 4: Nonaktifkan card OLT yang paling panas secara bertahap jika suhu > 78 °C.",
            "Step 5: Hubungi vendor untuk RMA jika penggantian fan tidak menurunkan suhu.",
        ],
        "escalation": (
            "Eskalasi ke Facility Management jika suhu ruangan > 35 °C; "
            "eskalasi ke vendor jika suhu card > 80 °C setelah semua langkah dilakukan."
        ),
    },
    {
        "sop_id": "SOP-OLT-002",
        "domain": "OLT",
        "applies_to": ["OLT"],
        "title": "Penanganan CPU Tinggi pada OLT",
        "symptoms": (
            "- `cpu_load_pct` OLT ≥ 85% (Warning) atau ≥ 95% (Critical).\n"
            "- Response time CLI/SNMP OLT melambat.\n"
            "- Potensi packet drop pada control plane."
        ),
        "trigger": (
            "| Kondisi | Ambang |\n"
            "|---------|--------|\n"
            "| cpu_load_pct ≥ 85% | Warning |\n"
            "| cpu_load_pct ≥ 95% | Critical |"
        ),
        "diagnosis": [
            "Step 1: Login ke CLI OLT, jalankan perintah `show process cpu` untuk identifikasi proses tertinggi.",
            "Step 2: Cek apakah ada flooding ARP/MAC atau storm control yang aktif.",
            "Step 3: Cek jumlah sesi SNMP polling; polling berlebihan dapat meningkatkan CPU.",
            "Step 4: Cek log OLT untuk error atau exception yang berkorelasi dengan lonjakan CPU.",
        ],
        "actions": [
            "Step 1: Kurangi interval SNMP polling dari NMS untuk OLT tersebut menjadi ≥ 5 menit.",
            "Step 2: Nonaktifkan fitur debugging atau tracing yang mungkin aktif secara tidak sengaja.",
            "Step 3: Terapkan rate-limiting ARP pada port yang terindikasi flooding.",
            "Step 4: Jadwalkan cold reboot OLT di luar jam sibuk jika CPU tetap > 90% selama 30 menit.",
            "Step 5: Upgrade firmware OLT jika ada patch untuk bug CPU spike yang diketahui.",
        ],
        "escalation": (
            "Eskalasi ke Network Engineering jika CPU > 95% dan reboot tidak menyelesaikan masalah; "
            "lakukan capacity planning untuk mengurangi beban OLT."
        ),
    },
    {
        "sop_id": "SOP-CORE-001",
        "domain": "CORE",
        "applies_to": ["CORE_ROUTER"],
        "title": "Penanganan Kongesti Link Core",
        "symptoms": (
            "- `packet_loss_pct` Core Router ≥ 1% (Warning) atau ≥ 5% (Critical).\n"
            "- `latency_ms` ≥ 60 ms (Warning) atau ≥ 150 ms (Critical).\n"
            "- Utilisasi interface core > 80% pada traffic report."
        ),
        "trigger": (
            "| Kondisi | Ambang |\n"
            "|---------|--------|\n"
            "| packet_loss_pct ≥ 1% OR latency_ms ≥ 60 ms | Warning |\n"
            "| packet_loss_pct ≥ 5% OR latency_ms ≥ 150 ms | Critical |"
        ),
        "diagnosis": [
            "Step 1: Cek utilisasi link core di traffic monitoring (target < 70% sustained).",
            "Step 2: Identifikasi top-talker/flow menggunakan NetFlow atau sFlow.",
            "Step 3: Verifikasi routing table; pastikan tidak ada loop atau flapping.",
            "Step 4: Cek QoS queue statistics untuk drop per class-of-service.",
        ],
        "actions": [
            "Step 1: Redirect traffic menggunakan traffic engineering / policy routing ke link alternatif.",
            "Step 2: Terapkan rate-limit pada top-talker yang melebihi SLA bandwidth.",
            "Step 3: Aktifkan ECMP jika tersedia link paralel dengan kapasitas serupa.",
            "Step 4: Koordinasi dengan tim IP Planning untuk augmentasi kapasitas link jika utilisasi > 85% sustained.",
            "Step 5: Implementasikan shaping pada traffic non-real-time untuk membebaskan kapasitas.",
        ],
        "escalation": (
            "Eskalasi ke tim IP Transport jika utilisasi link > 90% dan tidak ada link alternatif; "
            "buka tiket capacity planning dengan timeline < 30 hari."
        ),
    },
    {
        "sop_id": "SOP-CORE-002",
        "domain": "CORE",
        "applies_to": ["CORE_ROUTER"],
        "title": "Penanganan Lonjakan Latensi Core Router",
        "symptoms": (
            "- `latency_ms` Core Router ≥ 60 ms (Warning) atau ≥ 150 ms (Critical).\n"
            "- Keluhan pengguna terkait lambatnya akses layanan real-time (VoIP, gaming)."
        ),
        "trigger": (
            "| Kondisi | Ambang |\n"
            "|---------|--------|\n"
            "| latency_ms ≥ 60 ms | Warning |\n"
            "| latency_ms ≥ 150 ms | Critical |"
        ),
        "diagnosis": [
            "Step 1: Jalankan traceroute dari core router ke destination yang terdampak.",
            "Step 2: Identifikasi hop dengan latensi tertinggi dalam path.",
            "Step 3: Cek CPU dan memory utilization pada hop yang bermasalah.",
            "Step 4: Verifikasi apakah ada maintenance window atau planned change yang sedang aktif.",
        ],
        "actions": [
            "Step 1: Reroute traffic melalui path alternatif jika tersedia (BGP local-preference / OSPF cost).",
            "Step 2: Clear BGP/OSPF neighbor jika flapping terdeteksi pada log.",
            "Step 3: Nonaktifkan fitur hardware yang menyebabkan latency (mis. deep packet inspection) secara sementara.",
            "Step 4: Turunkan MTU di interface yang mengalami fragmentasi berlebih.",
            "Step 5: Buka tiket eskalasi ke upstream provider jika latensi berasal dari link transit.",
        ],
        "escalation": (
            "Eskalasi ke NOC Level 3 dan tim IP Transport jika latensi > 200 ms selama > 5 menit; "
            "aktifkan prosedur major incident jika SLA pelanggan enterprise terdampak."
        ),
    },
]


def _render_sop(doc: dict) -> str:
    lines = [
        "---",
        f"sop_id: {doc['sop_id']}",
        f"domain: {doc['domain']}",
        f"applies_to: {doc['applies_to']}",
        "synthetic: true",
        "---",
        f"# {doc['sop_id']} — {doc['title']}",
        "",
        DISCLAIMER,
        "## Gejala",
        "",
        doc["symptoms"],
        "",
        "## Ambang Pemicu",
        "",
        doc["trigger"],
        "",
        "## Diagnosis",
        "",
    ]
    lines.extend(doc["diagnosis"])
    lines += ["", "## Tindakan", ""]
    lines.extend(doc["actions"])
    lines += [
        "",
        "## Eskalasi",
        "",
        doc["escalation"],
        "",
    ]
    return "\n".join(lines)


def write_sop_docs(sop_dir: Path, overwrite: bool) -> None:
    sop_dir.mkdir(parents=True, exist_ok=True)
    for doc in SOP_DOCS:
        path = sop_dir / f"{doc['sop_id']}.md"
        if path.exists() and not overwrite:
            print(f"ERROR: {path} already exists. Use --overwrite.", file=sys.stderr)
            sys.exit(1)
        path.write_text(_render_sop(doc), encoding="utf-8")
        print(f"Written {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic SOP Markdown docs")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    write_sop_docs(settings.sop_dir, args.overwrite)


if __name__ == "__main__":
    main()
