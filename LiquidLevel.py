# akatsuki_heartlung_monitor_gui.py
# Ultra-Modern Dashboard for Heart-Lung Machine Monitoring with Akatsuki Theme
# pip install opencv-python numpy pyserial tkinter pillow

import cv2
import numpy as np
import time
import serial
import threading
import tkinter as tk
from PIL import Image, ImageTk
from datetime import datetime
from collections import deque

# ========== ARDUINO SETTINGS ==========
ARDUINO_PORT = 'COM8'  # Change to your Arduino port
BAUD_RATE = 115200
SERIAL_TIMEOUT = 10

# ========== CAMERA SETTINGS ==========
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

# ========== LIQUID LEVEL DETECTION SETTINGS ==========
SCREEN_HEIGHT = 480
Y_BOTTOM_INPUT = 100
Y_TOP_INPUT = 300
ROI_X_START, ROI_X_END = 200, 400

# Color thresholds for red liquid
LOWER_RED1 = np.array([0, 120, 70])
UPPER_RED1 = np.array([10, 255, 255])
LOWER_RED2 = np.array([170, 120, 70])
UPPER_RED2 = np.array([180, 255, 255])

NORMAL_RANGE_TOP_PC = 0.60
NORMAL_RANGE_BOTTOM_PC = 0.40
MAINTENANCE_TIME_THRESHOLD = 1.0
MIRROR_CAMERA = True

# Pre-calculations for level detection
ROI_Y_END = SCREEN_HEIGHT - Y_BOTTOM_INPUT
ROI_Y_START = SCREEN_HEIGHT - Y_TOP_INPUT
BOTTLE_HEIGHT = ROI_Y_END - ROI_Y_START
LOW_Y_NORM = int(BOTTLE_HEIGHT * NORMAL_RANGE_BOTTOM_PC)
HIGH_Y_NORM = int(BOTTLE_HEIGHT * NORMAL_RANGE_TOP_PC)

# ========== GLOBALS ==========
arduino_conn = None
arduino_lock = threading.Lock()

# Arduino data structure matching LCD display
arduino_data = {
    "connected": False,
    "last_heartbeat": 0,
    "heart_rate": 0,
    "pressure": 0,
    "bubble_value": 0,
    "spo2_value": 0,
    "temperature": 0.0,
    "alarm_active": False,
    "suction_on": False
}

# Liquid level data
level_data = {
    "current_level_y": 0,
    "screen_level_y": ROI_Y_END,
    "range_text": "INITIALIZING",
    "level_color": (128, 128, 128),
    "alert_active": False,
    "is_maintained": False
}

event_log = deque(maxlen=20)
maintenance_start_time = None
last_sent_state = None

# Data history for trends
hr_history = deque(maxlen=50)
pressure_history = deque(maxlen=50)
temp_history = deque(maxlen=50)
level_history = deque(maxlen=50)


def log_event(message, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    event_log.append(f"[{timestamp}] {level}: {message}")


# ========== ARDUINO FUNCTIONS ==========
def open_arduino():
    global arduino_conn
    try:
        arduino_conn = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=SERIAL_TIMEOUT)
        time.sleep(2.5)
        arduino_conn.reset_input_buffer()
        arduino_conn.reset_output_buffer()
        log_event(f"Connected to Arduino on {ARDUINO_PORT}", "SUCCESS")
        arduino_data["connected"] = True
        arduino_data["last_heartbeat"] = time.time()
        return True
    except Exception as e:
        log_event(f"Could not connect to Arduino: {e}", "ERROR")
        arduino_conn = None
        return False


def serial_reader_thread():
    global arduino_conn
    while True:
        try:
            if arduino_conn and arduino_conn.is_open:
                if arduino_conn.in_waiting > 0:
                    with arduino_lock:
                        line = arduino_conn.readline().decode('utf-8', errors='ignore').strip()

                    if line:
                        # Parse STATUS line: [STATUS] HR=X P=Y Bval=Z Sval=W T=A Alarm=YES/NO Suction=ON/OFF
                        if line.startswith("[STATUS]"):
                            arduino_data["last_heartbeat"] = time.time()
                            arduino_data["connected"] = True

                            try:
                                # Parse HR
                                if "HR=" in line:
                                    hr_start = line.find("HR=") + 3
                                    hr_end = line.find(" ", hr_start)
                                    arduino_data["heart_rate"] = float(line[hr_start:hr_end])

                                # Parse Pressure
                                if "P=" in line:
                                    p_start = line.find("P=") + 2
                                    p_end = line.find(" ", p_start)
                                    arduino_data["pressure"] = float(line[p_start:p_end])

                                # Parse Bubble value
                                if "Bval=" in line:
                                    b_start = line.find("Bval=") + 5
                                    b_end = line.find(" ", b_start)
                                    arduino_data["bubble_value"] = int(line[b_start:b_end])

                                # Parse SPO2 value
                                if "Sval=" in line:
                                    s_start = line.find("Sval=") + 5
                                    s_end = line.find(" ", s_start)
                                    arduino_data["spo2_value"] = int(line[s_start:s_end])

                                # Parse Temperature
                                if "T=" in line:
                                    t_start = line.find("T=") + 2
                                    t_end = line.find(" ", t_start)
                                    arduino_data["temperature"] = float(line[t_start:t_end])

                                # Parse Alarm status
                                if "Alarm=" in line:
                                    arduino_data["alarm_active"] = "YES" in line

                                # Parse Suction status
                                if "Suction=" in line:
                                    arduino_data["suction_on"] = "ON" in line

                                # Store history
                                hr_history.append(arduino_data["heart_rate"])
                                pressure_history.append(arduino_data["pressure"])
                                temp_history.append(arduino_data["temperature"])

                            except Exception as e:
                                log_event(f"Parse error: {e}", "ERROR")

                        elif "ALARM:" in line:
                            log_event(line.replace("ALARM:", ""), "ALARM")
                        elif "[COM]" in line:
                            log_event(line, "INFO")
                else:
                    time.sleep(0.01)
            else:
                time.sleep(0.1)
        except Exception as e:
            if arduino_conn:
                log_event(f"Serial reader error: {e}", "ERROR")
            arduino_conn = None
            arduino_data["connected"] = False
            time.sleep(1)


def send_suction_command(state):
    global arduino_conn
    if arduino_conn is None or not arduino_conn.is_open:
        return False

    try:
        with arduino_lock:
            cmd = b'1\n' if state else b'0\n'
            arduino_conn.write(cmd)
            arduino_conn.flush()
        log_event(f"Suction command sent: {'ON' if state else 'OFF'}", "SUCCESS")
        return True
    except Exception as e:
        log_event(f"Serial write error: {e}", "ERROR")
        return False


def send_level_to_arduino(in_normal_range):
    """Send liquid level status to Arduino (reuses suction command for now)"""
    global last_sent_state

    if last_sent_state == in_normal_range:
        return  # Don't send duplicate states

    try:
        if arduino_conn and arduino_conn.is_open:
            with arduino_lock:
                if in_normal_range:
                    arduino_conn.write(b'1')  # NORMAL
                    log_event("Level: NORMAL sent to Arduino", "SUCCESS")
                else:
                    arduino_conn.write(b'0')  # OUT OF RANGE
                    log_event("Level: OUT OF RANGE sent to Arduino", "WARN")
            last_sent_state = in_normal_range
    except Exception as e:
        log_event(f"Level send error: {e}", "ERROR")


# ========== CV PROCESSING ==========
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)


# ========== MODERN DASHBOARD GUI ==========
class HeartLungMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("Akatsuki Medical - Heart-Lung Machine Monitor")
        self.root.geometry("1400x900")
        self.root.bind('<Configure>', self.resize_widgets)

        # Theme colors
        self.colors = {
            'bg': '#0a0e1a',
            'sidebar': '#151923',
            'card': '#1a1f2e',
            'text': '#e8eaed',
            'text_secondary': '#8b92a0',
            'accent': '#cc0000',
            'success': '#00ff88',
            'warning': '#ffa726',
            'danger': '#ff3d3d',
            'border': '#2d3548',
            'graph_bg': '#12161f',
            'shadow': '#000000'
        }

        # Main container
        self.main_container = tk.Frame(root, bg=self.colors['bg'])
        self.main_container.pack(fill=tk.BOTH, expand=True)

        self.create_interface()

        self.root.after(30, self.update_video)
        self.root.after(100, self.update_dashboard)

    def create_interface(self):
        self.create_background_pattern()
        self.create_top_nav()

        # Main content area - TWO PANELS ONLY
        content = tk.Frame(self.main_container, bg=self.colors['bg'])
        content.pack(fill=tk.BOTH, expand=True, padx=25, pady=(10, 25))

        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=2)  # Camera panel (larger)
        content.grid_columnconfigure(1, weight=1)  # Parameters panel

        # Left Panel: Camera
        self.create_camera_panel(content, 0, 0)

        # Right Panel: Parameters
        self.create_parameters_panel(content, 0, 1)

    def create_background_pattern(self):
        self.bg_canvas = tk.Canvas(self.main_container,
                                   bg=self.colors['bg'],
                                   highlightthickness=0)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.root.update_idletasks()
        self.draw_cube_pattern()

    def draw_cube_pattern(self):
        self.bg_canvas.delete("all")
        self.bg_canvas.configure(bg=self.colors['bg'])

        self.root.update_idletasks()
        width = self.bg_canvas.winfo_width()
        height = self.bg_canvas.winfo_height()

        if width <= 1 or height <= 1:
            return

        cube_size = 60
        row_offset = cube_size * 0.866
        col_offset = cube_size * 1.5

        for row in range(-2, int(height / row_offset) + 3):
            for col in range(-2, int(width / col_offset) + 3):
                x = col * col_offset + (row % 2) * (col_offset / 2)
                y = row * row_offset

                if -cube_size <= x <= width + cube_size and -cube_size <= y <= height + cube_size:
                    self.draw_isometric_cube(x, y, cube_size)

    def draw_isometric_cube(self, x, y, size):
        h = size * 0.866
        top = [x, y, x + size / 2, y + h / 2, x, y + h, x - size / 2, y + h / 2]
        left = [x - size / 2, y + h / 2, x, y + h, x, y + h + size / 2, x - size / 2, y + h + size / 2]
        right = [x, y + h, x + size / 2, y + h / 2, x + size / 2, y + h + size / 2, x, y + h + size / 2]

        self.bg_canvas.create_polygon(left, fill='#151923', outline='#2d3548', width=1)
        self.bg_canvas.create_polygon(right, fill='#12161f', outline='#2d3548', width=1)
        self.bg_canvas.create_polygon(top, fill='#1a1f2e', outline='#2d3548', width=1)

    def create_top_nav(self):
        nav = tk.Frame(self.main_container, bg=self.colors['sidebar'], height=75)
        nav.pack(fill=tk.X)
        nav.pack_propagate(False)

        left_frame = tk.Frame(nav, bg=self.colors['sidebar'])
        left_frame.pack(side=tk.LEFT, padx=30, pady=15)

        logo_container = tk.Frame(left_frame, bg=self.colors['accent'],
                                  width=45, height=45, relief=tk.FLAT)
        logo_container.pack(side=tk.LEFT, padx=(0, 15))
        logo_container.pack_propagate(False)

        tk.Label(logo_container, text="暁", font=('MS Gothic', 20, 'bold'),
                 bg=self.colors['accent'], fg='white').pack(expand=True)

        title_frame = tk.Frame(left_frame, bg=self.colors['sidebar'])
        title_frame.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(title_frame, text="AKATSUKI MEDICAL",
                 font=('Segoe UI', 15, 'bold'),
                 bg=self.colors['sidebar'], fg=self.colors['text'],
                 anchor='w').pack(anchor='w')
        tk.Label(title_frame, text="Heart-Lung Machine Monitoring System",
                 font=('Segoe UI', 9),
                 bg=self.colors['sidebar'], fg=self.colors['text_secondary'],
                 anchor='w').pack(anchor='w')

        right_frame = tk.Frame(nav, bg=self.colors['sidebar'])
        right_frame.pack(side=tk.RIGHT, padx=30, pady=15)

        conn_frame = tk.Frame(right_frame, bg=self.colors['sidebar'])
        conn_frame.pack(side=tk.RIGHT, padx=20)

        self.connection_indicator = tk.Label(conn_frame, text="●",
                                             font=('Arial', 14),
                                             bg=self.colors['sidebar'],
                                             fg=self.colors['danger'])
        self.connection_indicator.pack(side=tk.LEFT, padx=(0, 5))

        self.connection_label = tk.Label(conn_frame, text="Disconnected",
                                         font=('Segoe UI', 9),
                                         bg=self.colors['sidebar'],
                                         fg=self.colors['text_secondary'])
        self.connection_label.pack(side=tk.LEFT)

        self.time_display = tk.Label(right_frame, text="",
                                     font=('Segoe UI', 11),
                                     bg=self.colors['sidebar'],
                                     fg=self.colors['text'])
        self.time_display.pack(side=tk.RIGHT, padx=20)
        self.update_time()

    def create_card_frame(self, parent, row, col, rowspan=1, columnspan=1):
        shadow = tk.Frame(parent, bg=self.colors['shadow'], relief=tk.FLAT)
        shadow.grid(row=row, column=col, rowspan=rowspan, columnspan=columnspan,
                    sticky='nsew', padx=8, pady=8)

        card = tk.Frame(shadow, bg=self.colors['card'], relief=tk.FLAT, bd=0)
        card.place(x=3, y=3, relwidth=1, relheight=1)

        return card

    def create_camera_panel(self, parent, row, col):
        card = self.create_card_frame(parent, row, col)

        header = tk.Frame(card, bg=self.colors['card'], height=60)
        header.pack(fill=tk.X, padx=25, pady=(18, 8))
        header.pack_propagate(False)

        tk.Label(header, text="🎥 System Camera Feed",
                 font=('Segoe UI', 14, 'bold'),
                 bg=self.colors['card'],
                 fg=self.colors['text']).pack(side=tk.LEFT, anchor='w')

        self.alarm_badge = tk.Label(header, text="● NORMAL",
                                    font=('Segoe UI', 10, 'bold'),
                                    bg=self.colors['success'],
                                    fg='white',
                                    padx=18, pady=6)
        self.alarm_badge.pack(side=tk.RIGHT)

        video_container = tk.Frame(card, bg='#000000', relief=tk.FLAT)
        video_container.pack(fill=tk.BOTH, expand=True, padx=25, pady=(0, 25))

        self.video_container_ref = video_container
        self.video_label = tk.Label(video_container, bg='#000000')
        self.video_label.pack(expand=True)

    def create_parameters_panel(self, parent, row, col):
        card = self.create_card_frame(parent, row, col)

        header = tk.Frame(card, bg=self.colors['card'], height=60)
        header.pack(fill=tk.X, padx=25, pady=(18, 12))
        header.pack_propagate(False)

        tk.Label(header, text="📊 System Parameters",
                 font=('Segoe UI', 14, 'bold'),
                 bg=self.colors['card'],
                 fg=self.colors['text']).pack(anchor='w')

        # Parameters container with scrolling
        params_outer = tk.Frame(card, bg=self.colors['card'])
        params_outer.pack(fill=tk.BOTH, expand=True, padx=25, pady=(0, 25))

        # Main parameters display
        self.params_container = tk.Frame(params_outer, bg=self.colors['card'])
        self.params_container.pack(fill=tk.BOTH, expand=True)

        # Create parameter items
        self.param_widgets = {}

        parameters = [
            ("Heart Rate", "HR", "bpm", "💓"),
            ("Pressure", "P", "mmHg", "🩸"),
            ("Bubble Value", "B", "", "💧"),
            ("SPO2 Value", "S", "", "🫁"),
            ("Temperature", "T", "°C", "🌡️"),
            ("Liquid Level", "Level", "px", "🧪"),
            ("Suction Status", "Suction", "", "🔄")
        ]

        for title, key, unit, icon in parameters:
            widget_dict = self.create_parameter_item(self.params_container, title, unit, icon)
            widget_dict['frame'].pack(fill=tk.X, pady=8)
            self.param_widgets[key] = widget_dict

        # Suction control button
        control_frame = tk.Frame(self.params_container, bg=self.colors['card'])
        control_frame.pack(fill=tk.X, pady=15)

        self.suction_btn = tk.Button(control_frame,
                                     text="Enable Suction Pump",
                                     font=('Segoe UI', 11, 'bold'),
                                     bg=self.colors['success'],
                                     fg='white',
                                     activebackground=self.colors['warning'],
                                     relief=tk.FLAT,
                                     padx=20, pady=12,
                                     command=self.toggle_suction,
                                     cursor='hand2',
                                     bd=0)
        self.suction_btn.pack(fill=tk.X)

    def create_parameter_item(self, parent, title, unit, icon):
        item = tk.Frame(parent, bg=self.colors['card'], relief=tk.FLAT)
        item.configure(highlightbackground=self.colors['border'],
                       highlightcolor=self.colors['border'],
                       highlightthickness=1)

        content = tk.Frame(item, bg=self.colors['card'])
        content.pack(fill=tk.X, padx=15, pady=12)

        # Left side: icon and title
        left_frame = tk.Frame(content, bg=self.colors['card'])
        left_frame.pack(side=tk.LEFT, fill=tk.Y)

        icon_label = tk.Label(left_frame, text=icon,
                              font=('Segoe UI', 20),
                              bg=self.colors['card'],
                              width=2)
        icon_label.pack(side=tk.LEFT, padx=(0, 10))

        text_frame = tk.Frame(left_frame, bg=self.colors['card'])
        text_frame.pack(side=tk.LEFT, fill=tk.Y)

        title_label = tk.Label(text_frame, text=title,
                               font=('Segoe UI', 11, 'bold'),
                               bg=self.colors['card'],
                               fg=self.colors['text'],
                               anchor='w')
        title_label.pack(fill=tk.X, anchor='w')

        unit_label = tk.Label(text_frame, text=unit if unit else "status",
                              font=('Segoe UI', 8),
                              bg=self.colors['card'],
                              fg=self.colors['text_secondary'],
                              anchor='w')
        unit_label.pack(fill=tk.X, anchor='w')

        # Right side: value
        value_label = tk.Label(content, text="--",
                               font=('Segoe UI', 24, 'bold'),
                               bg=self.colors['card'],
                               fg=self.colors['text'],
                               anchor='e',
                               width=8)
        value_label.pack(side=tk.RIGHT, padx=(10, 0))

        return {
            'frame': item,
            'icon': icon_label,
            'title': title_label,
            'unit': unit_label,
            'value': value_label
        }

    def toggle_suction(self):
        if not arduino_data["connected"]:
            log_event("Cannot toggle suction: Arduino disconnected", "ERROR")
            return

        new_state = not arduino_data["suction_on"]
        send_suction_command(new_state)

    def update_time(self):
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_display.config(text=current_time)
        self.root.after(1000, self.update_time)

    def update_video(self):
        global maintenance_start_time

        ret, frame = cap.read()
        if ret:
            try:
                if MIRROR_CAMERA:
                    frame = cv2.flip(frame, 1)

                current_time = time.time()

                # ========== LIQUID LEVEL DETECTION LOGIC ==========
                roi = frame[ROI_Y_START:ROI_Y_END, ROI_X_START:ROI_X_END]

                if roi.size > 0:
                    # HSV color detection for red liquid
                    hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

                    # Detect red in both HSV ranges
                    mask1 = cv2.inRange(hsv_roi, LOWER_RED1, UPPER_RED1)
                    mask2 = cv2.inRange(hsv_roi, LOWER_RED2, UPPER_RED2)
                    liquid_mask = cv2.bitwise_or(mask1, mask2)

                    # Cleanup noise
                    kernel = np.ones((5, 5), np.uint8)
                    liquid_mask = cv2.morphologyEx(liquid_mask, cv2.MORPH_OPEN, kernel, iterations=1)
                    liquid_mask = cv2.morphologyEx(liquid_mask, cv2.MORPH_CLOSE, kernel, iterations=1)

                    # Find liquid pixels
                    liquid_pixels = np.where(liquid_mask == 255)

                    if liquid_pixels[0].size > 0:
                        # Find the HIGHEST white pixel (smallest Y value)
                        level_in_roi_from_top = np.min(liquid_pixels[0])
                        current_level_y = BOTTLE_HEIGHT - level_in_roi_from_top
                        screen_level_y = level_in_roi_from_top + ROI_Y_START
                    else:
                        # No liquid found
                        current_level_y = 0
                        screen_level_y = ROI_Y_END

                    # Check ranges
                    level_alert = False
                    level_color = (0, 255, 0)  # Green
                    range_text = "NORMAL"

                    if current_level_y > HIGH_Y_NORM:
                        level_alert = True
                        level_color = (0, 0, 255)  # Red
                        range_text = "HIGH"
                    elif current_level_y < LOW_Y_NORM:
                        level_alert = True
                        level_color = (0, 0, 255)  # Red
                        range_text = "LOW"

                    # Update maintenance flag
                    if range_text == "NORMAL":
                        if maintenance_start_time is None:
                            maintenance_start_time = current_time
                        elif (current_time - maintenance_start_time) >= MAINTENANCE_TIME_THRESHOLD:
                            level_data["is_maintained"] = True
                    else:
                        level_data["is_maintained"] = False
                        maintenance_start_time = None

                    # Update level data
                    level_data["current_level_y"] = current_level_y
                    level_data["screen_level_y"] = screen_level_y
                    level_data["range_text"] = range_text
                    level_data["level_color"] = level_color
                    level_data["alert_active"] = level_alert

                    level_history.append(current_level_y)

                    # Send to Arduino
                    in_normal_range = (range_text == "NORMAL")
                    send_level_to_arduino(in_normal_range)

                    # Draw visuals on frame
                    screen_high_y = ROI_Y_END - HIGH_Y_NORM
                    screen_low_y = ROI_Y_END - LOW_Y_NORM

                    # Draw level line
                    cv2.line(frame, (ROI_X_START, screen_level_y), (ROI_X_END, screen_level_y),
                             level_color, 3)

                    # Draw threshold lines
                    cv2.line(frame, (ROI_X_START - 20, screen_high_y), (ROI_X_START + 20, screen_high_y),
                             (0, 255, 255), 2)
                    cv2.line(frame, (ROI_X_START - 20, screen_low_y), (ROI_X_START + 20, screen_low_y),
                             (0, 255, 255), 2)

                    # Draw ROI rectangle
                    cv2.rectangle(frame, (ROI_X_START, ROI_Y_START), (ROI_X_END, ROI_Y_END),
                                  (255, 0, 0), 2)

                    # Draw labels
                    label_x_offset = ROI_X_START - 70 if MIRROR_CAMERA else ROI_X_END + 10
                    normal_mid_y = (screen_high_y + screen_low_y) // 2

                    cv2.putText(frame, "HIGH", (label_x_offset, screen_high_y - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                    cv2.putText(frame, "NORMAL", (label_x_offset, normal_mid_y),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    cv2.putText(frame, "LOW", (label_x_offset, screen_low_y + 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

                # Add status overlay
                overlay = frame.copy()
                cv2.rectangle(overlay, (10, 10), (300, 100), (26, 31, 47), -1)
                cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

                # Display key parameters on video
                cv2.putText(frame, f"HR: {arduino_data['heart_rate']:.0f} bpm",
                            (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 136), 2)
                cv2.putText(frame, f"P: {arduino_data['pressure']:.0f} mmHg",
                            (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 212, 255), 2)
                cv2.putText(frame, f"Level: {range_text}",
                            (20, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.6, level_color, 2)

                # Display alarm status if active
                if arduino_data["alarm_active"]:
                    alarm_overlay = frame.copy()
                    h, w = frame.shape[:2]
                    cv2.rectangle(alarm_overlay, (0, h - 60), (w, h), (61, 61, 255), -1)
                    cv2.addWeighted(alarm_overlay, 0.5, frame, 0.5, 0, frame)
                    cv2.putText(frame, "!!! ALARM ACTIVE !!!",
                                (w // 2 - 150, h - 25), cv2.FONT_HERSHEY_SIMPLEX,
                               1.0, (255, 255, 255), 3)

                # Resize and display
                if self.video_container_ref:
                    self.root.update_idletasks()
                    container_w = self.video_container_ref.winfo_width()
                    container_h = self.video_container_ref.winfo_height()

                    if container_w > 10 and container_h > 10:
                        img_h, img_w = frame.shape[:2]
                        img_aspect = img_w / img_h
                        container_aspect = container_w / container_h

                        if img_aspect > container_aspect:
                            new_w = container_w - 40
                            new_h = int(new_w / img_aspect)
                        else:
                            new_h = container_h - 40
                            new_w = int(new_h * img_aspect)

                        new_w = max(100, min(new_w, container_w - 20))
                        new_h = max(75, min(new_h, container_h - 20))

                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        img_resized = cv2.resize(frame_rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)
                        photo = ImageTk.PhotoImage(image=Image.fromarray(img_resized))
                        self.video_label.config(image=photo)
                        self.video_label.image = photo

            except Exception as e:
                log_event(f"Error in video loop: {e}", "ERROR")

        self.root.after(30, self.update_video)

    def update_dashboard(self):
        try:
            # Update connection status
            if arduino_data["connected"]:
                if (time.time() - arduino_data["last_heartbeat"]) > 3.0:
                    self.connection_indicator.config(fg=self.colors['warning'])
                    self.connection_label.config(text="No Data", fg=self.colors['warning'])
                else:
                    self.connection_indicator.config(fg=self.colors['success'])
                    self.connection_label.config(text="Connected", fg=self.colors['success'])
            else:
                self.connection_indicator.config(fg=self.colors['danger'])
                self.connection_label.config(text="Disconnected", fg=self.colors['danger'])

            # Update alarm badge
            if arduino_data["alarm_active"] or level_data["alert_active"]:
                self.alarm_badge.config(text="● ALARM", bg=self.colors['danger'])
            else:
                self.alarm_badge.config(text="● NORMAL", bg=self.colors['success'])

            # Update parameters
            params_data = [
                ("HR", f"{arduino_data['heart_rate']:.0f}",
                 arduino_data['heart_rate'] < 40 or arduino_data['heart_rate'] > 180),
                ("P", f"{arduino_data['pressure']:.0f}",
                 arduino_data['pressure'] < 8 or arduino_data['pressure'] > 20),
                ("B", f"{arduino_data['bubble_value']}",
                 arduino_data['bubble_value'] < 300),
                ("S", f"{arduino_data['spo2_value']}",
                 arduino_data['spo2_value'] < 30 or arduino_data['spo2_value'] > 230),
                ("T", f"{arduino_data['temperature']:.1f}",
                 arduino_data['temperature'] < 36.5 or arduino_data['temperature'] > 37.5),
                ("Level", f"{level_data['current_level_y']}",
                 level_data['alert_active']),
                ("Suction", "ON" if arduino_data["suction_on"] else "OFF", False)
            ]

            for key, value, is_bad in params_data:
                if key in self.param_widgets:
                    widget = self.param_widgets[key]
                    widget['value'].config(text=value)

                    if is_bad:
                        widget['value'].config(fg=self.colors['danger'])
                        widget['frame'].config(
                            highlightbackground=self.colors['danger'],
                            highlightcolor=self.colors['danger'],
                            highlightthickness=2
                        )
                    else:
                        widget['value'].config(fg=self.colors['success'])
                        widget['frame'].config(
                            highlightbackground=self.colors['border'],
                            highlightcolor=self.colors['border'],
                            highlightthickness=1
                        )

            # Update suction button
            if arduino_data["suction_on"]:
                self.suction_btn.config(text="Disable Suction Pump",
                                       bg=self.colors['danger'])
            else:
                self.suction_btn.config(text="Enable Suction Pump",
                                       bg=self.colors['success'])

        except Exception as e:
            log_event(f"Error updating dashboard: {e}", "ERROR")

        self.root.after(100, self.update_dashboard)

    def resize_widgets(self, event=None):
        if hasattr(self, 'bg_canvas'):
            if hasattr(self, 'resize_timer'):
                self.root.after_cancel(self.resize_timer)
            self.resize_timer = self.root.after(100, self._perform_resize)

    def _perform_resize(self):
        if hasattr(self, 'bg_canvas'):
            self.draw_cube_pattern()


# ========== MAIN ==========
if __name__ == "__main__":
    log_event("Akatsuki Heart-Lung Monitor Initializing", "INFO")
    log_event("暁 Dawn Protocol Active", "INFO")

    if open_arduino():
        reader_thread = threading.Thread(target=serial_reader_thread, daemon=True)
        reader_thread.start()
        log_event("Hardware interface established", "SUCCESS")
    else:
        log_event("Running in camera-only mode", "WARN")

    root = tk.Tk()
    app = HeartLungMonitor(root)

    try:
        root.mainloop()
    finally:
        if arduino_conn:
            arduino_conn.close()
        cap.release()
        log_event("System shutdown complete", "INFO")