import serial
import requests
import time
import re
import csv
import os

# ================= CONFIG =================
# Get your API key from: https://www.perplexity.ai/settings/api
API_KEY = "your_perplexity_api_key_here"
API_URL = "https://api.perplexity.ai/chat/completions"

PORT = "COM5"
BAUD_RATE = 115200
CSV_FILE = "sonar_pro_latency_log.csv"

# ================= SERIAL =================
esp = serial.Serial(PORT, BAUD_RATE, timeout=1)
time.sleep(2)
print(f"[INFO] Connected to {PORT}")

# ================= CSV INIT =================
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp",
            "morse_text",
            "length",
            "rx_ms",
            "cloud_ms",
            "tx_ms",
            "end_to_end_ms"
        ])

# ================= BUFFER CONTROL =================
text_buffer = ""
llm_gate_open = False

# ================= HELPERS =================
def clean_llm_output(text):
    return re.sub(
        r"\b(GPT|LLM|Assistant|AI)\s*[:\-–—]?\s*",
        "",
        text,
        flags=re.I
    ).strip()


def is_final_morse_text(text):
    text = text.strip()

    if not text:
        return False

    # Ignore raw Morse symbols
    if all(c in ".- " for c in text):
        return False

    # Ignore debug arrows
    if "→" in text:
        return False

    # Ignore ESP32 status/debug lines
    if text.startswith("Special Command Triggered"):
        return False

    return True


# ================= LLM QUERY =================
def query_perplexity(text):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "sonar-pro",
        "messages": [
            {
                "role": "system",
                "content": "Reply using plain text only. Do not include labels."
            },
            {"role": "user", "content": text}
        ],
        "max_tokens": 300
    }

    t_cloud_start = time.perf_counter()
    response = requests.post(API_URL, headers=headers, json=payload, timeout=20)
    t_cloud_end = time.perf_counter()

    cloud_latency = t_cloud_end - t_cloud_start

    if response.status_code == 200:
        reply = response.json()["choices"][0]["message"]["content"]
    else:
        reply = "LLM response failed."

    return reply, cloud_latency


# ================= MAIN LOOP =================
while True:
    if esp.in_waiting > 0:
        t0 = time.perf_counter()

        incoming = esp.readline().decode(errors="ignore").strip()
        t1 = time.perf_counter()

        if not is_final_morse_text(incoming):
            continue

        morse_text = incoming

        # ---------- CONTROL COMMANDS ----------
        if morse_text == "<CLEAR>":
            text_buffer = ""
            llm_gate_open = False
            print("[INFO] Buffer cleared")
            continue

        if morse_text == "<CONFIRM>":
            llm_gate_open = True
        else:
            # Normal decoded text → store only
            text_buffer += morse_text + " "
            print("[BUFFER]", text_buffer.strip())
            continue

        # ---------- LLM TRIGGER ----------
        if not llm_gate_open or not text_buffer.strip():
            continue

        final_text = text_buffer.strip()

        # ---- PREP QUERY ----
        if final_text.startswith("REPORT:"):
            data = final_text.replace("REPORT:", "").strip()
            query_text = f"Health readings: {data}. Give medical summary."
        else:
            query_text = final_text

        # ---- CLOUD ----
        raw_reply, cloud_latency = query_perplexity(query_text)
        clean_reply = clean_llm_output(raw_reply)

        # ---- SEND BACK ----
        esp.write((clean_reply + "\n").encode("utf-8"))
        t2 = time.perf_counter()

        # ---- LATENCY CALC ----
        rx_latency = t1 - t0
        tx_latency = t2 - t1 - cloud_latency
        end_to_end = t2 - t0

        # ---- PRINT REPORT ----
        print("\n[MORSE TEXT] :", final_text)
        print("--- LATENCY REPORT ---")
        print(f"RX  (ESP32 → PC)  : {rx_latency*1000:.2f} ms")
        print(f"Cloud Round-Trip  : {cloud_latency*1000:.2f} ms")
        print(f"TX  (PC → ESP32)  : {tx_latency*1000:.2f} ms")
        print(f"End-to-End        : {end_to_end*1000:.2f} ms")
        print("----------------------")

        # ---- CSV LOG ----
        with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                time.strftime("%Y-%m-%d %H:%M:%S"),
                final_text,
                len(final_text),
                round(rx_latency * 1000, 2),
                round(cloud_latency * 1000, 2),
                round(tx_latency * 1000, 2),
                round(end_to_end * 1000, 2)
            ])

        # ---- RESET STATE ----
        text_buffer = ""
        llm_gate_open = False
