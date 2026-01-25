<div align="center">

<img src="akatsuki_logo.png" alt="Akatsuki Medical Logo" width="120" height="120"/>

# 暁 Akatsuki Medical Heart-Lung Machine

**Advanced Monitoring System for Cardiovascular Support**

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.0+-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)](https://opencv.org)
[![Arduino](https://img.shields.io/badge/Arduino-00979D?style=for-the-badge&logo=arduino&logoColor=white)](https://www.arduino.cc)


</div>

---

## 🎯 Overview

The Akatsuki Heart-Lung Machine Monitoring System is a sophisticated medical device prototype designed for real-time monitoring and control of cardiovascular support equipment. Combining computer vision, embedded systems, and modern GUI design, this system provides comprehensive oversight of critical patient parameters during cardiac surgery procedures.

<div align="center">

### 🖼️ Hardware Prototype

<img src="IMG20251203191026.jpg" alt="Heart-Lung Machine Hardware" width="600"/>

*Complete hardware assembly with integrated sensors and monitoring systems*

</div>


---

## ✨ Key Features

<table>
<tr>
<td width="50%" bgcolor="#f0f9ff">

### 📊 Real-Time Monitoring
- **Heart Rate Tracking** - Continuous cardiac rhythm analysis
- **Pressure Monitoring** - Blood pressure measurement (8-20 mmHg)
- **Temperature Control** - Precise thermal regulation (36.5-37.5°C)
- **Oxygen Saturation** - SPO2 level monitoring
- **Bubble Detection** - Air embolism prevention system

</td>
<td width="50%" bgcolor="#fef3f2">

### 🎮 Advanced Controls
- **Computer Vision** - Liquid level detection via camera
- **Automated Alerts** - Multi-parameter alarm system
- **Suction Control** - Remote pump activation
- **Serial Communication** - High-speed Arduino interface (115200 baud)
- **Event Logging** - Comprehensive activity tracking

</td>
</tr>
</table>

---

## 🏗️ System Architecture

```
╔════════════════════════╗
║   Camera Feed (CV)     ║  ← 🎥 Liquid Level Detection
║   OpenCV Processing    ║     HSV Color Analysis
╚═══════════╦════════════╝
            ║
            ║ Image Processing
            ▼
╔════════════════════════╗
║  Python Dashboard      ║  ← 🖥️ Tkinter GUI
║  (Main Controller)     ║     Real-time Visualization
╚═══════════╦════════════╝
            ║ Serial @ 115200 baud
            ▼
╔════════════════════════╗
║  Arduino Hardware      ║  ← 🔌 Sensors & Actuators
║  + Medical Sensors     ║     Heart Rate | Pressure | Temp
╚════════════════════════╝
```

---

## 🛠️ Technical Specifications

### Hardware Components

| Component | Specification | Function |
|-----------|--------------|----------|
| **Microcontroller** | Arduino (COM8) | Central processing and sensor management |
| **Heart Rate Sensor** | Optical/ECG | Cardiac rhythm monitoring (40-180 BPM) |
| **Pressure Transducer** | Medical-grade | Blood pressure measurement (8-20 mmHg) |
| **SPO2 Sensor** | Pulse oximeter | Oxygen saturation tracking (30-230 range) |
| **Temperature Sensor** | High-precision | Thermal monitoring (±0.1°C accuracy) |
| **Bubble Detector** | Ultrasonic | Air embolism prevention (threshold: 300) |
| **USB Camera** | 640x480 @ 30fps | Liquid level visual monitoring |
| **Alarm System** | Audio buzzer | Critical parameter alerts |
| **Suction Pump** | Medical-grade | Remote-controlled activation |

### Software Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.8+ | Core application logic |
| **OpenCV** | 4.0+ | Computer vision processing |
| **Tkinter** | Built-in | Modern GUI framework |
| **PySerial** | 3.5+ | Arduino communication |
| **Pillow** | 8.0+ | Image processing |
| **NumPy** | 1.20+ | Numerical computations |

---

## 📊 Monitored Parameters

### Critical Thresholds

<table>
<tr>
<td width="33%" align="center" bgcolor="#ecfdf5">

**💓 Heart Rate**

Normal: 40-180 BPM

Alert on deviation

</td>
<td width="33%" align="center" bgcolor="#fef2f2">

**🩸 Pressure**

Normal: 8-20 mmHg

Critical range monitoring

</td>
<td width="33%" align="center" bgcolor="#fffbeb">

**🌡️ Temperature**

Normal: 36.5-37.5°C

Precision thermal control

</td>
</tr>
<tr>
<td width="33%" align="center" bgcolor="#f0f9ff">

**🫁 SPO2**

Normal: 30-230

Oxygen saturation

</td>
<td width="33%" align="center" bgcolor="#faf5ff">

**💧 Bubble Value**

Threshold: >300

Air detection system

</td>
<td width="33%" align="center" bgcolor="#f0fdf4">

**🧪 Liquid Level**

40-60% range

Visual CV detection

</td>
</tr>
</table>

### Liquid Level Detection

The system employs advanced computer vision techniques for non-contact liquid level monitoring:

- **Color Detection**: Dual HSV range for red liquid identification
- **ROI Analysis**: Configurable region of interest (200-400px horizontal)
- **Threshold Zones**: 40% (low) to 60% (high) normal range
- **Real-time Feedback**: Visual indicators and Arduino communication

---

## 🚀 Installation & Setup

### Prerequisites

<table>
<tr>
<td width="50%" bgcolor="#fef3f2">

**📦 Required Software**
```bash
pip install opencv-python
pip install numpy
pip install pyserial
pip install pillow
```

</td>
<td width="50%" bgcolor="#f0f9ff">

**🔧 Hardware Setup**
- Arduino board connected via USB
- Camera device (index 0)
- Sensor array properly wired
- COM port configured (default: COM8)

</td>
</tr>
</table>

### Quick Start Guide

#### Step 1: Hardware Configuration

```bash
# Connect Arduino to computer
# Upload the Arduino sketch
# Verify COM port (Windows: Device Manager, Linux: ls /dev/tty*)
# Connect camera to USB port
```

#### Step 2: Software Configuration

Open `akatsuki_heartlung_monitor_gui.py` and configure:

```python
# Arduino Settings
ARDUINO_PORT = 'COM8'  # Update to your port
BAUD_RATE = 115200

# Camera Settings
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

# Liquid Detection ROI
ROI_X_START, ROI_X_END = 200, 400  # Adjust for your setup
Y_BOTTOM_INPUT = 100
Y_TOP_INPUT = 300
```

#### Step 3: Launch Application

```bash
python akatsuki_heartlung_monitor_gui.py
```

The system will:
- ✅ Initialize Arduino connection
- ✅ Start camera feed
- ✅ Launch monitoring dashboard
- ✅ Begin real-time data collection

---

## 🎨 User Interface

### Dashboard Layout

The Akatsuki interface features a modern, two-panel design:

**Left Panel - Camera Feed**
- Real-time video stream with overlay graphics
- Liquid level visualization with threshold lines
- Parameter status display (HR, Pressure, Level)
- Alarm status banner

**Right Panel - System Parameters**
- Heart Rate (💓) - BPM display
- Pressure (🩸) - mmHg measurement
- Bubble Value (💧) - Air detection
- SPO2 Value (🫁) - Oxygen saturation
- Temperature (🌡️) - Celsius reading
- Liquid Level (🧪) - Pixel position
- Suction Control (🔄) - Pump toggle button

### Color-Coded Alerts

| Status | Color | Meaning |
|--------|-------|---------|
| 🟢 Green | #00ff88 | Normal parameters |
| 🟠 Orange | #ffa726 | Warning - attention needed |
| 🔴 Red | #ff3d3d | Critical - immediate action required |

---

## 🔬 Computer Vision System

### Liquid Level Detection Algorithm

The system uses advanced HSV color space analysis:

```python
# Red liquid detection (dual HSV range)
LOWER_RED1 = [0, 120, 70]    # Lower red hue
UPPER_RED1 = [10, 255, 255]

LOWER_RED2 = [170, 120, 70]  # Upper red hue
UPPER_RED2 = [180, 255, 255]

# Morphological operations for noise reduction
kernel = 5x5
operations: MORPH_OPEN → MORPH_CLOSE
```

### Processing Pipeline

1. **Frame Acquisition** - Capture from USB camera
2. **ROI Extraction** - Isolate monitoring region
3. **Color Space Conversion** - BGR → HSV
4. **Threshold Application** - Dual-range red detection
5. **Noise Filtering** - Morphological operations
6. **Level Calculation** - Pixel analysis (highest point)
7. **Range Classification** - LOW / NORMAL / HIGH
8. **Arduino Communication** - Serial status update

---

## 🔔 Alert System

### Multi-Level Alarm Protocol

**🔴 Critical Alerts**
- Heart rate outside 40-180 BPM range
- Pressure deviation from 8-20 mmHg
- Temperature beyond 36.5-37.5°C limits
- Bubble detection below threshold (300)
- Liquid level HIGH or LOW status

**🟠 Warning Indicators**
- Connection loss (>3 seconds no data)
- SPO2 value anomalies
- Suction pump status changes

**Visual & Audio Feedback**
- On-screen alarm badge (top-right)
- Video overlay banner (bottom)
- Parameter card highlighting
- Event log entries with timestamps

---

## 📡 Communication Protocol

### Arduino Serial Format

**Status Message Structure:**
```
[STATUS] HR=120 P=15 Bval=450 Sval=150 T=37.0 Alarm=NO Suction=OFF
```

**Control Commands:**
```
1\n  → Enable suction pump
0\n  → Disable suction pump
```

**Level Status:**
```
1    → Liquid level NORMAL
0    → Liquid level OUT OF RANGE
```

---

## 🎯 Use Cases

<table>
<tr>
<td width="50%">

### Medical Applications
- Cardiac surgery monitoring
- Extracorporeal membrane oxygenation (ECMO)
- Cardiopulmonary bypass procedures
- Critical care patient monitoring
- Medical device testing

</td>
<td width="50%">

### Research & Development
- Medical device prototyping
- Computer vision algorithm testing
- Embedded systems integration
- Real-time monitoring system design
- Educational demonstrations

</td>
</tr>
</table>

---

## 🔒 Safety Features

- **Multi-Parameter Redundancy** - Continuous verification across all sensors
- **Immediate Alert System** - <100ms response time for critical events
- **Historical Tracking** - 50-point data history for trend analysis
- **Automatic Reconnection** - Resilient Arduino communication
- **Comprehensive Logging** - 20-event circular buffer with timestamps
- **Visual Confirmation** - Color-coded status on all parameters

---

<div align="center">

*暁 Dawn of a new era in cardiovascular monitoring*

</div>
