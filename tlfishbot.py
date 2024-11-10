from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QTextEdit, QLineEdit
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
    def __init__(self, stop_event, log_signal, work_time, rest_time):
        self.stop_event = stop_event
        self.log_signal = log_signal
        self.work_time = work_time
        self.rest_time = rest_time
        self.first_run = True

        screen_width, screen_height = pyautogui.size()

        self.log(f"Screen width: {screen_width}, Screen height: {screen_height}")

        snapRegion = {"top": 900, "left": 1250, "width": 32, "height": 32} # Q 
        castRegion = {"top": 841, "left": 1524, "width": 25, "height": 25} # F
        recoverRegion = {"top": 805, "left": 1525, "width": 24, "height": 24}
        fishRegion = {"top": 782, "left": 1450, "width": 13, "height": 143}
        staminaRegion = {"top": 784, "left": 1475, "width": 8, "height": 136}

        if (screen_width, screen_height) == (2560, 1080):
            snapRegion = {"top": 702, "left": 1252, "width": 30, "height": 30}
            castRegion = {"top": 649, "left": 1499, "width": 25, "height": 25}
            recoverRegion = {"top": 617, "left": 1499, "width": 24, "height": 24}
            fishRegion = {"top": 596, "left": 1432, "width": 13, "height": 129}
            staminaRegion = {"top": 596, "left": 1454, "width": 8, "height": 127}
        
        elif (screen_width, screen_height) == (1920, 1080):
            snapRegion = {"top": 675, "left": 940, "width": 24, "height": 24}
            castRegion = {"top": 630, "left": 1143, "width": 19, "height": 19}
            recoverRegion = {"top": 605, "left": 1144, "width": 18, "height": 18}
            fishRegion = {"top": 585, "left": 1087, "width": 10, "height": 107}
            staminaRegion = {"top": 587, "left": 1105, "width": 6, "height": 103}

        self.snapRegion = {"mon": 1, **snapRegion}
        self.castRegion = {"mon": 1, **castRegion}
        self.recoverRegion = {"mon": 1, **recoverRegion}
        self.fishRegion = {"mon": 1, **fishRegion}
        self.staminaRegion = {"mon": 1, **staminaRegion}

        self.sct = mss.mss()

    def log(self, message):
        self.log_signal.emit(message)

    def sleep_with_stop_check(self, duration):
        end_time = time.time() + duration
        while time.time() < end_time:
            if self.stop_event.is_set():
                break
            time.sleep(0.1)

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
            self.log(f"Unable to find fish bar: {e}")
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
            self.log(f"Unable to find stamina: {e}")
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
        start_time = time.time()
        next_rest_time = start_time + self.work_time

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
                self.log(f"Unable to find Q: {e}")
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
                            self.log(f"Unable to find F: {e}")
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
                        time.sleep(0.2 + animationSleepTime)
                        pyautogui.keyDown(ActiveKey)
                    time.sleep(animationSleepTime)

                pyautogui.keyUp(ActiveKey)
                time.sleep(5)
                wasCast = False
                current_time = time.time()

                if not self.first_run and current_time >= next_rest_time:
                    self.log(f"Wait {int(self.rest_time / 60)} minute...")
                    self.sleep_with_stop_check(self.rest_time)
                    start_time = time.time()
                    next_rest_time = start_time + self.work_time
                    self.log("Resuming work...")

                if self.first_run:
                    self.first_run = False
                
                continue

            foundF = None
            try:
                foundF = pyautogui.locate(
                    resource_path('imgs/F.png'), castImg, grayscale=True, confidence=0.7)
            except Exception as e:
                self.log(f"Unable to find F: {e}")

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
        self.setGeometry(200, 200, 400, 400)
        self.setFocus()

        self.start_button = QPushButton("Start Bot", self)
        self.start_button.setGeometry(100, 20, 100, 40)

        self.stop_button = QPushButton("Stop Bot", self)
        self.stop_button.setGeometry(210, 20, 100, 40)
        self.stop_button.setEnabled(False)

        self.status_label = QLabel("Bot is stopped", self)
        self.status_label.setGeometry(20, 70, 360, 20)

        self.work_time_label = QLabel("Work Time (minutes):", self)
        self.work_time_label.setGeometry(20, 100, 160, 20)
        self.work_time_input = QLineEdit(self)
        self.work_time_input.setGeometry(180, 100, 100, 20)
        self.work_time_input.setText("30")

        self.rest_time_label = QLabel("Rest Time (minutes):", self)
        self.rest_time_label.setGeometry(20, 130, 160, 20)
        self.rest_time_input = QLineEdit(self)
        self.rest_time_input.setGeometry(180, 130, 100, 20)
        self.rest_time_input.setText("5")

        self.log_text = QTextEdit(self)
        self.log_text.setGeometry(20, 160, 360, 200)
        self.log_text.setReadOnly(True)

        self.bot_thread = None
        self.bot_running = False
        self.bot = None
        self.stop_event = threading.Event()

        self.log_signal.connect(self.append_log)

        self.start_button.clicked.connect(self.start_bot)
        self.stop_button.clicked.connect(self.stop_bot)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_F7:
            self.log("F7 pressed")
            if self.bot_running:
                self.stop_bot()
            else:
                self.start_bot()

    def append_log(self, message):
        self.log_text.append(message)

    def start_bot(self):
        if not self.bot_running:
            self.bot_running = True
            self.status_label.setText("Bot is running...")
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)

            work_time = int(self.work_time_input.text()) * 60
            rest_time = int(self.rest_time_input.text()) * 60

            self.bot_thread = threading.Thread(target=self.run_bot, args=(work_time, rest_time))
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

    def run_bot(self, work_time, rest_time):
        self.bot = FishBot(self.stop_event, self.log_signal, work_time, rest_time)
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
