"""
auto_retry.py
=============
Auto-clicks a 'Retry' button found on screen using image recognition.

Controls:
  `       →  Toggle the scanner ON / OFF
  System tray icon (right-click to toggle / quit)

Visual feedback:
  • Tray icon: lime dot = idle, red dot = active
  • Desktop notifications on state changes

Requirements:
  pip install pyautogui opencv-python keyboard plyer pillow pystray
"""

import time
import os
import re
import threading
import datetime
import pyautogui
import keyboard
import pystray
from PIL import Image, ImageDraw
from plyer import notification

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
BUTTON_IMAGE      = os.path.join(os.path.dirname(__file__), "retry_button.png")
TRACKER_FILE      = os.path.join(os.path.dirname(__file__), "clickcounttracker.md")
SCAN_INTERVAL     = 0          # seconds between scans when idle (0 = no delay)
POST_CLICK_WAIT   = 0          # seconds to wait after a successful click (0 = none)
CONFIDENCE        = 0.8        # image-match confidence (0.0 – 1.0)
HOTKEY            = "`"        # toggle hotkey
APP_NAME          = "AutoRetry"

# Cursor / tray icon colours  (PIL RGB tuples)
ACTIVE_DOT_COLOR = (255,   0,   4)   # #FF0004 — red  (scanner ON)
IDLE_DOT_COLOR   = (203, 255,   0)   # #CBFF00 — lime (scanner OFF)


# ──────────────────────────────────────────────
# State
# ──────────────────────────────────────────────
running        = False              # whether the scanner is active
state_lock     = threading.Lock()  # protect `running` across threads
session_clicks = 0                 # clicks in this run
_tray_icon: pystray.Icon | None = None  # system tray icon instance


# ──────────────────────────────────────────────
# Tray icon helpers
# ──────────────────────────────────────────────
def _make_dot_icon(color_rgb: tuple, size: int = 64) -> Image.Image:
    """Generate a circular dot PNG as a PIL Image for the system tray."""
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad  = 4
    # Filled circle
    draw.ellipse([pad, pad, size - pad, size - pad], fill=color_rgb)
    # Thin dark border for legibility on light/dark taskbars
    draw.ellipse([pad, pad, size - pad, size - pad],
                 outline=(30, 30, 30, 180), width=3)
    return img


def _update_tray(active: bool) -> None:
    """Swap the tray icon image and tooltip to reflect the current state."""
    global _tray_icon
    if _tray_icon is None:
        return
    color   = ACTIVE_DOT_COLOR if active else IDLE_DOT_COLOR
    label   = "SCANNING 🔴" if active else "IDLE 🟢"
    _tray_icon.icon  = _make_dot_icon(color)
    _tray_icon.title = f"{APP_NAME}  —  {label}"


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def notify(title: str, message: str) -> None:
    """Send a system desktop notification."""
    try:
        notification.notify(
            title=f"{APP_NAME} — {title}",
            message=message,
            app_name=APP_NAME,
            timeout=4,
        )
    except Exception as e:
        print(f"[Notification error] {e}")



def log_click_to_tracker() -> None:
    """
    Increment today's click count in clickcounttracker.md.
    Creates the file if it doesn't exist.
    Format per day:
      ### 2026-04-15  →  Clicks: 7
    """
    today = datetime.date.today().isoformat()   # e.g. "2026-04-15"
    header_re = re.compile(rf"^### {re.escape(today)}\s*→\s*Clicks:\s*(\d+)", re.MULTILINE)

    # Read existing content (or start fresh)
    if os.path.isfile(TRACKER_FILE):
        with open(TRACKER_FILE, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = "# Click Count Tracker\n\nLogs how many times AutoRetry clicked the Retry button, per day.\n\n"

    match = header_re.search(content)
    if match:
        new_count = int(match.group(1)) + 1
        content = header_re.sub(f"### {today}  →  Clicks: {new_count}", content, count=1)
    else:
        # New day — append a fresh entry
        new_count = 1
        content += f"### {today}  →  Clicks: {new_count}\n"

    with open(TRACKER_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[{time.strftime('%H:%M:%S')}] 📊 Tracker updated — {today}: {new_count} clicks total")


def find_and_click() -> bool:
    """
    Search for retry_button.png on screen.
    Returns True if found and clicked, False otherwise.
    """
    global session_clicks
    try:
        location = pyautogui.locateOnScreen(BUTTON_IMAGE, confidence=CONFIDENCE)
        if location:
            center = pyautogui.center(location)
            pyautogui.click(center)
            session_clicks += 1
            print(f"[{time.strftime('%H:%M:%S')}] ✅ Clicked Retry button at {center}  (session: {session_clicks})")
            log_click_to_tracker()
            return True
        else:
            return False
    except pyautogui.ImageNotFoundException:
        return False
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] ⚠️  Error during scan: {e}")
        return False


def toggle_running() -> None:
    """Toggle the running state, swap cursor colour + tray icon, and notify."""
    global running
    with state_lock:
        running = not running
        state = running

    _update_tray(state)   # update dot colour in taskbar

    if state:
        print(f"\n[{time.strftime('%H:%M:%S')}] ▶️  Scanner STARTED (Press {HOTKEY.upper()} to stop)")
        notify("Started ▶️", f"Now scanning. Press {HOTKEY.upper()} to stop.")
    else:
        print(f"\n[{time.strftime('%H:%M:%S')}] ⏹️  Scanner STOPPED (Press {HOTKEY.upper()} to resume)")
        notify("Stopped ⏹️", f"Scanner paused. Press {HOTKEY.upper()} to resume.")


# ──────────────────────────────────────────────
# Main loop (runs in its own thread)
# ──────────────────────────────────────────────
def scan_loop() -> None:
    """Background loop that scans for the Retry button."""
    while True:
        with state_lock:
            active = running

        if active:
            clicked = find_and_click()

            if clicked:
                notify(
                    "Clicked! ✅",
                    "Retry button found and clicked immediately."
                )
                if POST_CLICK_WAIT > 0:
                    time.sleep(POST_CLICK_WAIT)
            else:
                if SCAN_INTERVAL > 0:
                    time.sleep(SCAN_INTERVAL)
            # Tiny yield so we don't peg the CPU at 100%
            time.sleep(0.05)
        else:
            # Sleeping in small increments so the loop stays responsive
            time.sleep(0.1)


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────
def _quit_app(icon: pystray.Icon | None = None, item=None) -> None:
    """Cleanly shut down: print summary, stop tray."""
    print(f"\n\n📊 Session summary: {session_clicks} click(s) this session.")
    print(f"   Full log → {TRACKER_FILE}")
    print("👋 Exiting AutoRetry. Goodbye!")
    if _tray_icon is not None:
        _tray_icon.stop()


def main() -> None:
    global _tray_icon

    # Sanity check – make sure the button image exists
    if not os.path.isfile(BUTTON_IMAGE):
        print(
            f"\n⚠️  '{BUTTON_IMAGE}' not found!\n"
            f"   Please place retry_button.png in the same folder as this script and try again.\n"
        )
        return

    print("=" * 52)
    print(f"  {APP_NAME}  –  Auto Retry Button Clicker")
    print("=" * 52)
    print(f"  Hotkey  : {HOTKEY.upper()} to toggle ON / OFF")
    print(f"  Image   : {BUTTON_IMAGE}")

    print(f"  Tray    : lime dot = idle  │  red dot = scanning")
    print("  Right-click the tray icon to toggle or quit.\n")

    keyboard.add_hotkey(HOTKEY, toggle_running)
    threading.Thread(target=scan_loop, daemon=True).start()

    notify("Ready 🟢", f"AutoRetry is running. Press {HOTKEY.upper()} to start scanning.")

    # ── Build and run the tray icon in a dedicated daemon thread ─────────────
    # Windows native UI loops MUST be created and run in the same thread to
    # appear reliably. Running it in a thread lets Python's main thread catch Ctrl+C.
    def _run_tray_worker():
        global _tray_icon
        menu = pystray.Menu(
            pystray.MenuItem(
                lambda item: "Scanner: ON 🔴" if running else "Scanner: OFF 🟢",
                toggle_running,
                default=True,          # double-click activates this item
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(f"Quit {APP_NAME}", _quit_app),
        )
        _tray_icon = pystray.Icon(
            name   = APP_NAME,
            icon   = _make_dot_icon(IDLE_DOT_COLOR),
            title  = f"{APP_NAME}  —  IDLE 🟢",
            menu   = menu,
        )
        _tray_icon.run()

    threading.Thread(target=_run_tray_worker, daemon=True).start()

    # The main thread simply waits, running Python bytecode periodically
    # so that Ctrl+C (KeyboardInterrupt) can be successfully caught and processed.
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        _quit_app()

if __name__ == "__main__":
    main()
