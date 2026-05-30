# Troubleshooting Guide

This document provides solutions for common issues encountered when setting up or running the Morse Code Based ESP32 Communication System.

## Table of Contents

1. [Hardware Issues](#hardware-issues)
2. [Serial Communication Problems](#serial-communication-problems)
3. [Software and Dependencies](#software-and-dependencies)
4. [API and LLM Issues](#api-and-llm-issues)
5. [Morse Decoding Problems](#morse-decoding-problems)
6. [Display and Output Issues](#display-and-output-issues)
7. [Performance and Latency](#performance-and-latency)
8. [Getting Help](#getting-help)

---

## Hardware Issues

### Problem: ESP32 Not Powering On

**Symptoms:**
- No LED lights on ESP32
- Serial monitor shows nothing

**Solutions:**

1. **Check USB Power Supply**
   ```bash
   # Verify power with multimeter
   # Should read ~5V between GND and VCC
   # Check USB cable carries power properly
   ```

2. **Try Different USB Port**
   - Some Raspberry Pi USB ports provide limited power
   - Try alternate ports or USB hub with external power

3. **Check Micro-USB Cable**
   - Ensure cable is not data-only (should have 5 pins)
   - Try different cable known to work

4. **Reset ESP32**
   - Press the RESET button on ESP32 board
   - Wait 2 seconds and check for boot messages

### Problem: TTP223 Sensors Not Responding

**Symptoms:**
- Touch sensors don't register when pressed
- No input received in serial monitor

**Solutions:**

1. **Verify Wiring**
   ```
   Correct connections:
   - TTP223 VCC → ESP32 3.3V (not 5V!)
   - TTP223 GND → ESP32 GND
   - TTP223 OUT → GPIO 13 (DOT) or GPIO 14 (DASH)
   ```

2. **Check for Loose Connections**
   - Gently wiggle jumper wires to see if sensor responds
   - Re-seat wires firmly into breadboard

3. **Test Sensor Directly**
   ```cpp
   // Upload to ESP32 to test sensors directly
   void setup() {
     Serial.begin(115200);
     pinMode(13, INPUT);  // DOT sensor
     pinMode(14, INPUT);  // DASH sensor
   }
   
   void loop() {
     Serial.print("DOT: ");
     Serial.print(digitalRead(13));
     Serial.print(" DASH: ");
     Serial.println(digitalRead(14));
     delay(100);
   }
   ```
   - If either sensor always reads HIGH or LOW, replace it

4. **Verify Sensor Jumpers**
   - TTP223 has jumper for sensitivity (A/B modes)
   - Ensure jumper is in correct position for your setup

### Problem: OLED Display Not Showing Anything

**Symptoms:**
- Display is powered (brightness visible) but no text
- Display shows garbage/random characters

**Solutions:**

1. **Verify I2C Connections**
   ```bash
   # Check I2C device detection on Raspberry Pi
   i2cdetect -y 1
   
   # Should show device at 0x3C
   # If not found, check SDA (GPIO 21) and SCL (GPIO 22) connections
   ```

2. **Update I2C Address in Code**
   - If display shows at different address (e.g., 0x3F)
   - Update in Arduino code or Python config

3. **Test I2C Hardware**
   ```bash
   # Install I2C tools
   sudo apt-get install i2c-tools
   
   # Scan for devices
   i2cdetect -y 1
   ```

4. **Check Display Library**
   - Reinstall correct library for display type
   - SSD1306 (most common): https://github.com/adafruit/Adafruit_SSD1306

---

## Serial Communication Problems

### Problem: "SerialException: Port Already in Use"

**Symptoms:**
```
SerialException: COM3 is already open
```

**Solutions:**

1. **Close Arduino Serial Monitor**
   - Arduino IDE locks the port when monitor is open
   - Close the monitor window before running Python script

2. **Kill Processes Using Port**
   ```bash
   # Linux/Mac: Find process using port
   lsof /dev/ttyUSB0
   
   # Kill the process
   kill -9 <PID>
   
   # Windows: Check Device Manager, restart if locked
   ```

3. **Restart Raspberry Pi**
   ```bash
   sudo reboot
   ```

### Problem: "No Such File or Directory: /dev/ttyUSB0"

**Symptoms:**
```
FileNotFoundError: [Errno 2] No such file or directory: '/dev/ttyUSB0'
```

**Solutions:**

1. **Check USB Connection**
   ```bash
   # List all USB devices
   lsusb
   
   # Look for "CP210x" or "CH340" (depending on ESP32 board)
   ```

2. **Install CH340 Driver (if needed)**
   ```bash
   # Linux
   sudo apt-get install ch340-modules-dkms
   
   # macOS: Download from https://ch340.com/
   ```

3. **Find Correct Port**
   ```bash
   # List serial ports
   ls -la /dev/tty*
   
   # Might be /dev/ttyUSB0, /dev/ttyACM0, etc.
   # Update config.json with correct port
   ```

4. **Check Permissions**
   ```bash
   # Add user to dialout group
   sudo usermod -a -G dialout pi
   
   # Or run with sudo
   sudo python3 main.py
   ```

### Problem: "Connection Refused" or "Timeout"

**Symptoms:**
```
Serial timeout
OSError: [Errno 111] Connection refused
```

**Solutions:**

1. **Verify Baud Rate**
   - Default is 115200
   - Check config.json matches Arduino code

2. **Test Serial Connection**
   ```bash
   # Use minicom to test
   minicom -D /dev/ttyUSB0 -b 115200
   
   # Should see boot messages from ESP32
   ```

3. **Reset ESP32 Connection**
   - Unplug USB cable
   - Wait 5 seconds
   - Plug back in
   - Restart Python script

---

## Software and Dependencies

### Problem: "ModuleNotFoundError: No module named 'requests'"

**Symptoms:**
```
ModuleNotFoundError: No module named 'requests'
```

**Solutions:**

1. **Install Missing Package**
   ```bash
   # Activate virtual environment
   source env/bin/activate
   
   # Install package
   pip install requests
   
   # Or install all requirements
   pip install -r requirements.txt
   ```

2. **Check Python Version**
   ```bash
   python3 --version
   # Should be 3.7 or higher
   ```

3. **Verify Virtual Environment**
   ```bash
   which python3
   # Should show path within 'env' directory if activated correctly
   ```

### Problem: "ImportError: cannot import name 'Board' from 'board'"

**Symptoms:**
```
ImportError: cannot import name 'Board' from 'board'
```

**Solutions:**

1. **Install Adafruit Libraries**
   ```bash
   pip install board adafruit-circuitpython-oled adafruit-circuitpython-ssd1306
   ```

2. **Fix Import Statements**
   - Ensure imports match installed package names
   - Check for typos in import statements

---

## API and LLM Issues

### Problem: "401 Unauthorized" from Perplexity API

**Symptoms:**
```
HTTPError: 401 Client Error: Unauthorized for url: https://api.perplexity.ai/...
```

**Solutions:**

1. **Verify API Key**
   ```bash
   # Check if API key is set
   echo $PERPLEXITY_API_KEY
   
   # Should print your key, not blank
   ```

2. **Verify Key is Valid**
   - Log into Perplexity dashboard
   - Check API key is active
   - Ensure it hasn't expired

3. **Check Billing**
   - Verify billing is enabled in Perplexity settings
   - Check account balance/credit

4. **Test API Directly**
   ```bash
   curl -X POST "https://api.perplexity.ai/chat/completions" \
     -H "Authorization: Bearer $PERPLEXITY_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model":"sonar-pro","messages":[{"role":"user","content":"hello"}]}'
   ```

### Problem: "Connection Timeout" or "No Internet Connection"

**Symptoms:**
```
requests.exceptions.ConnectTimeout
requests.exceptions.ConnectionError
```

**Solutions:**

1. **Check Internet Connection**
   ```bash
   # Ping Google DNS
   ping 8.8.8.8
   
   # Should get responses, not timeouts
   ```

2. **Check WiFi on Raspberry Pi**
   ```bash
   # View connection status
   iwconfig
   
   # For Pi with WiFi adapter
   ```

3. **Verify API Endpoint**
   - Check that URL is correct in config.json
   - Verify API is not down (check Perplexity status page)

4. **Increase Timeout**
   - Edit `config.json`
   - Change `"timeout_sec": 15` to higher value (30 seconds)

### Problem: "Rate Limit Exceeded"

**Symptoms:**
```
429 Too Many Requests
```

**Solutions:**

1. **Check API Rate Limits**
   - Perplexity API has rate limits per account
   - Check dashboard for current usage

2. **Reduce Request Frequency**
   ```json
   // In config.json
   {
     "rate_limit_requests": true,
     "requests_per_minute": 20
   }
   ```

3. **Upgrade API Plan**
   - Contact Perplexity for higher limits
   - Or distribute requests over time

### Problem: "Model Not Found" or "Invalid Model Name"

**Symptoms:**
```
ValueError: Model 'sonar-pro' not found
```

**Solutions:**

1. **Verify Model Name**
   - Check Perplexity documentation for latest models
   - Common models: `sonar-pro`, `sonar`, `sonar-long`

2. **Update Model in Config**
   ```json
   {
     "llm": {
       "model": "sonar-pro"
     }
   }
   ```

3. **Test with Different Model**
   - Try alternative model available in your API plan

---

## Morse Decoding Problems

### Problem: Incorrect Morse Character Decoding

**Symptoms:**
- Input "·-" (A) shows as "B"
- Random characters appearing
- Mostly ? characters in output

**Solutions:**

1. **Adjust Dot/Dash Threshold**
   ```json
   // In config.json
   {
     "morse": {
       "dot_threshold_ms": 500
     }
   }
   ```
   - If too many dashes: lower to 400ms
   - If too many dots: raise to 600ms

2. **Increase Pause Timing**
   ```json
   {
     "morse": {
       "letter_pause_ms": 1000,
       "word_pause_ms": 2000
     }
   }
   ```
   - Ensure clear 1+ second pause between letters
   - Ensure clear 2+ second pause between words

3. **Test Sensor Timing**
   ```cpp
   // Upload to ESP32 to debug timing
   void setup() {
     Serial.begin(115200);
     pinMode(13, INPUT);  // DOT
     pinMode(14, INPUT);  // DASH
   }
   
   unsigned long startTime = 0;
   
   void loop() {
     if (digitalRead(13) == LOW && startTime == 0) {
       startTime = millis();
       Serial.print("DOT pressed at ");
       Serial.println(millis());
     }
     
     if (digitalRead(13) == HIGH && startTime > 0) {
       unsigned long duration = millis() - startTime;
       Serial.print("DOT released after ");
       Serial.print(duration);
       Serial.println("ms");
       startTime = 0;
     }
     
     delay(10);
   }
   ```

### Problem: Characters Show as "?" (Uncertain)

**Symptoms:**
- Output shows "C?O" instead of "CAR"
- Indicates uncertainty in character decoding

**Solutions:**

1. **Ensure Tap Clarity**
   - Tap sensors more deliberately
   - Avoid accidental taps or vibrations

2. **Clean Sensor Contacts**
   - Wipe sensor surface with dry cloth
   - Ensure no dust on capacitive touch area

3. **Calibrate TTP223**
   - TTP223 has a learning mode
   - Press and hold for 3 seconds until LED blinks (calibration)

4. **Reduce External Interference**
   - Move away from strong RF sources
   - Reduce electrical noise near sensors

### Problem: Morse Input Not Being Detected at All

**Symptoms:**
- No dots or dashes appearing in output
- System appears "dead"

**Solutions:**

1. **Verify Sensor Connections**
   ```cpp
   // Upload test code to ESP32
   void setup() {
     Serial.begin(115200);
     pinMode(13, INPUT);
     pinMode(14, INPUT);
   }
   
   void loop() {
     Serial.println(digitalRead(13)); // Should show 1 (HIGH)
     delay(100);
   }
   ```

2. **Check TTP223 Power**
   - Verify 3.3V on VCC pin
   - Use multimeter to confirm voltage

3. **Look for Sensor LEDs**
   - TTP223 has a small LED (usually green or red)
   - LED should turn on when sensor touched
   - If no LED response, sensor may be faulty

4. **Test with Serial Monitor**
   - Open Arduino Serial Monitor
   - Touch sensor directly
   - Should see immediate serial output

---

## Display and Output Issues

### Problem: Text Garbled or Unreadable on Display

**Symptoms:**
- OLED shows random characters or blocks
- Text overlaps or doesn't clear

**Solutions:**

1. **Clear Display Explicitly**
   ```python
   # In Python code before writing text
   display.fill(0)  # Clear all pixels
   display.show()    # Update display
   ```

2. **Verify Display Buffer**
   - Ensure display resolution matches config
   - Check 128x32 vs 128x64 setting

3. **Update Display Library**
   ```bash
   pip install --upgrade adafruit-circuitpython-ssd1306
   ```

### Problem: No Output to Display

**Symptoms:**
- Text not showing on OLED even though script runs
- Display stays blank

**Solutions:**

1. **Check Display Power**
   - Verify 3.3V on VCC
   - Verify GND connected

2. **Test Display Directly**
   ```python
   from board import SCL, SDA
   import busio
   from adafruit_ssd1306 import SSD1306_I2C
   
   i2c = busio.I2C(SCL, SDA)
   display = SSD1306_I2C(128, 32, i2c)
   
   # Test if display initializes
   print("Display initialized successfully")
   ```

3. **Enable I2C in Raspberry Pi**
   ```bash
   sudo raspi-config
   # Interface Options → I2C → Yes
   sudo reboot
   ```

---

## Performance and Latency

### Problem: Excessive Latency (>15 seconds)

**Symptoms:**
- System takes 15-30 seconds to respond
- Much longer than expected 4-11 seconds

**Solutions:**

1. **Check Network Speed**
   ```bash
   # Test internet connection
   speedtest-cli
   
   # Check latency to API
   ping api.perplexity.ai
   ```

2. **Monitor Raspberry Pi Resources**
   ```bash
   # Check CPU usage
   top
   
   # Check memory usage
   free -h
   
   # Check disk I/O
   iostat -x 1 5
   ```

3. **Reduce LLM Response Size**
   ```json
   {
     "llm": {
       "max_tokens": 256
     }
   }
   ```

4. **Check Perplexity API Status**
   - Visit Perplexity status page
   - May be experiencing degraded performance

### Problem: Raspberry Pi CPU Usage Very High (>90%)

**Symptoms:**
- System becomes slow and unresponsive
- High CPU usage in `top` command

**Solutions:**

1. **Kill Unnecessary Processes**
   ```bash
   # List processes by CPU usage
   ps aux --sort=-%cpu
   
   # Kill resource-heavy processes
   kill -9 <PID>
   ```

2. **Reduce Logging Detail**
   ```json
   {
     "logging": {
       "level": "WARNING"
     }
   }
   ```

3. **Disable Metrics Collection**
   ```json
   {
     "performance": {
       "measure_latency": false,
       "measure_accuracy": false
     }
   }
   ```

4. **Check for Memory Leaks**
   ```bash
   # Monitor memory over time
   watch -n 1 free -h
   
   # If memory grows continuously, restart service
   ```

---

## Getting Help

If you can't resolve the issue:

1. **Review Logs**
   ```bash
   # Check system logs
   tail -f morse_system.log
   
   # Arduino Serial Monitor output
   # (Tools → Serial Monitor in Arduino IDE)
   ```

2. **Enable Debug Mode**
   ```json
   {
     "logging": {
       "level": "DEBUG"
     }
   }
   ```

3. **Provide Debug Information**
   When asking for help, include:
   - Error message (full traceback)
   - Steps to reproduce
   - Output of: `python3 --version`
   - Output of: `pip list`
   - Arduino board type and driver version
   - Raspberry Pi model and OS version

4. **Contact Support**
   - Email: mithun@amrita.edu.in
   - Include debug information from above

5. **Check GitHub Issues**
   - Search existing issues
   - Create new issue with template provided

---

**Last Updated:** May 2025
