#!/usr/bin/env python3

# DigiMode Table
#
# Reads an ADI file as produced by WSJT-X, and summarises the number of QSOs
# on each band and in each mode.
#
# Ken McMullan, 2E0UMK
#
# 03 Jul 2025
# Converted to use tkinter rather than just text.
#
# Fixed the non-saving of the QSO list window.
# Bound the "r" key to the recent QSO list button.
#
# Bug list:
# <empty>
#
# To do:
# Rearrange the display so the Present time is at the top.
# Save the fact that the Most Recet QSO window is open, for next time.
# Buttons attached to bottom of table rether than bottom of window.
# Merge the two config files into one.
# Shorter summary (eg From: To:).
# Display count of QSOs this period (this hour, nominally).
# Remove the need to read the .ADI file again in updating the most
# recent QSOs list, since the records have already been read. 

import os
import threading
import time
from datetime import datetime, timedelta
from collections import defaultdict
import tkinter as tk
import configparser

FILENAME = "wsjtx_log.adi"
CONFIG_FILE = "window_position.ini"

if os.name == 'nt':
    FILE_PATH = os.path.join(r"D:\Ken\HamRadio", FILENAME)
else:
    FILE_PATH = os.path.join(os.path.expanduser("~/.local/share/WSJT-X"), FILENAME)

mode_index = 0
mode_lock = threading.Lock()

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

    print(f"Reading: {filepath}", end="")

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

    print(f" {len(records)} entries.")

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

        if 'MFSK' in mode:
            submode = qso.get('submode', '').upper()
            if 'FT4' in submode:
                mode = 'FT4'
            else:
                continue

        if mode == '' or band == '':
            continue

        counts[(mode, band)] += 1
    return dict(counts)

def get_unique_callsigns(records):
    calls = set()
    for record in records:
        call = record.get('call', '').strip().upper()
        if call:
            calls.add(call)
    return len(calls)

# ----------- Tkinter GUI Part ------------

class QSOStatsApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WSJT-X QSO Statistics")
        self.load_window_position()

        self.mode_index = 0
        self.recent_window = None  # Track recent window instance

        self.label_mode = tk.Label(self, text="", font=("Arial", 14))
        self.label_mode.pack(pady=5)

        self.text_output = tk.Text(self, font=("Courier", 12), wrap='none')
        self.text_output.pack(fill=tk.BOTH, expand=True)

        self.btn_change_mode = tk.Button(self, text="Change <M>ode", command=self.change_mode)
        self.btn_change_mode.pack(pady=5)

        # New button for last 10 QSOs window
        self.btn_show_recent = tk.Button(self, text="Show <R>ecent QSOs", command=self.show_recent_window)
        self.btn_show_recent.pack(pady=5)

        # Bind 'm' key to mode change
        self.bind('<m>', lambda event: self.change_mode())

        # Bind 'r' key to show recent window
        self.bind('<r>', lambda event: self.show_recent_window())

        # Bind close event to save geometry
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Start periodic update of main stats
        self.update_stats()

    # Your existing methods unchanged here...

    def show_recent_window(self):
        if self.recent_window is not None and self.recent_window.winfo_exists():
            self.recent_window.lift()
            return

        self.recent_window = tk.Toplevel(self)
        self.recent_window.title("Recent QSOs")
        
        # Load last saved geometry and set it if available
        geom = self.load_recent_window_position()
        if geom:
            self.recent_window.geometry(geom)
        else:
            self.recent_window.geometry("300x250")

        self.recent_text = tk.Text(self.recent_window, font=("Courier", 12), wrap='none', state=tk.DISABLED)
        self.recent_text.pack(fill=tk.BOTH, expand=True)

        # Save geometry on close
        def on_close_recent():
            self.save_geometry_section('recentWindow', self.recent_window.geometry())
            self.close_recent_window()

        self.recent_window.protocol("WM_DELETE_WINDOW", on_close_recent)

        self.update_recent_qsos()

    def close_recent_window(self):
        if self.recent_window is not None:
            self.recent_window.destroy()
        self.recent_window = None


    def update_recent_qsos(self):
        if self.recent_window is None or not self.recent_window.winfo_exists():
            # Window closed, stop updating
            return

        records = read_adi_to_dict(FILE_PATH)

        # Sort records by datetime descending
        def record_dt(r):
            try:
                dt_str = r.get('qso_date', '') + r.get('time_on', '000000').zfill(6)
                return datetime.strptime(dt_str, '%Y%m%d%H%M%S')
            except:
                return datetime.min

        sorted_records = sorted(records, key=record_dt, reverse=True)

        recent = sorted_records[:10]

        lines = []
        for rec in recent:
            dt = record_dt(rec)
            call = rec.get('call', '').upper()
            time_str = dt.strftime("%H:%M:%S")
            lines.append(f"{time_str}  {call}")

        self.recent_text.config(state=tk.NORMAL)
        self.recent_text.delete("1.0", tk.END)
        if lines:
            self.recent_text.insert(tk.END, "\n".join(lines))
        else:
            self.recent_text.insert(tk.END, "No QSOs found.")
        self.recent_text.config(state=tk.DISABLED)

        # Schedule next update in 15 seconds
        self.recent_window.after(15000, self.update_recent_qsos)

    def change_mode(self):
        self.mode_index = (self.mode_index + 1) % 3
        self.update_stats()

    def update_stats(self):
        label, start_dt, end_dt = get_time_window(self.mode_index)
        records = read_adi_to_dict(FILE_PATH)
        filtered = filter_by_dates(records, start_dt, end_dt)
        counts = count_modes_bands(filtered)
        total_qsos = len(filtered)
        total_calls = get_unique_callsigns(filtered)
        now = datetime.utcnow()

        # Clear and print in text widget
        self.text_output.delete("1.0", tk.END)

        if not counts:
            self.text_output.insert(tk.END, "No data to display.\n")
        else:
            modes = sorted(set(mode for (mode, band) in counts.keys()))
            bands = sorted(set(band for (mode, band) in counts.keys()))

            mode_col_width = max(len("Mode"), max(len(m) for m in modes)) if modes else len("Mode")
            band_col_width = max(max(len(b) for b in bands), 5) if bands else 5

            header = "Mode".ljust(mode_col_width) + " "
            for band in bands:
                header += band.ljust(band_col_width) + " "
            self.text_output.insert(tk.END, header + "\n")
            self.text_output.insert(tk.END, "-" * len(header) + "\n")

            for mode in modes:
                row = mode.ljust(mode_col_width) + " "
                for band in bands:
                    count = counts.get((mode, band), 0)
                    row += str(count).rjust(band_col_width) + " "
                self.text_output.insert(tk.END, row + "\n")

            self.text_output.insert(tk.END, "\n")
            self.text_output.insert(tk.END, f"{label}: {start_dt} to {end_dt} (Now: {now} UTC)\n")
            self.text_output.insert(tk.END, f"Total QSOs: {total_qsos}    Unique callsigns: {total_calls}\n")

        # Schedule next update in 15 seconds
        self.after(15000, self.update_stats)

    def save_geometry_section(self, section, geometry):
        config = configparser.ConfigParser()
        if os.path.exists(CONFIG_FILE):
            config.read(CONFIG_FILE)
        config[section] = {'geometry': geometry}
        with open(CONFIG_FILE, 'w') as f:
            config.write(f)

    def load_recent_window_position(self):
        if os.path.exists(CONFIG_FILE):
            config = configparser.ConfigParser()
            config.read(CONFIG_FILE)
            geometry = config.get('recentWindow', 'geometry', fallback=None)
            return geometry
        return None

    def load_window_position(self):
        if os.path.exists(CONFIG_FILE):
            config = configparser.ConfigParser()
            config.read(CONFIG_FILE)
            geometry = config.get('Window', 'geometry', fallback=None)
            if geometry:
                self.geometry(geometry)

    def on_close(self):
        self.save_geometry_section('Window', self.geometry())
        if self.recent_window and self.recent_window.winfo_exists():
            self.save_geometry_section('recentWindow', self.recent_window.geometry())
        self.destroy()


def main():
    app = QSOStatsApp()
    app.mainloop()

if __name__ == "__main__":
    main()
