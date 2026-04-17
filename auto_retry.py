"""
auto_retry.py
=============
Auto-clicks a 'Retry' button found on screen using image recognition.

Controls:
  `       →  Toggle the scanner ON / OFF
  System tray icon (right-click to toggle / quit)

Visual feedback:
  • Tray icon: lime dot = idle, red dot = active
  • Cursor colour: lime when idle, red when scanning
  • Desktop notifications on state changes

Requirements:
  pip install pyautogui opencv-python keyboard plyer pillow pystray
"""

import time
import os
import re
import threading
import datetime
import ctypes
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

# Win32 OCR_ cursor IDs — we recolour ALL of them so every cursor is consistent
_OCR_NORMAL    = 32512   # IDC_ARROW
_OCR_IBEAM     = 32513
_OCR_WAIT      = 32514
_OCR_CROSS     = 32515
_OCR_UP        = 32516
_OCR_SIZENWSE  = 32642
_OCR_SIZENESW  = 32643
_OCR_SIZEWE    = 32644
_OCR_SIZENS    = 32645
_OCR_SIZEALL   = 32646
_ALL_OCR = [_OCR_NORMAL, _OCR_IBEAM, _OCR_WAIT, _OCR_CROSS, _OCR_UP,
            _OCR_SIZENWSE, _OCR_SIZENESW, _OCR_SIZEWE, _OCR_SIZENS, _OCR_SIZEALL]

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


# ──────────────────────────────────────────────
# Cursor helpers  (Win32 SetSystemCursor approach)
# ──────────────────────────────────────────────

def _make_arrow_image(r: int, g: int, b: int, size: int = 32) -> Image.Image:
    """Draw a filled arrow-pointer shape in the given colour (RGBA image)."""
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    s    = size
    # Classic arrow — hotspot at top-left corner (0, 0)
    arrow = [
        (0,    0),
        (0,    s - 8),
        (4,    s - 12),
        (8,    s - 5),
        (11,   s - 8),
        (7,    s - 16),
        (s//3, s//3),
    ]
    draw.polygon(arrow, fill=(r, g, b, 255))
    # Thin dark outline for visibility on any background
    draw.line([(0, 0), (0,    s - 8)],   fill=(0, 0, 0, 200), width=1)
    draw.line([(0, 0), (s//3, s//3)],    fill=(0, 0, 0, 200), width=1)
    return img


def _image_to_hcursor(img: Image.Image,
                      hotspot_x: int = 0, hotspot_y: int = 0) -> int:
    """Convert a PIL RGBA Image to a Windows HCURSOR via CreateIconIndirect."""
    user32 = ctypes.windll.user32
    gdi32  = ctypes.windll.gdi32
    w, h   = img.size

    # Swap R↔B channels to get Windows BGRA ordering
    r_ch, g_ch, b_ch, a_ch = img.split()
    bgra = Image.merge("RGBA", (b_ch, g_ch, r_ch, a_ch)).tobytes()

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize",          ctypes.c_uint32),
            ("biWidth",         ctypes.c_int32),
            ("biHeight",        ctypes.c_int32),   # negative = top-down
            ("biPlanes",        ctypes.c_uint16),
            ("biBitCount",      ctypes.c_uint16),
            ("biCompression",   ctypes.c_uint32),
            ("biSizeImage",     ctypes.c_uint32),
            ("biXPelsPerMeter", ctypes.c_int32),
            ("biYPelsPerMeter", ctypes.c_int32),
            ("biClrUsed",       ctypes.c_uint32),
            ("biClrImportant",  ctypes.c_uint32),
        ]

    class ICONINFO(ctypes.Structure):
        _fields_ = [
            ("fIcon",    ctypes.c_bool),
            ("xHotspot", ctypes.c_uint32),
            ("yHotspot", ctypes.c_uint32),
            ("hbmMask",  ctypes.c_void_p),
            ("hbmColor", ctypes.c_void_p),
        ]

    # --- colour DIB section ---
    bmi            = BITMAPINFOHEADER()
    bmi.biSize     = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.biWidth    = w
    bmi.biHeight   = -h          # negative → top-down
    bmi.biPlanes   = 1
    bmi.biBitCount = 32          # 32-bit BGRA

    dc    = user32.GetDC(None)
    pv    = ctypes.c_void_p()
    hbm_c = gdi32.CreateDIBSection(dc, ctypes.byref(bmi), 0,
                                    ctypes.byref(pv), None, 0)
    user32.ReleaseDC(None, dc)
    if not hbm_c:
        raise OSError("CreateDIBSection failed")
    ctypes.memmove(pv, bgra, len(bgra))

    # --- monochrome mask (all 0 → colour bitmap controls per-pixel alpha) ---
    hbm_m = gdi32.CreateBitmap(w, h, 1, 1,
                                ctypes.create_string_buffer(w * h // 8))

    ii          = ICONINFO()
    ii.fIcon    = False          # False = cursor (not icon)
    ii.xHotspot = hotspot_x
    ii.yHotspot = hotspot_y
    ii.hbmMask  = hbm_m
    ii.hbmColor = hbm_c

    hcursor = user32.CreateIconIndirect(ctypes.byref(ii))
    gdi32.DeleteObject(hbm_c)
    gdi32.DeleteObject(hbm_m)
    return hcursor


def _apply_cursor_color(r: int, g: int, b: int) -> None:
    """Replace every system cursor with a freshly drawn coloured arrow."""
    try:
        user32  = ctypes.windll.user32
        hcursor = _image_to_hcursor(_make_arrow_image(r, g, b))
        # SetSystemCursor takes ownership of the handle, so give it a fresh
        # copy for each cursor ID.
        # NOTE: CopyCursor is a C macro → the real DLL export is CopyIcon.
        for ocr_id in _ALL_OCR:
            user32.SetSystemCursor(user32.CopyIcon(hcursor), ocr_id)
        user32.DestroyCursor(hcursor)
        print(f"[{time.strftime('%H:%M:%S')}] 🖱️  Cursor → #{r:02X}{g:02X}{b:02X}")
    except Exception as e:
        print(f"[Cursor error] {e}")


def _restore_cursors() -> None:
    """Reload all system cursors from the current Windows cursor scheme."""
    ctypes.windll.user32.SystemParametersInfoW(
        0x0057,   # SPI_SETCURSORS
        0, None,
        0x03,     # SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
    )
    print(f"[{time.strftime('%H:%M:%S')}] 🖱️  Cursors restored to system scheme")


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
        # ACTIVE: red cursor — scanner is hunting for the Retry button
        _apply_cursor_color(*ACTIVE_DOT_COLOR)
        print(f"\n[{time.strftime('%H:%M:%S')}] ▶️  Scanner STARTED — cursor → 🔴 red  (Press {HOTKEY.upper()} to stop)")
        notify("Started ▶️", f"Now scanning. Press {HOTKEY.upper()} to stop.")
    else:
        # IDLE: lime cursor — scanner is paused
        _apply_cursor_color(*IDLE_DOT_COLOR)
        print(f"\n[{time.strftime('%H:%M:%S')}] ⏹️  Scanner STOPPED — cursor → 🟢 lime  (Press {HOTKEY.upper()} to resume)")
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
    """Cleanly shut down: restore cursors, print summary, stop tray."""
    _restore_cursors()
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
    print(f"  Cursor  : 🟢 lime when idle  │  🔴 red when scanner is active")
    print(f"  Tray    : lime dot = idle  │  red dot = scanning")
    print("  Right-click the tray icon to toggle or quit.\n")

    # Apply lime cursor — scanner starts as OFF
    _apply_cursor_color(*IDLE_DOT_COLOR)
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
