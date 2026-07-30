#!/usr/bin/env python3

# DigiMode Table
#
# Reads an ADI file as produced by WSJT-X, and summarises the number of QSOs
# on each band and in each mode.
#
# Ken McMullan, 2E0UMK
#
# Interesting observation at 3rd October 2025: there are 437 lines of code.
# Only 75 are for displaying the data we want to display. 30 lines of code
# for readnig the data. Thre are 50 lines which are my comments and change
# history. If we discount the change history, 27% of the code is the important
# stuff, and the remaining 73% is for makng it look pretty: managing the
# windows and the config file.
#
# 09 Mar 2026
# Added a checkbox to cause the display of UNIQUE respondents only.
# The unique respondents in the table are unique to that band / mode.
# It would be impossible to show a table of globally unique QSOs, since
# we would have to pick a band / mode to assosciate them with.
# We now display the total QSOs, the total of unique QSOs for all bands /
# modes and teh total of globally unique QSOs.
#
# 07 Oct 2025
# Fixed a little buglet where the total number of seconds on the most recent
# callsigns list would go over 4 digits.
#
# 03 Oct 2025
# Added a new config variable which causes the display of seconds since QSO
# rather than time of QSO in Recent QSOs list.
#
# 30 Sept 2025
# Now loads the recent QSOs window on startup if that window had been open
# at the end of the last run.
# Also, removed the label bar. I'll implement that later.
# added a new config file parameter allowing the configuration of the count
# of recent QSOs.
# Always displays the display mode, even if there's no data to dispaly.
# Made a config file variable for the optional display of the time bounds.
#
# 29 Sept 2025
# Rearrange the display so the Present time is on its own line at the bottom.
# Buttons attached to bottom of window, but in such a way that the text
# window changes size when the window is resized.
# From / To now on its own line with milliseconds removed from times.
# Converted to Unix text file format.
#
# 03 Jul 2025
# Converted to use tkinter rather than just text.
#
# 25 Jun 2025
# Each time the mode was changed, a new scheduled upidate of the file read /
# parse was scheduled. Updated the threading model so that Update QSOs does not
# trigger a ile read and Update Stats only reshedules itself if it was called
# by a scheduled instance of itself.
# Started to create better mode switching (and new mode creation) logic.
#
# Fixed the non-saving of the QSO list window.
# Bound the "r" key to the recent QSO list button.
#
# Bug list:
#
# Fix:
# DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled
# for removal in a future version. Use timezone-aware objects to represent
# datetimes in UTC: datetime.datetime.now(datetime.UTC).
#
# To do:
# Given that there are over 11,000 QSO in my log with only c. 7,400 being
# unique, it might be fun to have a list of the top ten repeat QSOs.
# Remember and restore the previous display mode.
# Button (perhaps on Recent QSOs window) to restore (dock?) the Reecnt
# Window beside the main one, with a predefined height and width.
# Add scroll bars to the recent QSOs list.
# Display count of QSOs this period (this hour, nominally).
# Display time since last QSO.
# Display rate per hour of QSOs. 6 exchanges are required per QSO. An FT8
# exchange takes 15 seconds. 6*15= 90 seconds minimum per QSO, so 40 QSOs
# per hour is technically feasable. 80 for FT4.

import os
import threading
import time
from datetime import datetime, timedelta
from collections import defaultdict
import tkinter as tk
import configparser
import re
import inspect

CONFIG_FILE = "digimodetable.conf"
ADI_FILE_PATH = ""
UNIQUE_ONLY = False

mode_list = [{"label":"All QSOs","start":"epoch","stop":"now"},
             {"label":"Last 7 days","start":"-168","stop":"now"},
             {"label":"Last 24 hours","start":"-24","stop":"now"},
             {"label":"Since 04:00","start":"04:00","stop":"now"},
             {"label":"Last hour","start":"-1","stop":"now"}]


mode_index = 0
mode_lock = threading.Lock()

all_records = []

def translate_time(timeStr):

  # assume timestamp has been supplied in the format %Y%m%d %H:%M:%S
  # eg: "20250709 04:00:00"
  
  res = datetime.strptime(timeStr, "%Y%m%d %H:%M:%S")

  if timeStr == "now" :
    res = datetime.utcnow()
  elif timeStr == "epoch" :
    res = datetime(1900, 1, 1)
  elif int(timeStr) < 0 and int(timeStr) > -10000 :
    # a resonably sized negative integer is treated as an offset in hours
    res = datetime.now() + timedelta(hours=int(timeStr))      
  elif bool(re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", timeStr)) :
    # time in "%HH:MM" is assumed to be today today
    res = datetime.combine(datetime.today().date(), datetime.strptime(time_str, "%H:%M").time())

  return res

def get_time_window(index):
    if index < 0:
        index = 0
    elif index >= len(mode_list):
        index = len(mode_list) -1

    mode = mode_list[index]

# working

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

    print(f"{datetime.utcnow().strftime('%H:%M:%S')} {inspect.stack()[1][3]} Reading: {filepath}", end="")

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


def count_modes_bands(qsos, unique_only=False):
    if unique_only:
        counts = defaultdict(set)
    else:
        counts = defaultdict(int)

    for qso in qsos:
        mode = qso.get('mode', '').upper()
        band = qso.get('band', '').lower()
        call = qso.get('call', '').upper()

        if 'MFSK' in mode:
            submode = qso.get('submode', '').upper()
            if 'FT4' in submode:
                mode = 'FT4'
            else:
                continue

        if mode == '' or band == '':
            continue

        key = (mode, band)

        if unique_only:
            if call:
                counts[key].add(call)
        else:
            counts[key] += 1

    if unique_only:
        return {k: len(v) for k, v in counts.items()}

    return dict(counts)


def get_unique_callsigns(records):
    calls = set()
    for record in records:
        call = record.get('call', '').strip().upper()
        if call:
            calls.add(call)
    return len(calls)

def load_config():
    global ADI_FILE_PATH, RECENT_QSO_COUNT, DISPLAY_TIMES, DISPLAY_SINCE, UNIQUE_ONLY
    if os.path.exists(CONFIG_FILE):
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE)
        ADI_FILE_PATH = config.get('Settings', 'ADI_FILE_PATH')
        RECENT_QSO_COUNT = config.getint('Settings', 'RECENT_QSO_COUNT', fallback=10)
        DISPLAY_TIMES = config.getboolean('Settings', 'DISPLAY_TIMES', fallback=False)
        DISPLAY_SINCE = config.getboolean('Settings', 'DISPLAY_SINCE', fallback=True)
        UNIQUE_ONLY = config.getboolean('Settings', 'UNIQUE_ONLY', fallback=False)
        

# ----------- Tkinter GUI Part ------------

class QSOStatsApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WSJT-X QSO Statistics")
        self.load_window_position()

        self.mode_index = 0
        self.recent_window = None  # Track recent window instance

        self.rowconfigure(1, weight=1)   # Let row 1 (the text box) expand
        self.columnconfigure(0, weight=1)

        # Label at the top
#        self.label_mode = tk.Label(self, text="", font=("Arial", 14))
#        self.label_mode.grid(row=0, column=0, pady=5, sticky="w")

        # Text box in the middle, expands
        self.text_output = tk.Text(self, font=("Courier", 12), wrap='none')
        self.text_output.grid(row=1, column=0, sticky="nsew")

        # Buttons at the bottom
        button_frame = tk.Frame(self)
        button_frame.grid(row=2, column=0, pady=5, sticky="ew")

        self.btn_change_mode = tk.Button(button_frame, text="Change <M>ode", command=self.change_mode)
        self.btn_change_mode.pack(side=tk.LEFT, padx=5)

        self.btn_show_recent = tk.Button(button_frame, text="Show <R>ecent QSOs", command=self.show_recent_window)
        self.btn_show_recent.pack(side=tk.LEFT, padx=5)

        # create "Unique QSOs" checkbox 
        self.unique_var = tk.BooleanVar(value=UNIQUE_ONLY)

        self.chk_unique = tk.Checkbutton(
            button_frame,
            text="Unique QSOs Only",
            variable=self.unique_var,
            command=self.update_stats
        )

        self.chk_unique.pack(side=tk.LEFT, padx=5)

        # Bind 'm' key to mode change
        self.bind('<m>', lambda event: self.change_mode())

        # Bind 'r' key to show recent window
        self.bind('<r>', lambda event: self.show_recent_window())

        # Reopen recent QSOs window if it was open last time
        config = configparser.ConfigParser()
        if os.path.exists(CONFIG_FILE):
            config.read(CONFIG_FILE)
            was_open = config.get('recentWindow', 'open', fallback='no')
            if was_open.lower() == 'yes':
                self.show_recent_window()

        # Bind close event to save geometry
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Start periodic update of main stats
        self.update_stats()


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

        # Return focus to main window
        self.focus_force()
    
    def close_recent_window(self):
        if self.recent_window is not None:
            self.recent_window.destroy()
        self.recent_window = None



    def update_recent_qsos(self):
        global all_records
        if self.recent_window is None or not self.recent_window.winfo_exists():
            # Window closed, stop updating
            return

#        records = read_adi_to_dict(ADI_FILE_PATH) # can we make ths line redundant since we've already read the records?

        # Sort records by datetime descending
        def record_dt(r):
            try:
                dt_str = r.get('qso_date', '') + r.get('time_on', '000000').zfill(6)
                return datetime.strptime(dt_str, '%Y%m%d%H%M%S')
            except:
                return datetime.min

        sorted_records = sorted(all_records, key=record_dt, reverse=True)

        recent = sorted_records[:RECENT_QSO_COUNT]

        now = datetime.utcnow()
        lines = []
        for rec in recent:
            dt = record_dt(rec)
            call = rec.get('call', '').upper()

            if DISPLAY_SINCE:
                delta = now - dt
                if delta.total_seconds() > 16 * 3600: # (960 minutes = nearly 999)
#                    time_str = "---:--"
                    time_str = "---"
                else:
                    minutes, seconds = divmod(int(delta.total_seconds()), 60)
#                    time_str = f"{minutes:03}:{seconds:02}"
                    time_str = f"{minutes:03}"
            else:
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
        self.update_stats(False) # but don't schedule another update

    def update_stats(self, reschedule = True):

        global all_records

        # Schedule next update in 15 seconds
        if reschedule: self.after(15000, self.update_stats)

        label, start_dt, end_dt = get_time_window(self.mode_index)
        all_records = read_adi_to_dict(ADI_FILE_PATH)
        filtered = filter_by_dates(all_records, start_dt, end_dt)

        counts_all = count_modes_bands(filtered, False)
        counts_unique = count_modes_bands(filtered, True)

        # Table display follows checkbox
        counts = counts_unique if self.unique_var.get() else counts_all
        # counts = count_modes_bands(filtered, self.unique_var.get())

        total_qsos = len(filtered)
        total_calls = get_unique_callsigns(filtered)
        per_mode_band_unique = sum(counts_unique.values())

        now = datetime.utcnow()

        # Clear and print in text widget
        self.text_output.delete("1.0", tk.END)

#        strUTC = "%H:%M:%S UTC"
        strUTC = "%H:%M UTC"
        self.text_output.insert(tk.END, f"\"{label}\" ")
        if self.unique_var.get():
            self.text_output.insert(tk.END, "(Unique) ")
        else:
            self.text_output.insert(tk.END, "(Global) ")
        self.text_output.insert(tk.END, f"Time Now: {now.strftime(strUTC)}\n")

        if not counts:
            self.text_output.insert(tk.END, "\nNo data to display.\n")
        else:
            modes = sorted(set(mode for (mode, band) in counts.keys()))
            bands = sorted(set(band for (mode, band) in counts.keys()))

            mode_col_width = max(len("Mode"), max(len(m) for m in modes)) if modes else len("Mode")
            band_col_width = max(max(len(b) for b in bands), 5) if bands else 5

            if DISPLAY_TIMES:
              self.text_output.insert(tk.END, f"(From: {start_dt.strftime(strUTC)} To: {end_dt.strftime(strUTC)})\n")
            self.text_output.insert(tk.END, "\n")

            header = "Mode ".ljust(mode_col_width) + " "
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
#            self.text_output.insert(tk.END, f"Total QSOs: {total_qsos}\n")
#            self.text_output.insert(tk.END, f"Per Mode/Band Unique QSOs: {per_mode_band_unique}\n")
            self.text_output.insert(tk.END, f"Total QSOs: {total_qsos}, Unique per Mode/Band: {per_mode_band_unique}\n")
            self.text_output.insert(tk.END, f"Global Unique QSOs: {total_calls}\n")

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

        config = configparser.ConfigParser()
        if os.path.exists(CONFIG_FILE):
            config.read(CONFIG_FILE)

        # Save main program settings
        config['Settings'] = {
            'ADI_FILE_PATH': ADI_FILE_PATH,
            'RECENT_QSO_COUNT': RECENT_QSO_COUNT,
            'DISPLAY_TIMES': DISPLAY_TIMES,
            'DISPLAY_SINCE': DISPLAY_SINCE,
            'UNIQUE_ONLY': self.unique_var.get()
        }

        # Save recent window state
        if self.recent_window and self.recent_window.winfo_exists():
            config['recentWindow'] = {
                'geometry': self.recent_window.geometry(),
                'open': 'yes'
            }
        else:
            config['recentWindow'] = {'open': 'no'}

        with open(CONFIG_FILE, 'w') as f:
            config.write(f)

        self.destroy()

def main():
    load_config()
    app = QSOStatsApp()
    app.mainloop()

if __name__ == "__main__":
    main()
