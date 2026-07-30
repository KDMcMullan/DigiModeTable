# DigiModeTable
Create tabulated QSO counts by band and mode from the WSJT-X ADI file.

Grab the .py file and the .conf file. Put them in the same place. Modify the conf file to add the path to your .ADI file. Otherwise, just run it. You may havePython  libraries to install.

In the [Settings] section:

- adi_file_path is the path to your ADI file. Can be a Windows or a Linux path depending on your OS.
- recent_qso_count is the count of recent QSOs to show in that widget.
- display_times is to display the start and end time of teh data set you're looking at.

To be documented in due course:

- display_since
- unique_only
- rate_window_minutes

Farting around with them won'tbreak anything.

The script runs in Windows and Linux.
- In Windows, the file path might be "D:\Ken\HamRadio\wsjtx_log.adi".
- In Linux, it could be "~/.local/share/WSJT-X/wsjtx_log.adi".

# qso_web.py
This was the start point. This was a webserver which essentially had the same initial functions. I'd thought it might be the direction to go, but for some reason I'm enjoying tkinter.

# Interesting Observarion
Although, as a classically trained Software Engineer, it should have been obvious:
At 3rd October 2025, there were 437 lines of code.
Only 75 were for displaying the data we want to display. 30 lines of code were for reading the data. There were 50 lines of comments and change history.
If we discount the change history, 27% of the code is the important stuff, and the remaining 73% is just bloat for making it look pretty: managing the windows and the config file. Such is the nature of contemporary "programming".
