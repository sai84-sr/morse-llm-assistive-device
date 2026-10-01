import time
import json
import base64
import csv
import os
import difflib
import queue
import threading
import socketio
import serial
import serial.tools.list_ports

# Linux-only: needed to disable HUPCL (the kernel feature that resets the ESP32 on port open)
try:
    import termios
    HAS_TERMIOS = True
except ImportError:
    HAS_TERMIOS = False  # Windows fallback

# ---------------------------------------------------------
# ESP32 to BIATS V3 Server Bridge (Hardware Prototype)
# ---------------------------------------------------------
# This script runs on the Raspberry Pi (or your Laptop).
# It listens to the physical ESP32 via USB Serial, reads the
# decoded Morse text, and sends it instantly to your V3 Server.
# Now completely Event-Driven using Socket.IO for Biometrics!
# ---------------------------------------------------------

sio = socketio.Client()
SERVER_URL = 'http://127.0.0.1:5055' 

BAUD_RATE = 115200

# Global serial handle so Socket.IO callbacks can write to it
esp32_serial = None

# ── SYNC QUEUE (prevents flooding ESP32 with simultaneous syncs) ──────────────
# The ESP32's finger.storeModel() blocks ~500ms per patient. Sending all syncs
# at once means the ESP32 is frozen and can't read keyboard commands like D/E.
# This queue sends one sync at a time, with a 2-second gap between them.
_sync_queue = queue.Queue()

def _sync_worker():
    """Background thread: dispatches sync commands one-by-one with a delay."""
    while True:
        item = _sync_queue.get()  # Blocks until an item is available
        if esp32_serial:
            esp32_serial.write(item['cmd'].encode())
            esp32_serial.flush()
            print(item['msg'])
            time.sleep(0.8)  # Give ESP32 plenty of time to finish storeModel() before next sync
        _sync_queue.task_done()

# Start the sync worker as a daemon thread
threading.Thread(target=_sync_worker, daemon=True).start()

# ── SOCKET.IO EVENTS ─────────────────────────────────────

@sio.event
def connect():
    print(f"[NETWORK] Successfully connected to V3 Backend Server at {SERVER_URL}")
    print("[FP_SYNC] Startup sync is disabled so we can test Cloud Authentication!")
    # sio.emit('fp_request_full_sync')  # Catch up on anything missed while offline

@sio.event
def disconnect():
    print("[NETWORK] Disconnected from server.")

@sio.on('new_request')
def on_new_request(data):
    # This receives the translation back from the server (Intent, Triage, etc.)
    print(f"\n<<< [FROM SERVER] Triage: {data.get('triage')} | Intent: {data.get('intent')}")
    print(f"    Full Sentence: {data.get('rag_sentence')}\n")

@sio.on('fp_push')
def on_fp_push(data):
    """Triggered instantly when ANY bed uploads a new fingerprint template.
    Queues the sync so the ESP32 isn't flooded with simultaneous commands."""
    if not esp32_serial:
        return
        
    if data.get('deleted'):
        _sync_queue.put({
            'cmd': f"FP_DELETE:{data['patient_id']}\n",
            'msg': f"[FP_SYNC] Pushed DELETE command for patient {data['patient_id']} to this bed."
        })
    else:
        _sync_queue.put({
            'cmd': f"FP_SYNC_JSON:{json.dumps(data)}\n",
            'msg': f"[FP_SYNC] Pushed TEMPLATE + PARAMS for patient {data['patient_id']} to this bed."
        })


# ── MAIN LOOP ────────────────────────────────────────────

def get_esp32_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if 'USB' in port.device or 'ACM' in port.device or 'COM' in port.device:
            return port.device
    return None

def main():
    global esp32_serial
    print("--- Starting ESP32 Hardware Prototype Bridge ---")
    
    ESP32_PORT = get_esp32_port()
    if not ESP32_PORT:
        print("[ERROR] Could not find any plugged in ESP32 (Checked USB/ACM/COM).")
        print("Are you sure the ESP32 is plugged in via USB?")
        return
        
    # Connect to the physical ESP32 first
    print(f"[HARDWARE] Connecting to ESP32 on port {ESP32_PORT} at {BAUD_RATE} baud...")
    try:
        # ── STEP 1: Disable HUPCL at the Linux kernel level ──────────────────
        # HUPCL (Hang Up on Close) is a kernel tty feature that asserts DTR/RTS
        # every time a serial port is opened. On this Pi, this resets the ESP32
        # into Download Mode before Python can even connect.
        # We MUST disable it at the OS level BEFORE pyserial opens the port.
        if HAS_TERMIOS:
            try:
                fd = os.open(ESP32_PORT, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
                attrs = termios.tcgetattr(fd)
                attrs[2] &= ~termios.HUPCL  # Clear the HUPCL bit
                termios.tcsetattr(fd, termios.TCSANOW, attrs)
                os.close(fd)
            except Exception:
                pass  # If it fails, proceed anyway

        # ── STEP 2: Open serial port without touching DTR/RTS ─────────────────
        esp32_serial = serial.Serial(ESP32_PORT, BAUD_RATE, timeout=1, dsrdtr=False)
        esp32_serial.setDTR(False)
        esp32_serial.setRTS(False)
        
        time.sleep(0.5)  # Let the connection stabilize
        esp32_serial.reset_input_buffer()  # Clear any leftover bytes

        print("[HARDWARE] ESP32 Connected! Listening for Morse touches...\n")
        
        print("[KEYBOARD] You can type 'E', 'D', or 'L' and press Enter to send commands to the ESP32!\n")
        
    except Exception as e:
        print(f"[ERROR] Could not open Serial port {ESP32_PORT}: {e}")
        print("Are you sure the ESP32 is plugged in via USB?")
        return

    # Connect to the V3 server
    try:
        sio.connect(SERVER_URL)
    except Exception as e:
        print(f"[ERROR] Could not connect to V3 Server: {e}")
        print("Please make sure 'prototype_v3_server.py' is running!")
        esp32_serial.close()
        return

    import sys
    
    def keyboard_thread():
        while True:
            try:
                cmd = sys.stdin.readline()
                if cmd:
                    clean_cmd = cmd.strip()
                    if clean_cmd:
                        # If user types D to wipe the sensor, ALSO flush the sync queue!
                        # Otherwise pending syncs will immediately re-load fingerprints
                        # and the ESP32 will be busy (fpState != IDLE) when the user touches.
                        if clean_cmd.upper() == 'D':
                            flushed = 0
                            while not _sync_queue.empty():
                                try:
                                    _sync_queue.get_nowait()
                                    _sync_queue.task_done()
                                    flushed += 1
                                except Exception:
                                    break
                            if flushed:
                                print(f"[FP_SYNC] Flushed {flushed} pending sync(s) from queue (sensor wiped).")

                        # If user types E to enroll, wait 2s for the AS608 sensor to
                        # fully settle after any previous D/sync flash write operations.
                        # Without this delay, the sensor returns NOFINGER immediately
                        # and enrollment gets stuck at 'Step 1: Place finger on sensor...'
                        if clean_cmd.upper() == 'E':
                            print("[FP_SYNC] Waiting 2s for sensor to settle before enrollment...")
                            time.sleep(2.0)

                        print(f"\n[DEBUG] Forwarding command '{clean_cmd}' to ESP32!")
                        esp32_serial.write((clean_cmd + "\n").encode())
                        esp32_serial.flush()
            except Exception:
                pass
                
    threading.Thread(target=keyboard_thread, daemon=True).start()

    # Main Read Loop
    try:
        while True:
            # 2. Check if the ESP32 sent us data
            if esp32_serial.in_waiting > 0:
                raw_data = esp32_serial.readline()
                try:
                    decoded_text = raw_data.decode('utf-8', errors='ignore').strip()
                except Exception:
                    continue # Ignore garbled serial data
                
                if decoded_text:
                    # 1. Check if the ESP32 is sending us a new Fingerprint Enrollment bundle
                    if decoded_text.startswith("FP_ENROLL_JSON:"):
                        payload_str = decoded_text[len("FP_ENROLL_JSON:"):]
                        try:
                            payload = json.loads(payload_str)
                            if payload['patient_id'] == 999:
                                print("\n=======================================================")
                                print("[CLOUD MATCH] Received LIVE Fingerprint Vector from ESP32!")
                                
                                live_bytes = base64.b64decode(payload['template_b64'])
                                
                                # Convert a few bytes to literal 1s and 0s for the user to see!
                                binary_preview = "".join(f"{b:08b}" for b in live_bytes[:8])
                                print(f"[VECTOR DATA] First 64-bits: {binary_preview}...")
                                
                                print("[CLOUD MATCH] Comparing vector against Raspberry Pi Cloud Database...")
                                
                                # Read the CSV file to find the best match using Fuzzy Logic!
                                import os
                                csv_filename = "/home/pi/FInger_Print_Morse/Hardware_Deployment_Package/enrolled_fingerprints.csv"
                                
                                if not os.path.exists(csv_filename):
                                    print("[CLOUD MATCH] ➔ FAILED: No database found! Please enroll fingers first.")
                                else:
                                    live_bytes = base64.b64decode(payload['template_b64'])
                                    best_match_id = -1
                                    best_similarity = 0.0
                                    
                                    with open(csv_filename, "r") as f:
                                        reader = csv.reader(f)
                                        next(reader) # skip header
                                        for row in reader:
                                            db_pid = int(row[0])
                                            db_bytes = base64.b64decode(row[1])
                                            
                                            # We use difflib.SequenceMatcher which finds the longest contiguous matching 
                                            # blocks, ignoring byte shifts! This is crucial because AS608 merged 
                                            # (enrolled) templates have different offsets than single (live) templates.
                                            matcher = difflib.SequenceMatcher(None, live_bytes, db_bytes)
                                            similarity = matcher.ratio() * 100
                                            
                                            # Optionally strip trailing zeros for better accuracy?
                                            # Not strictly needed since SequenceMatcher handles junk gracefully.
                                            
                                            if similarity > best_similarity:
                                                best_similarity = similarity
                                                best_match_id = db_pid
                                                
                                    # No artificial sleep needed here
                                    print(f"[CLOUD MATCH] ➔ HIGHEST SIMILARITY: {best_similarity:.1f}%")
                                    if best_similarity >= 89.0:  # Raised from 35% — real matches score ~91%, false positives score ~88%
                                        print(f"[CLOUD MATCH] ➔ MATCH SUCCESSFUL! Vector matches Patient #{best_match_id}.")
                                        print("[CLOUD MATCH] Synchronizing Patient Profile to this bed's ESP32...")
                                        
                                        # Send the matched template back to the ESP32 to store in local memory!
                                        # We need to find the base64 string of the BEST match from the CSV again
                                        best_b64 = ""
                                        with open(csv_filename, "r") as f:
                                            reader = csv.reader(f)
                                            next(reader)
                                            for row in reader:
                                                if int(row[0]) == best_match_id:
                                                    best_b64 = row[1]
                                                    break
                                                    
                                        sync_payload = {
                                            "patient_id": best_match_id,
                                            "template_b64": best_b64,
                                            "dotEMA": 150.0,
                                            "dotThreshold": 150.0,
                                            "dashEMA": 350.0,
                                            "dashThreshold": 350.0
                                        }
                                        sync_str = "FP_SYNC_JSON:" + json.dumps(sync_payload) + "\n"
                                        esp32_serial.write(sync_str.encode())
                                        esp32_serial.flush()
                                        print(f"[CLOUD MATCH] ➔ Sync command sent for Patient #{best_match_id}!")
                                    else:
                                        print("[CLOUD MATCH] ➔ MATCH FAILED! Score too low (Needs 80%+).")
                                print("=======================================================\n")
                                
                            else:
                                # Standard Enrollment - Upload to server instantly
                                sio.emit('fp_upload', payload)
                                print(f"[FP_SYNC] Uploaded patient {payload['patient_id']} template & params to Server.")
                                
                                # Send the GO signal back to the ESP32 traffic light!
                                time.sleep(1) # Give the server 1 second to definitely save the CSV file
                                esp32_serial.write(b"FP_CSV_SAVED:OK\n")
                                print(f"[FP_SYNC] Sent Traffic GREEN LIGHT to ESP32!")
                        except json.JSONDecodeError:
                            print("[FP_SYNC] Error decoding JSON from ESP32.")
                        continue # Skip forwarding as patient text
                    
                    # 2. Check if ESP32 is sending standard debug text we should ignore
                    if decoded_text.startswith("[FP_SYNC]"):
                        print(decoded_text)
                        continue
                        
                    # 3. Handle actual decoded Morse text
                    if decoded_text.startswith("TOUCH_TEXT:"):
                        actual_text = decoded_text[len("TOUCH_TEXT:"):]
                        print(f">>> [FROM ESP32] Raw Touch Decoded: '{actual_text}'")
                        
                        payload = {
                            'patient_id': 1, # Update this to dynamic ID later
                            'text': actual_text
                        }
                        sio.emit('patient_message', payload)
                        print(f"    Forwarded '{actual_text}' to V3 Server ->")
                    else:
                        # Just print any other debug messages from the ESP32
                        print(f"[ESP32] {decoded_text}")
                    
            time.sleep(0.01) # Small sleep to prevent 100% CPU usage
            
    except KeyboardInterrupt:
        print("\nStopping hardware bridge...")
    finally:
        if esp32_serial:
            esp32_serial.close()
        sio.disconnect()
        print("Cleaned up connections.")

if __name__ == '__main__':
    main()
