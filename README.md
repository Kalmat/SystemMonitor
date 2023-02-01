# System Monitor by alef

This is just a graphical, easy-to-watch yet very simple system monitor
(Linux and Windows only; and Intel and NVIDIA only. Unfortunately, I can not test other combinations)

There are many other tools to monitor your system, but either they lack some info, or they are intended to system or game info only, or they are not easily readable, or not graphical, or too big, or too small...

You can easily monitor:

- CPU Usage (%)
- CPU Temp (C/F)
- Mem Usage (%)
- System Mode: Disk Usage (%) / Game Mode: FPS (#)
- GPU Usage (%)
- GPU Temp (C/F)
- GPU Fan (%)
- GPU Power (W)
- [Optional] System Information: System name, OS name and version, CPU model, GPU model, Uptime

Nevertheless, this script is just for a quick, easy monitoring. If you detect any problem, you better use a specialized, more detailed application.

#### WARNING

Be aware that integrated graphic cards will show null temperature and fan speed values. Its values will be similar to your CPU values.

## System Requirements

- Windows: Windows 8+ version
  - LibreHardwareMonitor.dll and SharpHid.dll (https://github.com/LibreHardwareMonitor/LibreHardwareMonitor). Don't forget to right-click the .dll files, open "Properties" and, under "General", click "Unblock"
  - PresentMon-1.8.0-x64.exe (https://github.com/GameTechDev/PresentMon)
  - Integrated GPU (Intel/AMD): Nothing additional required
  - Dedicated GPU - NVIDIA: Updated official drivers
  - Dedicated GPU - AMD: Not tested
- Linux: 
  - Integrated GPU (Intel/AMD): Mesa drivers (in some cases mesa-utils must be manually installed: sudo apt install mesa-utils)
  - Dedicated GPU:
    - NVIDIA: Updated proprietary drivers (not -open drivers). This will replace Mesa drivers, so FPS counter will not be available
    - AMD: Not tested

## Usage / Settings

Right-click SysMon window (or press Ctl+Alt+s, especially when in game mode) to show Settings Menu on screen:
- GAME/SYSTEM MODE: Toggle between Game (FPS info, no focus) and System modes
- ORIENTATION:      Switch view between horizontal/vertical
- THEME:            Switch styles between conky/gauge/pie/arc/arc with indicator/numbers
- SYSTEM INFO:      Show additional System Information
- MOVE WINDOW:      Mouse Left click and drag
- SHOW/HIDE:        (Alt+s) Show/Hide SysMon window (it also refreshes selected app when in game mode)
- QUIT SYSMON:      Quit program

Both key sequences (Ctl+Alt+s and Alt+s) are system-wide. In case of conflict, change the activation key ("s") in settings.json

For more advanced settings, edit settings.json to adapt window size, colors and other details.

## Monitor a specific application / game:

If you want to monitor the FPS values for a specific application or game, do the following:

### Windows:

Please note that not all applications will be available to be monitored (e.g. Chrome can be monitored, but not PyCharm).

1. Open SysMon and configure it (position, orientation, theme) to your needs
2. Activate Game Mode (Right-click on SysMon window and select proper option Settings window)
3. Open the target application/game (do not worry if the application obscures the SysMon window)
4. Minimize Sysmon (Alt+s), click on the application you want to monitor (not required if the application is fullscreen), and maximize Sysmon (Alt+s) again

On Windows, by default, SysMon will provide the FPS values for Desktop Window Manager (dwm.exe) application.

### Linux:

Only OpenGL applications (typically games) will provide the FPS values.

- Option 1.

  - Run on a Terminal: `sysmon (or python3 sysmon.py) full/path/to/application`

- Option 2.

  1. Open SysMon and configure it (position, orientation, theme) to your needs
  2. Activate Game Mode (Right-click on SysMon window and select proper option Settings window)
  3. Enter the full path of the application/game in the text field and press "Go" button 

On Linux, by default, SysMon will show no FPS values ("000").

#### WARNING

FPS counter will inevitably have a delay, since it calculates the number of frames in a period of time (1 second, in this case).

## Licenses and Mentions:

#### See 'resources/RESOURCES_LICENSES.txt' for more info on resources download and licenses
