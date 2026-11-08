"""Hand Gesture Control System (Handly)
Author: Rehan Khan
Description: Real-time hand gesture recognition for Windows master volume
             and presentation slide control using OpenCV, MediaPipe,
             PyAutoGUI, and PyCAW.
"""

import os
import sys
import time
import warnings
from ctypes import POINTER, cast

# Suppress background C++/TensorFlow & library warning messages
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
warnings.filterwarnings("ignore")

import cv2
import mediapipe as mp
import numpy as np
import pyautogui
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

# ----------------- Configuration & Settings -----------------
WINDOW_TITLE = "Handly - Gesture Control (by Rehan)"
CAMERA_INDEX = 0
GESTURE_COOLDOWN = 1.0       # Seconds between slide triggers
FEEDBACK_DURATION = 0.8      # Seconds to display action badge on HUD
PINCH_MIN_DIST = 20          # Pixel distance corresponding to 0% volume
PINCH_MAX_DIST = 175         # Pixel distance corresponding to 100% volume
MIN_VOLUME_CHANGE = 0.01     # Minimum change in scalar volume (1%) to update OS

# PyAutoGUI safety configuration
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


def init_audio_volume():
    """Safely initialize the Windows master audio endpoint.

    Compatible with both legacy and modern pycaw releases.
    Returns IAudioEndpointVolume pointer or None.
    """
    try:
        device = AudioUtilities.GetSpeakers()
        if device is None:
            print("[Warning] No default audio output device found.")
            return None

        # Modern pycaw (AudioDevice wrapper object)
        if hasattr(device, "EndpointVolume"):
            return device.EndpointVolume

        # Classic pycaw (COM MMDevice)
        if hasattr(device, "Activate"):
            interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            return cast(interface, POINTER(IAudioEndpointVolume))
    except Exception as exc:
        print(f"[Warning] Audio volume initialization failed ({exc}). Volume control disabled.")
    return None


def set_master_volume_scalar(volume_ctrl, percent):
    """Set the system volume linearly (0-100%) using scalar level."""
    if volume_ctrl is None:
        return
    try:
        scalar = max(0.0, min(1.0, float(percent) / 100.0))
        current = volume_ctrl.GetMasterVolumeLevelScalar()
        if abs(current - scalar) >= MIN_VOLUME_CHANGE:
            volume_ctrl.SetMasterVolumeLevelScalar(scalar, None)
    except Exception:
        pass


def get_master_volume_scalar(volume_ctrl):
    """Get current master volume as an integer percentage (0-100)."""
    if volume_ctrl is None:
        return 50
    try:
        return int(round(volume_ctrl.GetMasterVolumeLevelScalar() * 100))
    except Exception:
        return 50


def draw_hud_panel(img, x, y, w, h, alpha=0.6, color=(20, 20, 20)):
    """Draw a semi-transparent HUD panel strictly inside the specified ROI

    without dimming the rest of the camera frame.
    """
    h_img, w_img, _ = img.shape
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(w_img, x + w), min(h_img, y + h)

    if x2 > x1 and y2 > y1:
        roi = img[y1:y2, x1:x2]
        colored_rect = np.full_like(roi, color, dtype=np.uint8)
        blended = cv2.addWeighted(colored_rect, alpha, roi, 1 - alpha, 0)
        img[y1:y2, x1:x2] = blended


def main():
    # ---------------- Welcome Screen (Terminal) ----------------
    print("=" * 50)
    print("        HAND GESTURE CONTROL SYSTEM (HANDLY)")
    print("                 Developed by Rehan")
    print("=" * 50)
    print("\nControls & Gestures:")
    print("  - Pinch (Thumb + Index)      -> Volume Control (0 - 100%)")
    print("  - 1 Finger (Index Up)        -> Previous Slide (Left Arrow)")
    print("  - 2 Fingers (Peace / V)      -> Next Slide (Right Arrow)")
    print("  - Open Palm (4-5 Fingers)    -> Neutral / Standby")
    print("  - Fist (0 Fingers)           -> Idle / Rest")
    print("  - Press 'q' or ESC in window -> Quit Handly")
    print("=" * 50)

    # ---------------- Audio Setup ----------------
    volume_ctrl = init_audio_volume()
    current_vol_percent = get_master_volume_scalar(volume_ctrl)

    # ---------------- Camera Setup ----------------
    print("\nStarting camera...")
    # Prefer DirectShow on Windows for fast startup; fallback to default
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        print(f"\n[ERROR] Could not open webcam index {CAMERA_INDEX}.")
        print("Please check that your webcam is plugged in and not in use by another app.")
        return

    # Set camera resolution (standard 640x480 for smooth 30+ FPS)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # ---------------- MediaPipe Setup ----------------
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7,
    )
    mp_draw = mp.solutions.drawing_utils
    hand_draw_style = mp_draw.DrawingSpec(color=(0, 255, 128), thickness=2, circle_radius=2)
    conn_draw_style = mp_draw.DrawingSpec(color=(255, 128, 0), thickness=2)

    # Landmark indices
    # Tip IDs: Thumb: 4, Index: 8, Middle: 12, Ring: 16, Pinky: 20
    # PIP IDs: Index: 6, Middle: 10, Ring: 14, Pinky: 18

    # Timing and state variables
    last_slide_time = 0
    slide_locked = False
    active_action_badge = ""
    active_action_time = 0
    badge_color = (0, 255, 255)

    prev_frame_time = time.time()
    fps = 0.0

    print("Camera running. Show your hand to the camera.")
    print("Press 'q' or ESC to exit.\n")

    try:
        while True:
            success, frame = cap.read()
            if not success or frame is None:
                print("[Warning] Failed to grab camera frame. Exiting...")
                break

            # Natural horizontal mirror flip
            img = cv2.flip(frame, 1)
            h, w, _ = img.shape

            # Convert BGR to RGB for MediaPipe
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = hands.process(img_rgb)

            # Draw sleek semi-transparent HUD background
            draw_hud_panel(img, 10, 10, 310, 220, alpha=0.65, color=(15, 15, 20))
            cv2.rectangle(img, (10, 10), (320, 230), (70, 70, 80), 1)

            mode_text = "Status: Searching Hand"
            mode_color = (180, 180, 180)

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # Draw hand skeleton
                    mp_draw.draw_landmarks(
                        img,
                        hand_landmarks,
                        mp_hands.HAND_CONNECTIONS,
                        hand_draw_style,
                        conn_draw_style,
                    )

                    lm_list = []
                    for lm_id, lm in enumerate(hand_landmarks.landmark):
                        cx, cy = int(lm.x * w), int(lm.y * h)
                        lm_list.append((lm_id, cx, cy))

                    if len(lm_list) >= 21:
                        # Determine which fingers are extended UP (tip above PIP joint in y)
                        index_up = 1 if lm_list[8][2] < lm_list[6][2] else 0
                        middle_up = 1 if lm_list[12][2] < lm_list[10][2] else 0
                        ring_up = 1 if lm_list[16][2] < lm_list[14][2] else 0
                        pinky_up = 1 if lm_list[20][2] < lm_list[18][2] else 0

                        # Check thumb extension relative to index MCP
                        thumb_tip = np.array([lm_list[4][1], lm_list[4][2]])
                        index_mcp = np.array([lm_list[5][1], lm_list[5][2]])
                        thumb_extended_dist = float(np.linalg.norm(thumb_tip - index_mcp))

                        # Distance between thumb tip and index tip (pinch distance)
                        index_tip = np.array([lm_list[8][1], lm_list[8][2]])
                        pinch_dist = float(np.linalg.norm(index_tip - thumb_tip))

                        total_extended_fingers = index_up + middle_up + ring_up + pinky_up
                        current_time = time.time()

                        # ---------------- Gesture Classification ----------------
                        # Gesture 1: VOLUME CONTROL MODE
                        # When Ring and Pinky are curled DOWN, and thumb is extended
                        is_volume_pinch = (
                            ring_up == 0
                            and pinky_up == 0
                            and middle_up == 0
                            and thumb_extended_dist > 50
                            and pinch_dist < 210
                        )

                        if is_volume_pinch:
                            mode_text = "Mode: Volume Control"
                            mode_color = (0, 255, 128)

                            # Visual indicator for pinch line and endpoints
                            x1, y1 = lm_list[4][1], lm_list[4][2]
                            x2, y2 = lm_list[8][1], lm_list[8][2]
                            mid_x, mid_y = (x1 + x2) // 2, (y1 + y2) // 2

                            cv2.circle(img, (x1, y1), 8, (255, 0, 255), cv2.FILLED)
                            cv2.circle(img, (x2, y2), 8, (255, 0, 255), cv2.FILLED)
                            cv2.line(img, (x1, y1), (x2, y2), (255, 0, 255), 3)

                            # Touch detection (circle turns green when fully pinched)
                            if pinch_dist < PINCH_MIN_DIST + 10:
                                cv2.circle(img, (mid_x, mid_y), 9, (0, 255, 0), cv2.FILLED)

                            # Calculate linear volume percentage
                            current_vol_percent = int(
                                np.interp(pinch_dist, [PINCH_MIN_DIST, PINCH_MAX_DIST], [0, 100])
                            )
                            set_master_volume_scalar(volume_ctrl, current_vol_percent)

                            # Reset slide lock while in volume mode
                            slide_locked = False

                        # Gesture 2: NEXT SLIDE (2 fingers: Peace / V sign)
                        elif index_up == 1 and middle_up == 1 and ring_up == 0 and pinky_up == 0:
                            mode_text = "Gesture: 2 Fingers (Next)"
                            mode_color = (255, 200, 0)

                            if not slide_locked and (current_time - last_slide_time > GESTURE_COOLDOWN):
                                pyautogui.press("right")
                                last_slide_time = current_time
                                slide_locked = True
                                active_action_badge = "NEXT SLIDE >>"
                                active_action_time = current_time
                                badge_color = (0, 255, 255)

                        # Gesture 3: PREVIOUS SLIDE (1 finger: Index Up only)
                        elif index_up == 1 and middle_up == 0 and ring_up == 0 and pinky_up == 0:
                            mode_text = "Gesture: 1 Finger (Prev)"
                            mode_color = (0, 200, 255)

                            if not slide_locked and (current_time - last_slide_time > GESTURE_COOLDOWN):
                                pyautogui.press("left")
                                last_slide_time = current_time
                                slide_locked = True
                                active_action_badge = "<< PREV SLIDE"
                                active_action_time = current_time
                                badge_color = (0, 200, 255)

                        # Gesture 4: OPEN PALM (Neutral / Standby)
                        elif total_extended_fingers >= 4:
                            mode_text = "Mode: Standby (Open Palm)"
                            mode_color = (200, 200, 200)
                            # Unlock slide lock when hand returns to neutral
                            if current_time - last_slide_time > 0.4:
                                slide_locked = False

                        # Gesture 5: FIST / REST
                        elif total_extended_fingers == 0:
                            mode_text = "Mode: Idle (Fist)"
                            mode_color = (150, 150, 150)
                            if current_time - last_slide_time > 0.4:
                                slide_locked = False

                        else:
                            mode_text = f"Fingers: {total_extended_fingers}"
                            mode_color = (180, 180, 180)

            # ---------------- Draw HUD Elements ----------------
            # Title
            cv2.putText(
                img, "HANDLY GESTURES", (25, 36),
                cv2.FONT_HERSHEY_DUPLEX, 0.65, (255, 255, 255), 1
            )
            cv2.line(img, (25, 45), (305, 45), (90, 90, 100), 1)

            # Current Mode / Status
            cv2.putText(
                img, mode_text, (25, 75),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, mode_color, 2
            )

            # Volume Bar & Text
            cv2.putText(
                img, f"Volume: {current_vol_percent}%", (70, 120),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2
            )

            # Vertical Volume Bar
            bar_top = 95
            bar_bottom = 195
            bar_h = bar_bottom - bar_top
            fill_y = int(bar_bottom - (current_vol_percent / 100.0) * bar_h)

            cv2.rectangle(img, (25, bar_top), (55, bar_bottom), (100, 100, 110), 2)
            cv2.rectangle(img, (27, fill_y), (53, bar_bottom - 2), (0, 255, 0), cv2.FILLED)

            # Cooldown progress indicator
            now = time.time()
            elapsed_since_slide = now - last_slide_time
            if elapsed_since_slide < GESTURE_COOLDOWN:
                cd_ratio = elapsed_since_slide / GESTURE_COOLDOWN
                cd_width = int(cd_ratio * 160)
                cv2.putText(
                    img, "Cooldown:", (70, 150),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (160, 160, 160), 1
                )
                cv2.rectangle(img, (70, 158), (230, 168), (70, 70, 80), 1)
                cv2.rectangle(img, (71, 159), (70 + cd_width, 167), (0, 200, 255), cv2.FILLED)

            # Triggered Action Notification Badge
            if now - active_action_time < FEEDBACK_DURATION:
                # Pulsing / prominent notification badge
                cv2.rectangle(img, (68, 180), (280, 215), (0, 0, 0), cv2.FILLED)
                cv2.rectangle(img, (68, 180), (280, 215), badge_color, 2)
                cv2.putText(
                    img, active_action_badge, (80, 205),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, badge_color, 2
                )

            # FPS calculation and display
            curr_time = time.time()
            delta_time = curr_time - prev_frame_time
            prev_frame_time = curr_time
            if delta_time > 0:
                instant_fps = 1.0 / delta_time
                fps = 0.9 * fps + 0.1 * instant_fps if fps > 0 else instant_fps

            cv2.putText(
                img, f"FPS: {int(fps)}", (w - 110, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2
            )

            # Quit hint
            cv2.putText(
                img, "[Q] Quit", (w - 105, 55),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1
            )

            # Show frame
            cv2.imshow(WINDOW_TITLE, img)

            # Key and window state checks
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):  # 'q', 'Q', or ESC
                break

            # Handle user clicking the window close [X] button
            if cv2.getWindowProperty(WINDOW_TITLE, cv2.WND_PROP_VISIBLE) < 1:
                break

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("\nHandly gesture system closed cleanly. Thank you!")


if __name__ == "__main__":
    main()
