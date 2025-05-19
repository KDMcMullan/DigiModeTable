#!/usr/bin/env python3

import os
import platform
import time
from datetime import datetime, timedelta
from collections import defaultdict

# --- CONFIGURATION ---
ALL = False # Just one day
DATE = ""  # Format: "YYYYMMDD"; leave blank for today's date
INTERVAL = 30  # 0 = run once, >0 = run every INTERVAL seconds

# --- FILE PATH SETUP ---
if platform.system() == "Windows":
    FILE_PATH = r"D:\Ken\HamRadio\wsjtx_log.adi"
else:
    FILE_PATH = os.path.expanduser("~/.local/share/WSJTX/wsjtx_log.adi")

# --- HELPER FUNCTIONS ---
def parse_adi(filepath):
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.read().split("<eor>")
    qsos = []
    for entry in lines:
        qso = {}
        for part in entry.strip().split("<"):
            if ":" in part:
                keylen, val = part.split(">", 1)
                key = keylen.split(":")[0].lower()
                qso[key] = val.strip()
        if qso:
            qsos.append(qso)
    return qsos

def is_digimode(qso):
    mode = qso.get("mode", "").upper()
    submode = qso.get("submode", "").upper()
    return (mode == "FT8") or (submode == "FT4")

def get_qso_date(qso):
    return qso.get("qso_date", "")

def get_qso_hour(qso):
    return qso.get("time_on", "")[:2]

def print_summary(qsos, label=""):
    bands = sorted(set(qso.get("band", "").upper() for qso in qsos if qso.get("band")))
    bands = sorted(bands, key=lambda b: int(b[:-1]) if b[:-1].isdigit() else 0)
    modes = ["FT8", "FT4"]
    summary = defaultdict(lambda: defaultdict(int))
    hour_counts = defaultdict(int)

    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)

    for qso in qsos:
        mode = qso.get("mode", "").upper()
        submode = qso.get("submode", "").upper()
        band = qso.get("band", "").upper()
        qso_datetime_str = qso.get("qso_date", "") + qso.get("time_on", "")
        try:
            qso_time = datetime.strptime(qso_datetime_str, "%Y%m%d%H%M%S")
        except:
            continue
        if mode == "FT8":
            summary["FT8"][band] += 1
        elif submode == "FT4":
            summary["FT4"][band] += 1

        if one_hour_ago <= qso_time <= now:
            hour = qso_time.strftime("%H")
            hour_counts[hour] += 1

    # --- Print Table ---
    print("=" * 60)
    print(f"QSO Summary for {label}")
    print("=" * 60)
    if not summary:
        print("No FT8/FT4 QSOs found.")
        return

    header = f"| {'Mode':<4} |" + "".join([f" {b:>4} |" for b in bands])
    print(header)
    print("+" + "-" * (len(header) - 2) + "+")
    for mode in modes:
        row = f"| {mode:<4} |" + "".join([f" {summary[mode][b]:>4} |" for b in bands])
        print(row)
    print("=" * 60)

    print("QSOs in the last 60 minutes (UTC):", sum(hour_counts.values()))
    print("=" * 60)

# --- MAIN LOOP ---
def main():
    while True:
        qsos = parse_adi(FILE_PATH)
        filtered_qsos = []

        if ALL:
            filtered_qsos = [q for q in qsos if is_digimode(q)]
            label = "ENTIRE LOG"
        else:
            if DATE:
                date_filter = DATE
            else:
                date_filter = datetime.utcnow().strftime("%Y%m%d")
            filtered_qsos = [q for q in qsos if is_digimode(q) and get_qso_date(q) == date_filter]
            label = date_filter

        os.system("cls" if platform.system() == "Windows" else "clear")
        print_summary(filtered_qsos, label)

        if INTERVAL == 0:
            break
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
