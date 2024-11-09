from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QTextEdit
from PyQt5 import QtCore
from PIL import Image
import sys, threading, time, pyautogui, cv2, random, mss, gc, os
import numpy as np

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.01

SCREENSHOT_CATCH = False

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class FishBot:
    def __init__(self, stop_event, log_signal):
        self.stop_event = stop_event
        self.log_signal = log_signal

        self.snapRegion = {"mon": 1, "top": 900, "left": 1250, "width": 32, "height": 32}
        self.castRegion = {"mon": 1, "top": 841, "left": 1524, "width": 25, "height": 25}
        self.recoverRegion = {"mon": 1, "top": 805, "left": 1525, "width": 24, "height": 24}
        self.fishRegion = {"mon": 1, "top": 782, "left": 1450, "width": 13, "height": 143}
        self.staminaRegion = {"mon": 1, "top": 784, "left": 1475, "width": 8, "height": 138}

        self.sct = mss.mss()

    def log(self, message):
        self.log_signal.emit(message)

    def screenGrab(self, region):
        IMG = None
        while IMG is None and not self.stop_event.is_set():
            try:
                IMG = self.sct.grab(region)
            except Exception as e:
                self.log(f"[Error] Unable to take screenshot {region}: {e}")
                time.sleep(0.1)
        return IMG

    def getFishBar(self):
        fishbarImg = self.screenGrab(self.fishRegion)
        if fishbarImg is None:
            return None
        fishbarImg = np.array(fishbarImg)
        foundFish = None
        try:
            foundFish = pyautogui.locate(
                resource_path('imgs/fishbar3.png'), fishbarImg, grayscale=True, confidence=0.5)
        except Exception as e:
            self.log(f"Error finding fish bar: {e}")
        if foundFish is None:
            return None
        _, top, _, _ = foundFish
        return top

    def needStamina(self):
        staminaImg = self.screenGrab(self.staminaRegion)
        if staminaImg is None:
            return False
        staminaImg = np.array(staminaImg)
        foundStam = None
        try:
            foundStam = pyautogui.locate(
                resource_path('imgs/stamina.png'), staminaImg, grayscale=True, confidence=0.7)
        except Exception as e:
            self.log(f"Error finding stamina: {e}")
        return foundStam is None

    def main(self):
        throneWindows = pyautogui.getWindowsWithTitle("TL 1")
        throneWindow = None
        for window in throneWindows:
            if "TL 1" in window.title:
                throneWindow = window
                break
        if throneWindow is None:
            self.log("Game window not found")
            return
        cv2.namedWindow("visuals", cv2.WINDOW_NORMAL)
        throneWindow.activate()

        q_count = 0
        wasCast = False
        CASTED = time.time()
        tracker = 0
        while not self.stop_event.is_set():

            animationSleepTime = 0.1 + (0.1 * random.random())
            if wasCast and time.time() - CASTED > 60:
                wasCast = False

            snapImg = self.screenGrab(self.snapRegion)
            if snapImg is None:
                break
            snapImg = np.array(snapImg)

            castImg = self.screenGrab(self.castRegion)
            if castImg is None:
                break
            castImg = np.array(castImg)

            foundQ = None
            try:
                foundQ = pyautogui.locate(
                    resource_path('imgs/Q2.png'), snapImg, grayscale=True, confidence=0.7)
            except Exception as e:
                self.log(f"Error finding Q: {e}")
            if foundQ:

                pyautogui.press('q')
                q_count += 1
                self.log(f"Pressed Q (Snap up with) {q_count} times")
                ActiveKey = "d"
                pyautogui.keyDown(ActiveKey)

                track_progress = []

                START = time.time()
                zero_start_time = None

                while not self.stop_event.is_set():

                    if time.time() - START > 5:
                        recoverImg = self.screenGrab(self.recoverRegion)
                        if recoverImg is None:
                            break
                        recoverImg = np.array(recoverImg)
                        foundF = None
                        try:
                            foundF = pyautogui.locate(
                                resource_path('imgs/F2.png'), recoverImg, grayscale=True, confidence=0.7)
                        except Exception as e:
                            self.log(f"Error finding F: {e}")
                        if foundF is None:
                            if SCREENSHOT_CATCH:
                                monitor = self.sct.monitors[1]
                                catchImg = self.sct.grab(monitor)
                                mss.tools.to_png(
                                    catchImg.rgb, catchImg.size, output=f"fish_caught_{q_count}.png")
                            self.log("Reeling in completed...")
                            tracker = 0
                            break

                    top = self.getFishBar()
                    if top is None:
                        continue

                    if len(track_progress) == 0:
                        track_progress.append(top)
                        continue
                    track_progress.append(top)

                    progress = track_progress[-1] - track_progress[-2]

                    if progress <= 0:
                        if zero_start_time is None:
                            zero_start_time = time.time()
                        elif time.time() - zero_start_time >= 0.03:

                            zero_start_time = None
                            track_progress = []
                            pyautogui.keyUp(ActiveKey)

                            ActiveKey = "a" if ActiveKey == "d" else "d"
                            pyautogui.keyDown(ActiveKey)
                    else:
                        zero_start_time = None

                    if self.needStamina():
                        pyautogui.keyUp(ActiveKey)
                        time.sleep(0.3 + animationSleepTime)
                        pyautogui.keyDown(ActiveKey)
                    time.sleep(animationSleepTime)

                pyautogui.keyUp(ActiveKey)
                time.sleep(5)
                wasCast = False
                continue

            foundF = None
            try:
                foundF = pyautogui.locate(
                    resource_path('imgs/F.png'), castImg, grayscale=True, confidence=0.7)
            except Exception as e:
                self.log(f"Error finding F: {e}")

            if not wasCast and foundF:
                pyautogui.press('f')
                self.log("Pressed F to cast float")
                tracker += 1
                time.sleep(8 + animationSleepTime)
                wasCast = True
                CASTED = time.time()

            if tracker >= 5:
                self.log("Bot has completed 5 cycles")
                self.stop_event.set()
                break

            time.sleep(0.4)


class BotUI(QMainWindow):
    log_signal = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Fishing Bot UI")
        self.setGeometry(200, 200, 400, 350)

        self.start_button = QPushButton("Start Bot", self)
        self.start_button.setGeometry(100, 20, 100, 40)

        self.stop_button = QPushButton("Stop Bot", self)
        self.stop_button.setGeometry(210, 20, 100, 40)
        self.stop_button.setEnabled(False)

        self.status_label = QLabel("Bot is stopped", self)
        self.status_label.setGeometry(20, 70, 360, 20)

        self.log_text = QTextEdit(self)
        self.log_text.setGeometry(20, 100, 360, 230)
        self.log_text.setReadOnly(True)

        self.bot_thread = None
        self.bot_running = False
        self.bot = None
        self.stop_event = threading.Event()

        self.log_signal.connect(self.append_log)

        self.start_button.clicked.connect(self.start_bot)
        self.stop_button.clicked.connect(self.stop_bot)

    def append_log(self, message):
        self.log_text.append(message)

    def start_bot(self):
        if not self.bot_running:
            self.bot_running = True
            self.status_label.setText("Bot is running...")
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)

            self.bot_thread = threading.Thread(target=self.run_bot)
            self.bot_thread.start()

    def stop_bot(self):
        if self.bot_running:
            self.bot_running = False
            self.status_label.setText("Stopping bot...")
            self.stop_event.set()
            self.bot_thread.join()
            self.status_label.setText("Bot is stopped")
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.stop_event.clear()

    def run_bot(self):
        self.bot = FishBot(self.stop_event, self.log_signal)
        self.bot.main()
        self.bot_running = False
        self.status_label.setText("Bot is stopped")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

def main():
    app = QApplication(sys.argv)
    window = BotUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
