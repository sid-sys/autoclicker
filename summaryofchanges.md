# AutoRetry — Summary of Changes

## Project Overview
A Python automation script that watches the screen for a "Retry" button image and clicks it automatically. Designed to keep an IDE/server session alive without manual intervention.

---

## Session: 2026-04-15

### What Was Built
- **`auto_retry.py`** — Main script. Core logic:
  - `pyautogui.locateOnScreen()` with `confidence=0.8` finds the button using OpenCV template matching.
  - A `threading.Thread` (daemon) runs the scan loop so the main thread stays free for hotkey handling.
  - `keyboard.add_hotkey("ctrl+q")` registers a *global* hotkey — works even when the terminal is not in focus.
  - `plyer.notification.notify()` fires desktop popups for each state change or click event.
  - A `threading.Lock` protects the `running` boolean from race conditions between the hotkey thread and the scan thread.

### Key Architecture Decisions
| Decision | Reason |
|---|---|
| Daemon thread for scan loop | If the main process crashes or exits, the background thread dies too — no orphan processes. |
| `keyboard.wait()` in main thread | Blocks cleanly until Ctrl+C; simpler than a `while True: time.sleep(1)` loop. |
| `confidence=0.8` | High enough to avoid false positives; low enough to handle slight rendering differences per OS scaling. |
| 15s post-click wait | Gives the server time to respond before the next scan fires. Configurable at the top of the file. |
| Image path uses `__file__` | Makes the script portable — no hardcoded absolute paths. Drop the image next to the script and it works. |

### Files Created
- `auto_retry.py` — Main script
- `requirements.txt` — Python dependencies
- `suggested_features.md` — Feature tracker
- `summaryofchanges.md` — This file

### Dependencies
```
pyautogui      – screen capture + mouse clicking
opencv-python  – image template matching (used by pyautogui confidence param)
keyboard       – global hotkey registration
plyer          – cross-platform desktop notifications
pillow         – image loading support for pyautogui
```

### Outstanding Step for User
- Place `retry_button.png` (a cropped screenshot of the Retry button) in the same folder as `auto_retry.py`.
- Run: `pip install -r requirements.txt` then `python auto_retry.py`

---

## Session: 2026-04-15 — Instant Click Mode

### What Changed
- `SCAN_INTERVAL` set to `0` — no gap between scans.
- `POST_CLICK_WAIT` set to `0` — no cooldown after a click.
- Loop now has a `0.05s` micro-yield instead of `0.5s` idle sleep, so it stays
  responsive (~20 scans/sec) without burning 100% CPU.

### Why
User requested to change the hotkey to `Ctrl+1` instead of `Ctrl+Q`.

### Fix: Ctrl+C Terminal Quit
- **Problem**: Pressing `Ctrl+C` in the terminal did not quit the script because `pystray.Icon.run()` blocks the main thread in a native Windows UI loop, ignoring Python's `KeyboardInterrupt`.
- **Solution**: Evaluated the architecture and switched to `_tray_icon.run_detached()`, allowing the tray icon to run in a background thread. Now, the main Python thread simply runs a clean `time.sleep(1)` loop, which instantly intercepts `Ctrl+C` and gracefully stops the script and tray icon.

### Hotkey Tweak
- Changed the hotkey from `Ctrl+1` to `` ` `` (backtick, below Esc) for even faster, single-key toggling.

### Key Decision
Both `SCAN_INTERVAL` and `POST_CLICK_WAIT` remain as named constants at the top of
the file. To restore a delay, just set them to the desired number of seconds — no other
code needs to change.

---

## Session: 2026-04-15 — Daily Click Count Tracker

### What Changed
- Added `session_clicks` global counter incremented on every successful click.
- Added `log_click_to_tracker()` function:
  - Reads `clickcounttracker.md` (creates it from scratch if missing).
  - Searches for today's date entry using a compiled regex.
  - Increments the count in-place if found; appends a new line if it's a new day.
  - Writes the file back atomically.
- Terminal now shows `(session: N)` after each click line.
- Ctrl+C exit prints a full session summary: `📊 Session summary: N click(s) this session.`

### Why
User wants a running record of how often their IDE fails each day, saved
to a readable Markdown file they can check at any time.

### File Format (`clickcounttracker.md`)
```
# Click Count Tracker

### 2026-04-15  →  Clicks: 7
### 2026-04-16  →  Clicks: 3
```
Each line is updated in-place when a new click arrives on the same day.
A new line is appended automatically when the date changes.

### Imports Added
- `re` — regex parsing for the tracker file date entries.
- `datetime` — to get today's ISO date string (`YYYY-MM-DD`).

---

## Session: 2026-04-15 — Dual-Colour Cursor Scheme

### What Changed
- **Two-colour cursor system**:
  - 🟢 **Lime `#CBFF00`** (`IDLE_CURSOR_COLOR = 0x0000FFCB`) — script running, scanner is OFF/paused.
  - 🔴 **Red `#FF0004`** (`ACTIVE_CURSOR_COLOR = 0x000400FF`) — scanner is actively hunting for the Retry button.
- Lime cursor is set **immediately on script startup** (scanner begins as OFF).
- On Ctrl+C exit: cursor is restored to the state *before the script launched*.

### Architecture Decisions
- **COLORREF DWORD format** = `0x00BBGGRR`. Always convert before storing:
  - `#FF0004` → `0x000400FF`
  - `#CBFF00` → `0x0000FFCB`
- **Registry path correction**: `_CURSOR_REG_PATH` and `_CURSOR_REG_VALUE` were accidentally deleted in a prior edit and restored here.
- **`CursorType = 3`** must be written alongside `CursorColor` — without it Windows ignores the custom colour.
- **Broadcast**: `WM_SETTINGCHANGE + "ImmersiveColorSet"` (what Windows Settings itself uses) + legacy `SPI_SETCURSORS` for compatibility.
- **Prerequisite**: User must enable "Custom" pointer colour in *Settings → Accessibility → Mouse pointer and touch* at least once before registry control works.

---
