# Touch Morse Fingerprint System (Mark 1)

This repository contains the complete Mark 1 baseline system for the Touch Morse Fingerprint project. It includes the ESP32 firmware and the Raspberry Pi Python server/client bridge.

## System Architecture
- **ESP32**: Handles the physical AS608 fingerprint sensor, reads capacitive Morse touches (Dot, Dash, Control), and handles local authentication.
- **Raspberry Pi**: Runs the Python client bridge (`esp32_hardware_client.py`) and the V3 backend server (`prototype_v3_server.py`). Handles "Cloud" template matching via Socket.IO.

---

## 🚀 Step-by-Step Installation Guide (For any new Raspberry Pi)

### 1. Prerequisites (Hardware)
- 1x Raspberry Pi (tested on Pi 4 / Pi 5)
- 1x ESP32 Development Board
- 1x AS608 Optical Fingerprint Sensor (wired to ESP32 Serial2)
- 3x Capacitive Touch pads (wired to ESP32 Touch pins)
- USB Data Cable connecting ESP32 to Raspberry Pi

### 2. Flash the ESP32 Firmware
1. Open Arduino IDE on your PC.
2. Install the **Adafruit Fingerprint Sensor Library**.
3. Open `esp32_biats_firmware.ino`.
4. Select your ESP32 board and COM port.
5. Click **Upload**.

### 3. Setup the Raspberry Pi Environment
Open a terminal on your Raspberry Pi and run the following commands:

```bash
# Update system and install required packages
sudo apt update
sudo apt install python3 python3-pip python3-venv -y

# Create a virtual environment for the project
python3 -m venv ~/morse_env
source ~/morse_env/bin/activate

# Install the required Python libraries
pip install pyserial python-socketio aiohttp requests "Flask>=2.2.0" flask-socketio eventlet chromadb sentence-transformers
```

### 4. Build the AI Vector Database (First Time Only)
Before starting the server, you must build the local AI vector database. This script will automatically download the `Bio_ClinicalBERT` model from HuggingFace and generate the ChromaDB database.
```bash
source ~/morse_env/bin/activate
python3 build_database.py
```
This might take a few minutes depending on your internet connection (it downloads an 800MB AI model).

### 5. Running the System
You need to open two separate terminal windows on the Raspberry Pi.

**Terminal 1: Start the Backend Server**
```bash
source ~/morse_env/bin/activate
python3 prototype_v3_server.py
```

**Terminal 2: Start the Hardware Bridge**
```bash
source ~/morse_env/bin/activate
python3 esp32_hardware_client.py
```

### 5. Usage Commands (in Terminal 2)
With the client running, you can type the following commands and press Enter:
- `E` : Enroll a new fingerprint.
- `D` : Delete all fingerprints from the local ESP32 sensor.
- `L` : Lock the session (forces the ESP32 to scan for a fingerprint again).

### 6. Cloud Authentication Flow
If a finger is placed on the sensor that is NOT stored in the ESP32's local memory, the ESP32 will extract the 512-byte raw template and send it to the Raspberry Pi. The Pi uses a `difflib.SequenceMatcher` algorithm to fuzzy-match the template against the `enrolled_fingerprints.csv` database. If the similarity is `>= 35.0%`, access is granted!
