from flask import Flask, render_template, request
import os
import configparser
from datetime import datetime, timedelta, timezone
from collections import defaultdict

app = Flask(__name__)

# Config load
config = configparser.ConfigParser()
config.read("qso_stats.conf")
FILE_PATH = config.get("Settings", "FILE_PATH", fallback=os.path.expanduser("~/.local/share/WSJT-X/wsjtx_log.adi"))

VALID_MODES = {"FT8", "FT4"}
DEBUG_MODE = True  # Set to False to silence debug prints

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

def print_extra_stats(qsos, stat_level):
    if stat_level == 0:
        return ""

    now = datetime.now(timezone.utc)
    qso_24h = 0
    qso_week = 0
    unique_calls = set()

    for qso in qsos:
        date = qso.get("qso_date")
        time_on = qso.get("time_on")
        call = qso.get("call", "").upper()
        mode = qso.get("mode", "").upper()
        submode = qso.get("submode", "").upper()

        try:
            dt = datetime.strptime(f"{date} {time_on}", "%Y%m%d %H%M%S").replace(tzinfo=timezone.utc)
        except:
            continue

        if submode in VALID_MODES:
            mode = submode
        elif mode not in VALID_MODES:
            continue

        if now - dt <= timedelta(hours=24):
            qso_24h += 1

        if now - dt <= timedelta(days=7):
            qso_week += 1
            unique_calls.add(call)

    out = []
    if stat_level >= 1:
        out.append(f"QSOs in last 24 hours: {qso_24h}")
    if stat_level >= 2:
        out.append(f"QSOs this week: {qso_week}")
        out.append(f"Unique callsigns this week: {len(unique_calls)}")
    return "\n".join(out)

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

    if DEBUG_MODE:
        print("\n[DEBUG] summarize_qsos output:")
        print(f"Counts: {dict(counts)}")
        print(f"Hourly QSOs: {dict(hourly_qsos)}")
        print(f"Most recent highlight: {most_recent}")

    return counts, hourly_qsos, most_recent

@app.route("/", methods=["GET", "POST"])
def index():
    stat_level = int(request.form.get("stat_level", "0"))
    all_flag = request.form.get("all") == "1"
    interval = int(request.form.get("interval", "30"))
    date = request.form.get("date", "").strip()
    time_window = int(request.form.get("time_window", "60"))

    stats = ""
    table = ""
    latest_qso = "None"

    if os.path.isfile(FILE_PATH):
        qsos = parse_adi(FILE_PATH)

        stats = print_extra_stats(qsos, stat_level)

        target_date = date if date else None
        window_hours = time_window if not target_date else None

        counts, hourly_qsos, highlight = summarize_qsos(qsos, target_date=target_date, window_hours=window_hours)

        if counts:
            table = format_table(counts, highlight)

        all_times = []
        for q in qsos:
            try:
                dt = datetime.strptime(f"{q.get('qso_date','19700101')} {q.get('time_on','000000')}", "%Y%m%d %H%M%S").replace(tzinfo=timezone.utc)
                all_times.append(dt)
            except:
                pass
        if all_times:
            latest_qso = max(all_times).strftime("%Y-%m-%d %H:%M:%S UTC")
            if latest_qso.endswith(" UTC UTC"):
                latest_qso = latest_qso[:-4]

    return render_template("index.html",
                           stat_level=stat_level,
                           all=all_flag,
                           interval=interval,
                           date=date,
                           time_window=time_window,
                           stats=stats,
                           table=table,
                           latest_qso=latest_qso)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
