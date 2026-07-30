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

# qso_web.py
This was the start point. This was a webserver which essentially had the same initial functions. I'd thought it might be the direction to go, but for some reason I'm enjoying tkinter.

# Interesting Observarion
Although, as a classically trained Software Engineer, it should have been obvious:
At 3rd October 2025, there were 437 lines of code.
Only 75 were for displaying the data we want to display. 30 lines of code were for reading the data. There were 50 lines of comments and change history.
If we discount the change history, 27% of the code is the important stuff, and the remaining 73% is just bloat for making it look pretty: managing the windows and the config file. Such is the nature of contemporary "programming".
