# Handly - Hand Gesture Control System

Handly is a computer vision application that allows you to control system volume and presentation slides using intuitive hand gestures through your webcam in real-time. Built with Python, OpenCV, MediaPipe, PyAutoGUI, and PyCAW.

Developed by **Rehan Khan**.

---

## Features

- **Pinch Volume Control**: Smoothly adjust your Windows master volume by pinching your thumb and index finger.
- **Slide Navigation**: Move forward or backward in PowerPoint, Google Slides, PDF presentations, or browsers using simple finger gestures.
- **Real-Time Hand Tracking**: Powered by Google MediaPipe Hands for high accuracy and low latency.
- **HUD & Visual Feedback**: Crisp on-screen overlay displaying current mode, finger count, volume percentage bar, and gesture triggers.
- **Mirror Mode**: Naturally mirrored camera view for seamless real-time hand-eye coordination.
- **Clean Window Controls**: Exit anytime with `q`, `ESC`, or by clicking the window close button.

---

## Gestures Guide

| Gesture | Action | Description |
| :--- | :--- | :--- |
| **Pinch (Thumb + Index)** | **Volume Control** | Extend thumb and index finger while keeping other fingers curled. Vary distance to adjust volume (0% - 100%). |
| **1 Finger (Index Up)** | **Previous Slide** | Raise only your index finger to trigger `Left Arrow` (Previous Slide). |
| **2 Fingers (Peace / V)** | **Next Slide** | Raise index and middle fingers to trigger `Right Arrow` (Next Slide). |
| **Open Palm (4-5 Fingers)** | **Neutral** | Standby mode without triggering actions. |
| **Fist (0 Fingers)** | **Idle / Rest** | Resting hand position. |

---

## Prerequisites

- **Operating System**: Windows 10 or Windows 11
- **Python**: 3.10 or 3.11 recommended
- **Webcam**: Built-in or external USB webcam

---

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/rehankpathan/handly.git
   cd handly
   ```

2. **Create and activate a virtual environment (optional but recommended)**:
   ```bash
   python -m venv venv
   # On Windows PowerShell:
   .\venv\Scripts\Activate.ps1
   # On Windows Command Prompt:
   venv\Scripts\activate.bat
   ```

3. **Install the dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## Usage

Run the script directly with Python:

```bash
python handly.py
```

- Position your hand comfortably within the webcam's field of view.
- To switch slides, make sure your presentation window (e.g. PowerPoint, Google Slides, or PDF) is in the background or active while Handly runs.
- Press **q** or **ESC** in the camera window to quit.

---

## Packaging into a Standalone `.exe`

To build an executable using PyInstaller:

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. Build using the provided spec file:
   ```bash
   pyinstaller handly.spec
   ```

3. The standalone `.exe` will be generated in the `dist/` directory.

---

## Tech Stack

- [Python](https://www.python.org/)
- [OpenCV (cv2)](https://opencv.org/) - Video capture and image processing
- [MediaPipe](https://developers.google.com/mediapipe) - High-fidelity hand landmark detection
- [PyAutoGUI](https://pyautogui.readthedocs.io/) - Automated keyboard keystrokes
- [PyCAW](https://github.com/AndreMiras/pycaw) - Windows Core Audio API interface
- [NumPy](https://numpy.org/) - Landmark math and linear interpolation

---

## Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/rehankpathan/handly/issues).

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
