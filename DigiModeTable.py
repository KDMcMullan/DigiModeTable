#!/usr/bin/env python3

import os
import time
from datetime import datetime, timedelta, timezone
from collections import defaultdict

# CONFIGURATION
ALL = True       # If True, processes entire file once
DATE = ""        # If ALL is False and this is set, uses this date only
INTERVAL = 30    # Seconds for continuous mode; set to 0 for one-shot
HOUR_WINDOW = 60  # For recent QSO summary (e.g., 60 minutes)
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

def summarize_qsos(qsos, target_date=None, window_hours=None, include_highlight=True):
    counts = defaultdict(lambda: defaultdict(int))
    hourly_qsos = defaultdict(int)
    most_recent = None
    latest_time = None

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=window_hours) if window_hours else None

    for qso in qsos:
        date = qso.get("qso_date")
        time_on = qso.get("time_on")
        band = qso.get("band")
        mode = qso.get("mode", "").upper()
        submode = qso.get("submode", "").upper()

        try:
            dt = datetime.strptime(f"{date} {time_on}", "%Y%m%d %H%M%S").replace(tzinfo=timezone.utc)
        except:
            continue

        # Apply filtering rules
        if target_date:
            if date != target_date:
                continue
        elif window_start:
            if dt < window_start:
                continue

        if submode in VALID_MODES:
            mode = submode
        elif mode not in VALID_MODES:
            continue

        counts[mode][band] += 1
        hourly_qsos[dt.strftime("%H")] += 1

        if include_highlight:
            if not latest_time or dt > latest_time:
                latest_time = dt
                most_recent = (mode, band)

    return counts, hourly_qsos, most_recent

def main():
    filepath = os.path.join(FILE_PATH, FILENAME)
    if not os.path.isfile(filepath):
        print(f"File not found: {filepath}")
        return

    def determine_mode():
        if ALL or DATE:
            return "oneshot"
        return "interval"

    mode = determine_mode()
    target_date = DATE if DATE else None
    include_highlight = (mode == "interval")

    while True:
        qsos = parse_adi(filepath)
        window_hours = 24 if not ALL and not DATE else None
        counts, hourly_qsos, highlight = summarize_qsos(
            qsos, 
            target_date=target_date,
            window_hours=window_hours,
            include_highlight=include_highlight
        )

        if ALL:
            label = "ENTIRE LOG"
        elif DATE:
            label = f"{DATE} (static)"
        else:
            label = "last 24 hours"

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        print(f"\nQSO Summary for {label} @ {timestamp} UTC")
        print(format_table(counts, highlight=highlight))

        if mode == "interval":
            current_hour = datetime.now(timezone.utc).strftime("%H")
            count_last_hour = hourly_qsos.get(current_hour, 0)
            print(f"QSOs in the last {HOUR_WINDOW} minutes: {count_last_hour}")
            print("=" * 60)

        if mode == "oneshot" or INTERVAL <= 0:
            break
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
