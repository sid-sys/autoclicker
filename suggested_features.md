# AutoRetry – Feature Tracker

## ✅ Implemented Features

- **Screen Image Matching** — Uses `pyautogui` + `opencv-python` to locate `retry_button.png` on screen with configurable confidence threshold (default 0.8).
- **Ctrl+Q Global Hotkey Toggle** — Press `Ctrl+Q` anywhere on the system to start or stop scanning without switching windows.
- **System Notifications via plyer** — Desktop notifications fire on: toggle ON, toggle OFF, and successful button click.
- **Post-Click Wait (15s)** — After clicking Retry, the script waits 15 seconds before scanning again so the server has time to respond.
- **Scan Interval (2s)** — When idle (button not found), the script rescans every 2 seconds.
- **Daemon Thread** — Scanner runs in a background thread; Ctrl+C cleanly exits the whole program.
- **Instant Click (no delay)** — Removed all scan and post-click delays. The script now fires a click the moment the image is detected (~20 scans/sec with 0.05s CPU yield).
- **Click Count Tracker (Daily Log)** — Every successful click increments an in-memory session counter shown in the terminal. Writes/updates a per-day running total in `clickcounttracker.md` (format: `### YYYY-MM-DD → Clicks: N`). Counts persist across sessions and accumulate per calendar day. Session total is printed on Ctrl+C exit.

---

## 🚀 Implemented Features (from suggestions)

- **Dual-Colour Cursor** — System cursor changes colour to reflect scanner state: 🟢 lime `#CBFF00` when idle, 🔴 red `#FF0004` when scanning. Controlled via the Windows Accessibility registry (`HKCU\Software\Microsoft\Accessibility`). Saves and restores previous cursor state on exit. Uses `WM_SETTINGCHANGE + "ImmersiveColorSet"` broadcast for instant application without logout.

- **System Tray Icon** — A `pystray` tray icon sits in the Windows taskbar notification area. The icon is a dynamically generated coloured dot (lime = idle, red = scanning) that updates instantly on every toggle. Right-click menu has: **Toggle Scanner**, **Quit AutoRetry**. Double-click also toggles. The tray icon owns the main thread's Windows message loop, replacing `keyboard.wait()`.

---

## 💡 Suggested Features

1. **Multi-Button Support**
   - Support a list of button images (e.g., `retry_button.png`, `reconnect_button.png`) and click whichever one is found first.
   - Useful for IDEs that show different labels depending on the error state.

2. **Configurable Settings via `.env` or `config.ini`**
   - Let users set `SCAN_INTERVAL`, `POST_CLICK_WAIT`, `CONFIDENCE`, `HOTKEY`, and `BUTTON_IMAGE` path in a config file rather than editing the source code.
   - Validate the config on startup and show friendly error messages.

3. **Sound Feedback on Click**
   - Play a short system beep using `winsound.Beep()` when a click fires.
   - Lets you know the script worked even when you're not watching the terminal or screen.

4. **Weekly / Monthly Summary Report**
   - Add a `--report` CLI flag that reads `clickcounttracker.md` and prints a formatted table of totals by week and month.
   - Helps you spot patterns — e.g. which days / times your IDE fails most.

5. **Auto-Screenshot on Click**
   - Capture and save a screenshot (with timestamp filename) every time a click fires.
   - Useful for debugging: you can see exactly what state the IDE was in when it needed a retry.

6. **Click Count in Tray Tooltip**
   - Show today's click count in the tray icon tooltip text so you can check it without opening the terminal.
   - Example tooltip: `AutoRetry — IDLE 🟢 | Today: 42 clicks`

7. **Startup with Windows (Auto-Launch)**
   - Add a `--install` CLI flag that registers the script in `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` so it starts automatically at login.
   - Companion `--uninstall` flag to remove it.

8. **Configurable Hotkeys via GUI**
   - Provide a simple GUI (e.g., using `tkinter` or `PyQt`) where the user can bind custom hotkeys without editing the code.

9. **Detailed Logging System**
   - Implement a log file (`app.log`) that tracks all events like hotkey presses, state changes, errors, and timeouts.

10. **Multiple Image Matching with Fallbacks**
    - Provide fallback images in case the primary 'retry' button design changes slightly due to theme or resolution changes.
