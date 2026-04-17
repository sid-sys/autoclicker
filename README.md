# AutoRetry

A lightweight, high-performance image-recognition auto-clicker built in Python. Instead of blindly clicking coordinates, AutoRetry actively monitors your screen for a specific button or element (like a "Retry" or "Start" button) and clicks it the *instant* it appears. 

## Features
- **Instant Response**: Built with `mss` and OpenCV `matchTemplate` to scan the screen ~20 times per second with virtually zero delay and minimal CPU overhead.
- **Single-Key Toggle**: Tap the \` (backtick) key to magically toggle the scanner ON and OFF.
- **Visual Feedback**:
  - **Dynamic Mouse Cursor**: Turns 🔴 red when scanning, and 🟢 lime when paused.
  - **System Tray Icon**: Quietly sits in the system tray with live color-coded status.
  - **Click Counter**: Maintains a persistent Markdown log (`clickcounttracker.md`) of exactly how many times and when the button was clicked across all sessions.
- **Safe & Controllable**: Native Windows hooks run the tray icon in a dedicated daemon thread ensuring that `Ctrl+C` in your terminal is instantly respected.

## Requirements
- Windows OS (relies on Win32 API for cursor changes and tray integrations)
- Python 3+

## Installation
1. Clone this repository to your local machine.
2. Install the required Python dependencies:
   ```bash
   pip install opencv-python mss pyautogui win32api setcursor plyer pillow pystray keyboard
   ```
*(Note: Some of these utilize pywin32, ensure it's installed via `pip install pywin32` if you face issues).*

## How to Work It
1. **Target Image**: Take a screenshot of the button you want to click. Crop it down just to the button itself, and save it as `retry_button.png` in the same directory as the script.
2. **Run**:
   ```bash
   python auto_retry.py
   ```
3. **Usage**:
   - The scanner starts **idle** (lime cursor). 
   - Press the **\`** key (backtick, usually right below Esc) to activate the scanner. Your cursor will turn red.
   - You can leave it running in the background. It only clicks when your target image appears on screen. 
   - Press **\`** again to pause it.
   - To quit, either Right-Click the tray icon and hit Quit, or press `Ctrl + C` in the console.

## Safety Note
Auto-clicking software can sometimes conflict with anti-cheat methods in games. Use responsibly and ensure you understand the terms of service of the application you are automating.
