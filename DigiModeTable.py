#!/usr/bin/env python3

#!/usr/bin/env python3

import os
import time
from datetime import datetime
from collections import defaultdict

# CONFIGURATION
ALL = False  # If True, processes entire file once
DATE = ""    # If ALL is False, uses this date; if empty, uses today
INTERVAL = 30  # Set to 0 for one-shot mode, or seconds for continuous
FILENAME = "wsjtx_log.adi"

# Auto path detection
if os.name == 'nt':
    FILE_PATH = r"D:\Ken\HamRadio"
else:
    FILE_PATH = os.path.expanduser("~/.local/share/WSJT-X")

# Modes and Submodes to include
VALID_MODES = {"FT8", "FT4"}

def parse_adi(filepath):
    with open(filepath, encoding="utf-8", errors="ignore") as f:
        content = f.read()
    entries = content.split("<eor>")
    qsos = []
    for entry in entries:
        if "<call:" not in entry:
            continue
        qso = {}
        fields = entry.strip().split("<")[1:]
        for field in fields:
            if ":" not in field:
                continue
            try:
                tag_len, val = field.split(">", 1)
                tag = tag_len.split(":")[0].lower()
                qso[tag] = val.strip()
            except Exception:
                continue
        qsos.append(qso)
    return qsos

def format_table(counts, highlight=None):
    bands = sorted({band for band_counts in counts.values() for band in band_counts})
    highlight_band = highlight[1] if highlight else None

    # Prepare headers and rows
    header = ["Mode"]
    rows = []

    for band in bands:
        header.append(f"{band:>5}")

    for mode in sorted(counts):
        row = [mode]
        for band in bands:
            val = counts[mode].get(band, 0)
            if highlight and (mode, band) == highlight:
                row.append(f"* {val:>3}")
            else:
                row.append(f"{val:>5}")
        rows.append(row)

    # Compute column widths based on actual string widths
    col_widths = [max(len(cell) for cell in col) for col in zip(*([header] + rows))]
    table_lines = []

    def fmt_line(row):
        return "| " + " | ".join(f"{cell:>{w}}" for cell, w in zip(row, col_widths)) + " |"

    table_lines.append("=" * (sum(col_widths) + 3 * len(col_widths) + 1))
    table_lines.append(fmt_line(header))
    table_lines.append("+" + "+".join("-" * (w + 2) for w in col_widths) + "+")
    for row in rows:
        table_lines.append(fmt_line(row))
    table_lines.append("=" * (sum(col_widths) + 3 * len(col_widths) + 1))
    return "\n".join(table_lines)

def summarize_qsos(qsos, target_date=None):
    counts = defaultdict(lambda: defaultdict(int))
    hourly_qsos = defaultdict(int)
    most_recent = None
    latest_time = None

    for qso in qsos:
        date = qso.get("qso_date")
        time_on = qso.get("time_on")
        band = qso.get("band")
        mode = qso.get("mode", "").upper()
        submode = qso.get("submode", "").upper()

        if target_date and date != target_date:
            continue

        if submode in VALID_MODES:
            mode = submode
        elif mode not in VALID_MODES:
            continue

        counts[mode][band] += 1

        if time_on and len(time_on) >= 2:
            hour = time_on[:2]
            hourly_qsos[hour] += 1

        if INTERVAL > 0 and date:
            dt_str = f"{date} {time_on}"
            try:
                dt = datetime.strptime(dt_str, "%Y%m%d %H%M%S")
                if not latest_time or dt > latest_time:
                    latest_time = dt
                    most_recent = (mode, band)
            except:
                pass

    return counts, hourly_qsos, most_recent

def main():
    filepath = os.path.join(FILE_PATH, FILENAME)
    if not os.path.isfile(filepath):
        print(f"File not found: {filepath}")
        return

    def determine_date():
        if ALL:
            return None
        return DATE if DATE else datetime.utcnow().strftime("%Y%m%d")

    while True:
        qsos = parse_adi(filepath)
        target_date = determine_date()
        counts, hourly_qsos, highlight = summarize_qsos(qsos, target_date)

        label = "ENTIRE LOG" if ALL else f"{datetime.strptime(target_date, '%Y%m%d').date()}"
        print(f"\nQSO Summary for {label}")
        print(format_table(counts, highlight=highlight))

        if not ALL:
            current_hour = datetime.utcnow().strftime("%H")
            count_last_hour = hourly_qsos.get(current_hour, 0)
            print("Hourly QSO Count (UTC):")
            print(f"QSOs in the last 60 minutes: {count_last_hour}")
            print("=" * 60)

        if INTERVAL <= 0:
            break
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
