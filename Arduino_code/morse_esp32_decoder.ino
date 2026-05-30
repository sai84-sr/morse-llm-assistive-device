/**
 * ============================================================
 * Morse Code ESP32 Decoder with Bluetooth & Serial Output
 * ============================================================
 * 
 * Description:
 *   This firmware decodes Morse code input from capacitive touch
 *   sensors connected to an ESP32 microcontroller. It implements
 *   a two-sensor system for Morse input and confirmation/control.
 * 
 * Hardware:
 *   - ESP32 WROOM microcontroller
 *   - TTP223 capacitive touch sensors (Morse + Control)
 *   - Bluetooth Serial communication support
 * 
 * Pin Configuration:
 *   - GPIO 4:  Morse input sensor (dot/dash)
 *   - GPIO 15: Control/confirmation sensor
 * 
 * Protocol:
 *   - DOT (<500ms), DASH (≥500ms), SPACE (..), CLEAR (--)
 *   - Auto-decode after 2-second silence
 *   - Special commands for space and clear functions
 * 
 * Author: Research Team
 * Date: 2025
 * Version: 2.0
 * ============================================================
 */

#include "BluetoothSerial.h"

BluetoothSerial SerialBT;

// ===================== PIN CONFIGURATION =====================
const int morsePin   = 4;   // Morse sensor input (dot/dash)
const int controlPin = 15;  // Control sensor (confirm/send)

// ===================== STATE MANAGEMENT =====================
bool morsePressed = false;
bool controlPressed = false;

unsigned long morseStartTime = 0;
unsigned long controlStartTime = 0;

String currentMorse = "";
unsigned long lastInputTime = 0;

// ===================== TIMING CONFIGURATION =====================
const unsigned long DASH_THRESHOLD = 500;    // ms - threshold for dot/dash
const unsigned long CONTROL_THRESHOLD = 700; // ms - confirm vs full response
const unsigned long AUTO_DECODE_DELAY = 2000; // ms - auto-decode timeout

// ===================== MORSE CODE TABLE =====================
/**
 * Standard International Morse Code mapping
 * Each entry contains [morse_code, decoded_character]
 */
String morseTable[][2] = {
  // Letters A-Z
  {".-", "A"}, {"-...", "B"}, {"-.-.", "C"}, {"-..", "D"}, {".", "E"},
  {"..-.", "F"}, {"--.", "G"}, {"....", "H"}, {"..", "I"}, {".---", "J"},
  {"-.-", "K"}, {".-..", "L"}, {"--", "M"}, {"-.", "N"}, {"---", "O"},
  {".--.", "P"}, {"--.-", "Q"}, {".-.", "R"}, {"...", "S"}, {"-", "T"},
  {"..-", "U"}, {"...-", "V"}, {".--", "W"}, {"-..-", "X"}, {"-.--", "Y"},
  {"--..", "Z"},
  
  // Numbers 0-9
  {"-----", "0"}, {".----", "1"}, {"..---", "2"}, {"...--", "3"},
  {"....-", "4"}, {".....", "5"}, {"-....", "6"}, {"--...", "7"},
  {"---..", "8"}, {"----.", "9"}
};

// ===================== MORSE DECODING FUNCTION =====================
/**
 * Decodes a morse code string to its character representation
 * 
 * @param morse - Morse code string (dots and dashes)
 * @return Decoded character or "?" if not found
 */
String decodeMorse(String morse) {
  for (int i = 0; i < sizeof(morseTable)/sizeof(morseTable[0]); i++) {
    if (morseTable[i][0] == morse) {
      return morseTable[i][1];
    }
  }
  return "?"; // Unknown morse code
}

// ===================== SPECIAL COMMAND HANDLER =====================
/**
 * Handles special morse codes and standard character decoding
 * Special commands:
 *   ".." (I) -> Insert space
 *   "--" (M) -> Clear current input
 * 
 * @param morse - Morse code string to decode and handle
 */
void handleSpecialMorse(String morse) {
  
  // Special command: Insert space
  if (morse == "..") {
    Serial.println("<SPACE>");
    Serial.println("TOUCH_TEXT: ");
    return;
  }
  
  // Special command: Clear input
  if (morse == "--") {
    Serial.println("<CLEAR>");
    return;
  }
  
  // Standard character decoding
  String decoded = decodeMorse(morse);
  Serial.println(decoded);
  Serial.print("TOUCH_TEXT:");
  Serial.println(decoded);
}

// ===================== SETUP FUNCTION =====================
/**
 * Initializes the ESP32:
 *  - Serial communication (115200 baud for Raspberry Pi)
 *  - Bluetooth Serial (for wireless feedback)
 *  - GPIO pins (INPUT mode for capacitive sensors)
 */
void setup() {
  // Initialize serial communication
  Serial.begin(115200);
  SerialBT.begin("ESP32_Morse_2");
  
  // Configure pins as inputs
  pinMode(morsePin, INPUT);
  pinMode(controlPin, INPUT);
  
  // System initialization message
  Serial.println("System Ready");
}

// ===================== MAIN LOOP =====================
/**
 * Main program loop - continuous monitoring of sensors
 * Handles three concurrent tasks:
 *  1. Morse input detection (dot/dash timing)
 *  2. Control confirmation (short/long press)
 *  3. Auto-decode (2-second silence timeout)
 *  4. Bluetooth receive (LLM responses)
 */
void loop() {
  
  unsigned long now = millis();
  
  // Read sensor states
  int morseState = digitalRead(morsePin);
  int controlState = digitalRead(controlPin);
  
  // --------- MORSE SENSOR INPUT DETECTION ---------
  // Rising edge: sensor pressed
  if (morseState == HIGH && !morsePressed) {
    morsePressed = true;
    morseStartTime = now;
  }
  
  // Falling edge: sensor released
  if (morseState == LOW && morsePressed) {
    morsePressed = false;
    unsigned long duration = now - morseStartTime;
    
    // Classify as dot or dash based on duration
    if (duration < DASH_THRESHOLD) {
      currentMorse += ".";
      Serial.print(".");
    } else {
      currentMorse += "-";
      Serial.print("-");
    }
    
    lastInputTime = now;
  }
  
  // --------- CONTROL SENSOR CONFIRMATION ---------
  // Rising edge: control button pressed
  if (controlState == HIGH && !controlPressed) {
    controlPressed = true;
    controlStartTime = now;
  }
  
  // Falling edge: control button released
  if (controlState == LOW && controlPressed) {
    controlPressed = false;
    unsigned long duration = now - controlStartTime;
    
    // Process accumulated morse code
    if (currentMorse != "") {
      handleSpecialMorse(currentMorse);
      currentMorse = "";
    }
    
    // Determine confirmation type based on hold duration
    if (duration < CONTROL_THRESHOLD) {
      Serial.println("<CONFIRM_CORRECTION_ONLY>");
    } else {
      Serial.println("<CONFIRM_FULL_RESPONSE>");
    }
  }
  
  // --------- AUTO-DECODE TIMEOUT ---------
  // Auto-decode if no input for 2 seconds
  if (currentMorse != "" && (now - lastInputTime > AUTO_DECODE_DELAY)) {
    handleSpecialMorse(currentMorse);
    currentMorse = "";
  }
  
  // --------- BLUETOOTH RECEIVE (LLM RESPONSES) ---------
  // Receive responses from Raspberry Pi and forward via Bluetooth
  if (Serial.available()) {
    String reply = Serial.readStringUntil('\n');
    SerialBT.println("GPT: " + reply);
  }
}
