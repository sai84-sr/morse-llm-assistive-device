"""
================================================================================
Morse Code ESP32 LLM - Response Generation Tool
================================================================================

Description:
    Generates intelligent LLM responses to user Morse code input using the
    Perplexity AI Sonar Pro model (Llama 3.3-based). Integrates with ESP32
    for end-to-end communication and error correction.

Features:
    - Real-time response generation from Morse input
    - Medical/health reading analysis capability
    - Bluetooth relay support for wireless feedback
    - Streaming integration with ESP32 feedback loop

Hardware:
    - ESP32 WROOM with Morse sensors and USB serial
    - Optional Bluetooth receiver for wireless feedback

Output:
    - Serial console: Real-time response display
    - Bluetooth broadcast: Wireless feedback to mobile devices

Author: Research Team
Date: 2025
Version: 2.0
================================================================================
"""

import serial
import requests
import json

# ===================== CONFIGURATION =====================
# Get your API key from: https://www.perplexity.ai/settings/api
API_KEY = "your_perplexity_api_key_here"
API_URL = "https://api.perplexity.ai/chat/completions"
PORT = "COM5"       # Change to your ESP32 USB port
BAUD_RATE = 115200

# ===================== SERIAL CONNECTION =====================
esp = serial.Serial(PORT, BAUD_RATE, timeout=1)
print(f"[INFO] Connected to {PORT} at {BAUD_RATE} baud.")

# ===================== PERPLEXITY API FUNCTION =====================
def query_perplexity(user_text):
    """
    Query Perplexity AI Sonar Pro model for response generation.
    Includes medical assistant capabilities for health reading analysis.
    
    Args:
        user_text (str): User query from Morse code input
        
    Returns:
        str: LLM-generated response or error message
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "sonar-pro",  # Llama 3.3-based model
        "messages": [
            {"role": "system", "content": "You are a helpful medical + general assistant. "
                                          "If user sends health readings (like heart rate, oxygen, temperature), "
                                          "analyze them and generate a clear health report with precautions."},
            {"role": "user", "content": user_text}
        ],
        "max_tokens": 300
    }
    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            return "[ERROR] Unexpected response format."
    else:
        return f"[ERROR] API returned {response.status_code}: {response.text}"

# ===================== MAIN LOOP =====================
while True:
    if esp.in_waiting > 0:
        decoded_text = esp.readline().decode().strip()
        if decoded_text:
            print(f"[ESP32] Received: {decoded_text}")

            # Detect if it's a health report or normal Morse text
            if decoded_text.startswith("REPORT:"):
                # Example: REPORT: HR=78, SpO2=96, Temp=36.5
                health_data = decoded_text.replace("REPORT:", "").strip()
                query_text = f"Health readings received: {health_data}. Please provide a detailed medical report."
                reply = query_perplexity(query_text)
                print(f"[LLM] Health Report: {reply}")
            else:
                # Normal Morse-decoded conversation
                reply = query_perplexity(decoded_text)
                print(f"[LLM] Response: {reply}")

            # Send back to ESP32
            esp.write((reply + "\n").encode())
