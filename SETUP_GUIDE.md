# Detailed Setup Guide

This guide provides step-by-step instructions for setting up the Morse Code Based ESP32 Communication System with LLM Integration.

## Table of Contents

1. [Hardware Assembly](#hardware-assembly)
2. [ESP32 Configuration](#esp32-configuration)
3. [Raspberry Pi Setup](#raspberry-pi-setup)
4. [Software Installation](#software-installation)
5. [Configuration & API Setup](#configuration--api-setup)
6. [Testing & Verification](#testing--verification)
7. [Troubleshooting](#troubleshooting)

---

## Hardware Assembly

### Required Components
- ESP32 WROOM microcontroller
- TTP223 Capacitive touch sensors (x2)
- Raspberry Pi 3 Model B
- OLED/LCD display module (128x32 recommended)
- USB cable (micro USB for ESP32, USB A for Pi)
- 5V DC power supply (2A minimum)
- Jumper wires and breadboard

### Wiring Diagram

```
ESP32 Pin Configuration:
├── GPIO 13 → TTP223 Sensor 1 (DOT input)
├── GPIO 14 → TTP223 Sensor 2 (DASH input)
├── GPIO 21 (SDA) → OLED/LCD SDA
├── GPIO 22 (SCL) → OLED/LCD SCL
├── GND → TTP223 GND, OLED GND
└── 3.3V → TTP223 VCC, OLED VCC

USB Serial Connection:
├── ESP32 Micro USB → Raspberry Pi USB (Data lines)
└── Both share GND

Raspberry Pi Pin Configuration:
├── GPIO 17 → Bluetooth RX (HC-05 optional)
├── GPIO 27 → Bluetooth TX (HC-05 optional)
└── I2C pins accessible via library for OLED
```

### Step-by-Step Assembly

1. **Prepare the breadboard**
   - Place ESP32 on breadboard in center
   - Install both TTP223 sensors (left and right sides)

2. **Connect touch sensors**
   ```
   Sensor 1 (DOT):
   - VCC → ESP32 3.3V
   - GND → ESP32 GND
   - OUT → ESP32 GPIO 13

   Sensor 2 (DASH):
   - VCC → ESP32 3.3V
   - GND → ESP32 GND
   - OUT → ESP32 GPIO 14
   ```

3. **Connect OLED display**
   ```
   SSD1306 OLED (I2C):
   - VCC → ESP32 3.3V or 5V (check module spec)
   - GND → ESP32 GND
   - SDA → ESP32 GPIO 21
   - SCL → ESP32 GPIO 22
   ```

4. **Connect to Raspberry Pi**
   - Use USB micro-to-USB-A cable
   - Connect ESP32 micro USB to Raspberry Pi USB port
   - This provides both power and serial communication

5. **Power the system**
   - Connect 5V power supply to Raspberry Pi
   - ESP32 draws power from Pi via USB
   - Verify all LEDs light up on ESP32

---

## ESP32 Configuration

### Install Arduino IDE and ESP32 Support

**Windows/Mac/Linux:**

1. Download Arduino IDE from https://www.arduino.cc/en/software
2. Install and launch Arduino IDE
3. Go to **File → Preferences**
4. In "Additional Board Manager URLs", add:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
5. Go to **Tools → Board → Boards Manager**
6. Search for "ESP32"
7. Install "ESP32 by Espressif Systems" (latest version)

### Install Required Libraries

In Arduino IDE, go to **Tools → Manage Libraries** and install:

```
- Arduino JSON (Benoit Blanchon)
- WiFi (Arduino)
- Wire (Arduino - built-in)
```

### Upload Morse Decoder Code

1. Download the Arduino code from `code/Arduino_code/morse_esp32.ino`
2. Open in Arduino IDE
3. Select board:
   - **Tools → Board → ESP32 → ESP32 WROOM DA Module**
4. Select serial port:
   - **Tools → Port → COM3** (Windows) or `/dev/ttyUSB0` (Linux)
5. Set baud rate:
   - **Tools → Upload Speed → 115200**
6. Click **Upload** button
7. Wait for "Done uploading" message

### Verify ESP32 Connection

1. Open Serial Monitor: **Tools → Serial Monitor**
2. Set baud rate to 115200
3. Reset ESP32 (press reset button)
4. You should see startup messages

---

## Raspberry Pi Setup

### Install Raspberry Pi OS

1. Download **Raspberry Pi Imager** from https://www.raspberrypi.com/software/
2. Insert microSD card into computer
3. In Imager:
   - Choose Device: Raspberry Pi 3B
   - Choose OS: Raspberry Pi OS (Lite or Desktop)
   - Choose Storage: microSD card
4. Click **Write**
5. Insert SD card into Raspberry Pi

### Initial Raspberry Pi Configuration

**First Boot:**

```bash
# SSH into Pi (default user: pi, password: raspberry)
ssh pi@raspberrypi.local

# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Python 3.7+
python3 --version  # Should be 3.7 or higher

# Install pip and git
sudo apt-get install python3-pip git -y

# Create project directory
mkdir -p ~/morse_project
cd ~/morse_project
```

### Enable Serial Communication

```bash
# Enable serial port (disable serial login console)
sudo raspi-config
# Select: Interface Options → Serial Port → No → Yes
# This enables ttyUSB0 for ESP32 communication

# Set permissions for serial port
sudo usermod -a -G dialout pi

# Reboot
sudo reboot
```

### Verify Serial Connection

```bash
# List connected USB devices
ls -la /dev/ttyUSB*

# You should see /dev/ttyUSB0

# Test serial connection
sudo apt-get install minicom
minicom -D /dev/ttyUSB0 -b 115200
# You should see ESP32 serial output
# Press Ctrl+A then X to exit
```

---

## Software Installation

### Clone Repository

```bash
cd ~/morse_project
git clone https://github.com/yourusername/morse-esp32-llm.git
cd morse-esp32-llm
```

### Create Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv env

# Activate virtual environment
source env/bin/activate  # On Windows: env\Scripts\activate

# Upgrade pip
pip install --upgrade pip
```

### Install Python Dependencies

```bash
# Install required packages
pip install -r requirements.txt

# Verify installation
python3 -c "import requests, serial, json; print('All imports successful')"
```

---

## Configuration & API Setup

### Set Up Perplexity AI API

1. **Create Perplexity Account**
   - Visit https://www.perplexity.ai/
   - Sign up for API access
   - Go to Settings → API

2. **Generate API Key**
   - Click "Create New API Key"
   - Copy the key (save securely)
   - Set billing and rate limits

3. **Configure Environment Variable**

   **Linux/Mac:**
   ```bash
   echo "export PERPLEXITY_API_KEY='sk-your-key-here'" >> ~/.bashrc
   source ~/.bashrc
   ```

   **Windows (PowerShell):**
   ```powershell
   [Environment]::SetEnvironmentVariable("PERPLEXITY_API_KEY", "sk-your-key-here", "User")
   ```

4. **Verify API Key**
   ```bash
   echo $PERPLEXITY_API_KEY  # Should print your key
   ```

### Update Configuration File

Edit `config.json`:

```json
{
  "serial": {
    "port": "/dev/ttyUSB0",
    "baudrate": 115200
  },
  "llm": {
    "api_key": "sk-your-actual-key-here",
    "model": "sonar-pro"
  },
  "morse": {
    "dot_threshold_ms": 500,
    "letter_pause_ms": 1000,
    "word_pause_ms": 2000
  }
}
```

---

## Testing & Verification

### Test 1: Serial Connection

```bash
python3 -c "
import serial
try:
    ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
    ser.close()
    print('✓ Serial connection successful')
except Exception as e:
    print(f'✗ Serial error: {e}')
"
```

### Test 2: API Connectivity

```bash
python3 -c "
import requests
import os

api_key = os.getenv('PERPLEXITY_API_KEY')
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}
data = {
    'model': 'sonar-pro',
    'messages': [{'role': 'user', 'content': 'Say hello'}],
    'max_tokens': 100
}

try:
    response = requests.post(
        'https://api.perplexity.ai/chat/completions',
        headers=headers,
        json=data,
        timeout=10
    )
    if response.status_code == 200:
        print('✓ API connection successful')
        print(f'Response: {response.json()[\"choices\"][0][\"message\"][\"content\"]}')
    else:
        print(f'✗ API error: {response.status_code}')
except Exception as e:
    print(f'✗ Connection error: {e}')
"
```

### Test 3: Morse Decoding

1. Open serial monitor on ESP32
2. Tap the DOT sensor (short press < 500ms)
3. You should see dots (·) in the serial output
4. Tap the DASH sensor (long press >= 500ms)
5. You should see dashes (-) in the output

### Test 4: Full System Test

```bash
# Activate virtual environment
source env/bin/activate

# Run main application
python3 python_codes/main.py

# Follow on-screen prompts
# Tap sensors in Morse code for "HELP" or "TEST"
# Monitor console for errors
```

### Expected Output

```
[INFO] Starting Morse Code LLM Communication System...
[INFO] Serial connection: /dev/ttyUSB0 @ 115200 baud
[INFO] LLM model: sonar-pro
[INFO] Waiting for Morse input...

[User taps: · · · · | (letter pause) | - · - · | (word pause)]

[INFO] Raw input detected: "HELP"
[INFO] Confidence: 98%
[INFO] Stage 1 correction: HELP (no changes needed)
[INFO] Sending to LLM...
[INFO] LLM Response: "I'll help you right away. Please let me know how I can assist."
[INFO] Latency: 4.52 seconds
[INFO] Displaying response on OLED...
```

---

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: ESP32 Not Detected
```
Error: "SerialException: COM port not available"
```

**Solution:**
1. Check USB cable is properly connected
2. Verify device appears in Device Manager (Windows) or `lsusb` (Linux)
3. Install CH340 driver if needed: https://ch340.com/
4. Try different USB port on Pi or computer

#### Issue 2: Serial Permission Denied
```
Error: "PermissionError: [Errno 13] Permission denied: '/dev/ttyUSB0'"
```

**Solution:**
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER

# Or use sudo
sudo python3 python_codes/main.py
```

#### Issue 3: API Key Invalid
```
Error: "401 Unauthorized" from Perplexity API
```

**Solution:**
1. Verify API key in `config.json`
2. Check API key is active in Perplexity dashboard
3. Ensure billing is enabled
4. Try creating new API key

#### Issue 4: OLED Display Not Showing
```
Error: "OLED display not responding"
```

**Solution:**
1. Verify I2C connections (SDA on GPIO 21, SCL on GPIO 22)
2. Check display address: `i2cdetect -y 1` (should show 0x3C)
3. Install I2C tools: `sudo apt-get install i2c-tools`
4. Verify display power (check for LEDs on OLED module)

#### Issue 5: Slow Latency
```
System response takes 20+ seconds
```

**Solution:**
1. Check internet connection: `ping 8.8.8.8`
2. Monitor Perplexity API status
3. Reduce max_tokens in config.json
4. Check Raspberry Pi CPU usage: `top`

#### Issue 6: Morse Decoding Errors
```
Decoded text doesn't match input
```

**Solution:**
1. Adjust `dot_threshold_ms` (default 500ms)
2. Ensure clear pause between letters (1+ seconds)
3. Check TTP223 sensor calibration
4. Review sensor output in Arduino Serial Monitor

---

## Next Steps

Once setup is complete:

1. **Read** [API_REFERENCE.md](API_REFERENCE.md) for code details
2. **Review** [TESTING_PROTOCOL.md](TESTING_PROTOCOL.md) for testing procedures
3. **Explore** code in `python_codes/` and `Arduino_code/`
4. **Customize** configuration in `config.json` for your hardware
5. **Deploy** to production with appropriate safety measures

---

## Support

For issues or questions:
- Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Review GitHub issues
- Contact: mithun@amrita.edu.in

---

**Last Updated:** May 2025
