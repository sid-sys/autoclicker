# AutoRetry

A lightweight, high-performance image-recognition auto-clicker built in Python. Instead of blindly clicking coordinates, AutoRetry actively monitors your screen for a specific button or element and clicks it the *instant* it appears. 

## 📖 The Story Behind AutoRetry

I was building a project on the Antigravity IDE, and it kept exiting with an "Agent terminated" error. I had to manually click "Retry" roughly 20 times a minute just to keep my workflow moving. It was completely killing my productivity and sanity, so I had to find a way around it. As a result, **AutoRetry** was born!

For context, this was the nightmare error that started it all:
> 🚫 **Agent terminated due to error**
> 
> You can prompt the model to try again or start a new conversation if the error persists.
> 
> See our troubleshooting guide for more help.
> 
> `[Dismiss]` &nbsp;&nbsp;&nbsp; `[Copy debug info]` &nbsp;&nbsp;&nbsp; **`[Retry]`**

## ✨ Features & Indicators
AutoRetry provides multiple layers of rich feedback so you always know exactly what it's doing:
- **Dynamic Mouse Cursor**: The actual Windows mouse cursor turns 🔴 **Red** when the scanner is actively running, and 🟢 **Lime** when idle. *(Note: You must have the custom lime and red dotted mouse cursors selected in your Windows Mouse settings for this effect to work properly).*
- **System Tray Icon**: Quietly sits in your taskbar system tray. A lime dot means idle, and a red dot means it's actively scanning.
- **Push Notifications**: Sends a clean Windows desktop notification when you toggle the script on or off.
- **Click Counter Log**: Maintains a persistent Markdown log (`clickcounttracker.md`) of exactly how many times and when the button was successfully clicked across all your sessions.

## ⚙️ Prerequisites
- **Windows OS** (relies on Win32 API for cursor changes and tray integrations)
- **Python 3.x**

## 🚀 Installation & Execution

1. **Clone this repository** to your local machine.
2. **Install the required Python dependencies**:
   ```bash
   pip install opencv-python mss pyautogui win32api setcursor plyer pillow pystray keyboard
   ```
   *(Note: Some of these utilize pywin32, ensure it's installed via `pip install pywin32` if you face issues).*

3. **Set your Target Image**: Take a screenshot of the button you want to click. Crop it tightly down just to the button itself, and save it as `retry_button.png` in the same directory as the script.

4. **Run the script**:
   Open a terminal in the folder and run:
   ```bash
   python auto_retry.py
   ```

## 🎮 How to Use
- The scanner starts **idle** (represented by a lime cursor/tray icon). 
- **Toggle ON/OFF**: Press the **ESC** key to activate the scanner. Your cursor and tray icon will turn red.
- You can leave it running in the background. It only clicks when your target image appears on screen. 
- Press **ESC** again to pause it.
- **To Quit**: Either right-click the system tray dot icon and hit "Quit", or press `Ctrl + C` in the console.

---
*Built to save your sanity, one retry at a time.*
