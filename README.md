# DigiModeTable
Create tabulated QSO counts by band and mode from the WSJT-X ADI file.

In the configuration section:
- ALL is a boolean. True means process and tabulate the entire file. False means just for a specific day.
- DATE is a string in the format "YYYYMMDD". If blank, today's date is used.
- INTERVAL is an integer in seconds as to how often the process should run. Zero means run once and exit.
- HOURLY_WINDOW is an integer in minutes which tells us how many QSOs there have been in that time.

The script runs in Windows or Linux.
- In Windows, the defualt file path is "D:\Ken\HamRadio\wsjtx_log.adi".
- In Linux, it's "~/.local/share/WSJT-X/wsjtx_log.adi".
