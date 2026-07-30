#!/usr/bin/env python3
import os
import sys
import time
import threading
from collections import defaultdict

from datetime import datetime, timedelta
import csv

FILENAME = "wsjtx_log.adi"


# OS specific path / keyboard handler

if os.name == 'nt':

    import msvcrt

    def get_key_nonblocking():
        if msvcrt.kbhit():
            ch = msvcrt.getch()
            print(f"ch:{ch}")
            try:
                return ch.decode('utf-8').lower()
            except UnicodeDecodeError:
                return None
        return None

    FILE_PATH = os.path.join(r"D:\Ken\HamRadio", FILENAME)


else: # assume Linux

    import termios
    import tty
    import select

    def get_key_nonblocking():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            if select.select([sys.stdin], [], [], 0.05)[0]:
                return sys.stdin.read(1).lower()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return None

    FILE_PATH = os.path.join(os.path.expanduser("~/.local/share/WSJT-X"), FILENAME)


# Global mode index: 0 = All time, 1 = Since 4am today, 2 = Last 7 days
mode_index = 0
mode_lock = threading.Lock()

def input_monitor():
    global mode_index
    while True:
        key = input().strip().lower()
        if key == 'm':
            print("[SWITCH MODE] You typed 'm'")
            with mode_lock:
                mode_index = (mode_index + 1) % 3


def get_time_window(index):
    now = datetime.utcnow()
    if index == 0:
        return ("All QSOs", datetime(1900, 1, 1), now)
    elif index == 1:
        today_4am = now.replace(hour=4, minute=0, second=0, microsecond=0)
        if now < today_4am:
            today_4am -= timedelta(days=1)
        return ("Since 4am Today", today_4am, now)
    elif index == 2:
        return ("Last 7 Days", now - timedelta(days=7), now)

def read_adi_to_dict(filepath):
    if not os.path.exists(filepath):
        print(f"[ERROR] File not found: {filepath}")
        return []

    with open(filepath, 'r', encoding='utf-8') as file:
        content = file.read().lower()  # Normalize to lowercase
    entries = content.split('<eor>')
    records = []

    for entry in entries:
        qso = {}
        fields = entry.strip().split('<')
        for field in fields:
            if ':' in field:
                try:
                    key_len, value = field.split('>', 1)
                    key, length = key_len.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    qso[key] = value
                except ValueError:
                    continue
        if qso:
            records.append(qso)

    return records

def filter_by_dates(records, start_dt, end_dt):
    result = []
    for record in records:
        try:
            date_str = record.get('qso_date', '')
            time_str = record.get('time_on', '000000')
            if len(time_str) < 6:
                time_str = time_str.zfill(6)  # Pad to 6 digits

            dt = datetime.strptime(date_str + time_str, '%Y%m%d%H%M%S')
            if start_dt <= dt <= end_dt:
                result.append(record)
        except Exception as e:
            print(f"[WARN] Skipping record due to date parse error: {e}")
            continue
    return result

def count_modes_bands(qsos):
    counts = defaultdict(int)
    for qso in qsos:
        mode = qso.get('mode', '').upper()
        band = qso.get('band', '').lower()

        # Normalize mode for FT4 inside MFSK or others
        if 'MFSK' in mode:
            if 'FT4' in mode:
                mode = 'FT4'
            else:
                # Skip unrecognized MFSK modes
                continue

        if mode == '' or band == '':
            continue  # skip if missing

        counts[(mode, band)] += 1
    return dict(counts)

def get_unique_callsigns(records):
    calls = set()
    for record in records:
        call = record.get('call', '').strip().upper()
        if call:
            calls.add(call)
    return len(calls)

def print_table(counts, start, end, now, total_qsos, total_calls):
    if not counts:
        print("No data to display.")
        return

    # Extract modes and bands from keys that are tuples (mode, band)
    modes = set()
    bands = set()

    for key in counts.keys():
        if isinstance(key, tuple) and len(key) == 2:
            mode, band = key
            modes.add(mode)
            bands.add(band)
        else:
            # If key is not tuple, you might want to log or handle differently
            pass

    modes = sorted(modes)
    bands = sorted(bands)

    mode_col_width = max(len("Mode"), max(len(m) for m in modes)) if modes else len("Mode")
    band_col_width = max(max(len(b) for b in bands), 5) if bands else 5

    # Header
    header = "Mode".ljust(mode_col_width) + " "
    for band in bands:
        header += band.ljust(band_col_width) + " "
    print(header)
    print("-" * len(header))

    # Rows
    for mode in modes:
        row = mode.ljust(mode_col_width) + " "
        for band in bands:
            count = counts.get((mode, band), 0)
            row += str(count).rjust(band_col_width) + " "
        print(row)

    print()
    print(f"{start} to {end} (Now: {now} UTC)")
    print(f"Total QSOs: {total_qsos}    Unique callsigns: {total_calls}")


def main():

    mode_index = 0
    display_modes = [
      ("All QSOs since 1900-01-01", datetime(1900, 1, 1), datetime.utcnow()),
      ("All QSOs since 4am today", datetime.utcnow().replace(hour=4, minute=0, second=0, microsecond=0), datetime.utcnow()),
      ("All QSOs last 168 hours", datetime.utcnow() - timedelta(hours=168), datetime.utcnow())
    ]
    threading.Thread(target=input_monitor, daemon=True).start()
    while True:
        try:
            all_records = read_adi_to_dict(FILE_PATH)
            print(f"[DEBUG] Loaded {len(all_records)} QSOs from file.")
            with mode_lock:
                desc, start, end = get_time_window(mode_index)
            filtered = filter_by_dates(all_records, start, end)
            print(f"[DEBUG] Date filtered to {len(filtered)} QSOs.")
            counts = count_modes_bands(filtered)
            now = datetime.utcnow()
            total_qsos = len(filtered)
            total_calls = get_unique_callsigns(filtered)
            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"Display mode: {desc}")
            print_table(counts, start, end, now, total_qsos, total_calls)
            time.sleep(15)
        except KeyboardInterrupt:
            break

        time.sleep(1)  # Sleep a bit and loop again


if __name__ == "__main__":
    main()
