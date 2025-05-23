#!/usr/bin/env python3

import os
import time
from datetime import datetime, timedelta
from collections import defaultdict

# CONFIGURATION
ALL = False          # If True, processes entire file once
DATE = ""            # If populated, filters by this date (YYYYMMDD) in one-shot mode
INTERVAL = 30        # Interval (in seconds) for continuous mode; 0 = one-shot
HOURLY_WINDOW = 60   # QSO count window in minutes for recent activity display
FILENAME = "wsjtx_log.adi"

# Auto path detection
if os.name == 'nt':
    FILE_PATH = r"D:\Ken\HamRadio"
else:
    FILE_PATH = os.path.expanduser("~/.local/share/WSJTX")

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

    # Column widths
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

def summarize_qsos(qsos, time_threshold=None, target_date=None, highlight_enabled=True):
    counts = defaultdict(lambda: defaultdict(int))
    hourly_qsos = defaultdict(int)
    most_recent = None
    latest_time = None
    recent_cutoff = datetime.utcnow() - timedelta(minutes=HOURLY_WINDOW)

    for qso in qsos:
        date = qso.get("qso_date")
        time_on = qso.get("time_on")
        band = qso.get("band")
        mode = qso.get("mode", "").upper()
        submode = qso.get("submode", "").upper()

        if not date or not time_on or len(time_on) < 6:
            continue

        dt_str = f"{date} {time_on}"
        try:
            dt = datetime.strptime(dt_str, "%Y%m%d %H%M%S")
        except ValueError:
            continue

        if time_threshold and dt < time_threshold:
            continue
        if target_date and date != target_date:
            continue

        if submode in VALID_MODES:
            mode = submode
        elif mode not in VALID_MODES:
            continue

        counts[mode][band] += 1

        if dt >= recent_cutoff:
            hour = dt.strftime("%H")
            hourly_qsos[hour] += 1

        if highlight_enabled and (not latest_time or dt > latest_time):
            latest_time = dt
            most_recent = (mode, band)

    return counts, hourly_qsos, most_recent

def main():
    filepath = os.path.join(FILE_PATH, FILENAME)
    if not os.path.isfile(filepath):
        print(f"File not found: {filepath}")
        return

    # Determine operating mode
    one_shot = ALL or DATE != ""
    highlight_enabled = not ALL
    time_threshold = None
    target_date = None

    if ALL:
        label = "ENTIRE LOG"
    elif DATE:
        label = f"{datetime.strptime(DATE, '%Y%m%d').date()}"
        target_date = DATE
    else:
        label = "Last 24 hours"
        time_threshold = datetime.utcnow() - timedelta(hours=24)

    def report():
        qsos = parse_adi(filepath)
        counts, hourly_qsos, highlight = summarize_qsos(
            qsos, time_threshold=time_threshold,
            target_date=target_date,
            highlight_enabled=highlight_enabled
        )

        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        print(f"\nQSO Summary at {timestamp} ({label})")
        print(format_table(counts, highlight if highlight_enabled else None))

        if not ALL:
            current_hour = datetime.utcnow().strftime("%H")
            count_last_hour = hourly_qsos.get(current_hour, 0)
            print(f"QSOs in the last {HOURLY_WINDOW} minutes: {count_last_hour}")
            print("=" * 60)

    if one_shot or INTERVAL <= 0:
        report()
    else:
        while True:
            report()
            time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
