#include "mbedtls/base64.h"
#include <Adafruit_Fingerprint.h>
#include <ArduinoJson.h>
#include <esp_task_wdt.h>  // Needed for esp_task_wdt_reset() to prevent TG0WDT crashes

// ================================================================
// FINGERPRINT SETUP (UART2)
// ================================================================
#define RXD2 25
#define TXD2 26
HardwareSerial fpSerial(2); // Standard ESP32 UART2
Adafruit_Fingerprint finger = Adafruit_Fingerprint(&fpSerial);

bool patientAuthenticated = false;
int activePatientID = -1;

// ================================================================
// ALGORITHM CONFIG — EMA + CUSUM + CONFIDENCE GATING
// ================================================================
float alpha = 0.3f;
float slack = 5.0f;
float cusumLimit = 100.0f;
float stepSize = 3.0f;
const float HIGH_GATE = 0.75f;
const float LOW_GATE = 0.40f;

float dotEMA = 150.0f;
float dotThreshold = 150.0f;
float dotS_high = 0.0f;
float dotS_low = 0.0f;

float dashEMA = 150.0f;
float dashThreshold = 150.0f;
float dashS_high = 0.0f;
float dashS_low = 0.0f;

float sentenceConfSum = 0.0f;
int sentenceSymCount = 0;
const unsigned long IDLE_BEFORE_STATUS = 15000;
bool statusPrintedThisIdle = false;

unsigned long LETTER_GAP = 3000;

// ================= PIN CONFIG =================
const int dotPin = 27;
const int dashPin = 32;
const int controlPin = 33;

bool dotPressed = false;
bool dashPressed = false;
bool controlPressed = false;
unsigned long dotStartTime = 0;
unsigned long dashStartTime = 0;
unsigned long controlStartTime = 0;

String currentMorse = "";
unsigned long lastInputTime = 0;
String sentenceBuffer = "";

// ================= MORSE TABLE =================
String morseTable[][2] = {
    {".-", "A"},    {"-...", "B"},  {"-.-.", "C"},  {"-..", "D"},
    {".", "E"},     {"..-.", "F"},  {"--.", "G"},   {"....", "H"},
    {"..", "I"},    {".---", "J"},  {"-.-", "K"},   {".-..", "L"},
    {"--", "M"},    {"-.", "N"},    {"---", "O"},   {".--.", "P"},
    {"--.-", "Q"},  {".-.", "R"},   {"...", "S"},   {"-", "T"},
    {"..-", "U"},   {"...-", "V"},  {".--", "W"},   {"-..-", "X"},
    {"-.--", "Y"},  {"--..", "Z"},  {"-----", "0"}, {".----", "1"},
    {"..---", "2"}, {"...--", "3"}, {"....-", "4"}, {".....", "5"},
    {"-....", "6"}, {"--...", "7"}, {"---..", "8"}, {"----.", "9"}};

// ================================================================
// ALGORITHM FUNCTIONS
// ================================================================
float updateEMA(float newVal, float prevEMA) {
  return alpha * newVal + (1.0f - alpha) * prevEMA;
}

void updateCUSUM(float measured, float &threshold, float &S_high,
                 float &S_low) {
  float deviation = measured - threshold;
  S_high = max(0.0f, S_high + deviation - slack);
  S_low = max(0.0f, S_low - deviation - slack);
  if (S_high > cusumLimit) {
    threshold += stepSize;
    S_high = 0.0f;
  }
  if (S_low > cusumLimit) {
    threshold = max(50.0f, threshold - stepSize);
    S_low = 0.0f;
  }
}

float computeConfidence(float pressDuration, float threshold) {
  float distance = fabs(pressDuration - threshold);
  float maxRange = threshold * 0.8f;
  return min(1.0f, distance / maxRange);
}

void accumulateConfidence(float conf) {
  sentenceConfSum += conf;
  sentenceSymCount += 1;
}

void evaluateSentenceGate() {
  if (sentenceSymCount == 0)
    return;
  float sentConf = sentenceConfSum / (float)sentenceSymCount;
  Serial.println("-------- GATE EVALUATION --------");
  Serial.printf("Sentence confidence: %.2f | Symbols: %d\n", sentConf,
                sentenceSymCount);
  if (sentConf >= HIGH_GATE) {
    Serial.println("Route A: HIGH -> short prompt to Pi");
    Serial.println("[GATE:HIGH]");
  } else if (sentConf >= LOW_GATE) {
    Serial.println("Route B: MEDIUM -> extended prompt to Pi");
    Serial.println("[GATE:MEDIUM]");
  } else {
    Serial.println("Route C: LOW -> asking user to retry");
    Serial.println("[GATE:LOW] Input unclear. Please retry.");
  }
  Serial.println("---------------------------------");
  sentenceConfSum = 0.0f;
  sentenceSymCount = 0;
}

String decodeMorse(String morse) {
  for (int i = 0; i < sizeof(morseTable) / sizeof(morseTable[0]); i++) {
    if (morseTable[i][0] == morse)
      return morseTable[i][1];
  }
  return "?";
}

void handleSpecialMorse(String morse) {
  String decoded = decodeMorse(morse);
  sentenceBuffer += decoded;
  Serial.println();
  Serial.printf(" [LETTER DECODED: \"%s\" -> \"%s\"]\n", morse.c_str(),
                decoded.c_str());
  Serial.print("Current Buffer: ");
  Serial.println(sentenceBuffer);
}

// ================================================================
// NON-BLOCKING FINGERPRINT SYNC STATE MACHINE (CLAUDE'S FIX)
// ================================================================
#define FP_TEMPLATE_MAX 600

enum FPSyncState {
  FP_IDLE,
  FP_EXTRACT_CMD_SENT,
  FP_EXTRACT_READING,
  FP_INJECT_SENDING,
  FP_INJECT_WAIT_ACK
};
FPSyncState fpState = FP_IDLE;

uint8_t fpBuf[FP_TEMPLATE_MAX];
uint16_t fpBufLen = 0;
int fpSyncPatientID = -1;
unsigned long fpStateStart = 0;
uint16_t fpInjectSent = 0;

void fpWritePacket(uint8_t pid, uint8_t *data, uint16_t len) {
  fpSerial.write(0xEF);
  fpSerial.write(0x01);
  fpSerial.write(0xFF);
  fpSerial.write(0xFF);
  fpSerial.write(0xFF);
  fpSerial.write(0xFF);
  fpSerial.write(pid);
  uint16_t pktLen = len + 2;
  fpSerial.write((pktLen >> 8) & 0xFF);
  fpSerial.write(pktLen & 0xFF);
  uint16_t sum = pid + ((pktLen >> 8) & 0xFF) + (pktLen & 0xFF);
  for (uint16_t i = 0; i < len; i++) {
    fpSerial.write(data[i]);
    sum += data[i];
  }
  fpSerial.write((sum >> 8) & 0xFF);
  fpSerial.write(sum & 0xFF);
}

void emitExtractedTemplate(int patientID, uint8_t *tmpl, uint16_t len) {
  size_t outLen = 0, b64Cap = ((len + 2) / 3) * 4 + 4;
  char *b64 = (char *)malloc(b64Cap);
  mbedtls_base64_encode((unsigned char *)b64, b64Cap, &outLen, tmpl, len);
  b64[outLen] = '\0';

  DynamicJsonDocument doc(2048);
  doc["patient_id"] = patientID;
  doc["template_b64"] = b64;
  doc["dotEMA"] = dotEMA;
  doc["dotThreshold"] = dotThreshold;
  doc["dashEMA"] = dashEMA;
  doc["dashThreshold"] = dashThreshold;
  doc["dotS_high"] = dotS_high;
  doc["dotS_low"] = dotS_low;
  doc["dashS_high"] = dashS_high;
  doc["dashS_low"] = dashS_low;

  Serial.print("FP_ENROLL_JSON:");
  serializeJson(doc, Serial);
  Serial.println();
  free(b64);
}

void startExtractTemplate(int patientID) {
  if (patientID != 999) {
    if (finger.loadModel(patientID) != FINGERPRINT_OK)
      return;
    finger.getModel();
    delay(50);
  }

  // FLUSH ANY GARBAGE BYTES FROM THE SENSOR RX BUFFER
  while (fpSerial.available()) {
    fpSerial.read();
  }

  uint8_t cmd[2] = {0x08, 1};
  fpWritePacket(0x01, cmd, 2);

  fpBufLen = 0;
  bool done = false;
  unsigned long waitStart = millis();

  while (!done && millis() - waitStart < 5000) {
    yield(); // CRITICAL: Feed the ESP32 watchdog timer to prevent crash-reboot loop!
    if (fpSerial.available() >= 2) {
      if (fpSerial.read() == 0xEF) {
        unsigned long headerStart = millis();
        while (fpSerial.available() < 1 && millis() - headerStart < 100) {
          delay(1);
        }
        if (fpSerial.available() && fpSerial.read() == 0x01) {
          // Found header! Read the remaining 7 bytes of the 9-byte header
          uint8_t hdr[7];
          uint8_t bytes_read = 0;
          while (bytes_read < 7 && millis() - headerStart < 500) {
            if (fpSerial.available()) {
              hdr[bytes_read++] = fpSerial.read();
            }
          }
          if (bytes_read < 7)
            continue;

          uint8_t pid = hdr[4];
          uint16_t len = (hdr[5] << 8) | hdr[6];
          uint16_t payloadLen = len - 2;

          unsigned long pStart = millis();
          uint16_t bRead = 0;
          bool timeout = false;
          while (bRead < len) {
            if (fpSerial.available()) {
              uint8_t b = fpSerial.read();
              if (bRead < payloadLen) {
                if (pid == 0x02 || pid == 0x08) {
                  if (fpBufLen < FP_TEMPLATE_MAX)
                    fpBuf[fpBufLen++] = b;
                }
              }
              bRead++;
            } else {
              if (millis() - pStart > 1000) {
                timeout = true;
                break;
              }
            }
          }
          if (timeout)
            continue;

          if (pid == 0x08) {
            done = true;
            break;
          }
          waitStart = millis(); // Reset timeout for next packet
        }
      }
    }
  }

  if (done) {
    emitExtractedTemplate(patientID, fpBuf, fpBufLen);
    // No need to wait for Python to confirm - the Pi handles saving asynchronously.
    // The old 10-second blocking wait here was crashing the ESP32 watchdog!
  } else {
    Serial.println("[FP_SYNC] Timeout extracting template from sensor, aborting.");
  }
}

void startInjectTemplate(int patientID, uint8_t *data, uint16_t len) {
  if (fpState != FP_IDLE)
    return;
  if (len == 0) {
    Serial.println("[FP_SYNC] Error: Template length is 0. Aborting injection.");
    return;
  }
  memcpy(fpBuf, data, len);
  fpBufLen = len;
  fpSyncPatientID = patientID;
  
  // Flush any leftover ACKs from the sensor before sending a new command
  while (fpSerial.available()) fpSerial.read();
  
  uint8_t cmd[2] = {0x09, 1};
  fpWritePacket(0x01, cmd, 2);
  fpState = FP_INJECT_WAIT_ACK;
  fpStateStart = millis();
  fpInjectSent = 0;
}

void fpSyncUpdate() {
  if (fpState == FP_IDLE)
    return;

  if (millis() - fpStateStart > 1000) {
    Serial.println("[FP_SYNC] Timeout, aborting.");
    fpState = FP_IDLE;
    return;
  }

  switch (fpState) {
  case FP_INJECT_WAIT_ACK: {
    if (fpSerial.available() < 12)
      return;
      
    uint8_t hdr[12];
    for (int i = 0; i < 12; i++) {
      hdr[i] = fpSerial.read();
    }
    
    // Check if this is a valid ACK packet (0xEF 0x01 ... 0x07)
    if (hdr[0] == 0xEF && hdr[1] == 0x01 && hdr[6] == 0x07) {
      uint8_t confirmCode = hdr[9];
      if (confirmCode == 0x00) {
        // Sensor says "Ready to receive data"
        fpState = FP_INJECT_SENDING;
        fpInjectSent = 0;
      } else {
        // Sensor rejected the 0x09 command (e.g. it was busy)
        Serial.printf("[FP_SYNC] Sensor rejected 0x09 with code 0x%02X\n", confirmCode);
        fpState = FP_IDLE;
      }
    } else {
      // Completely unrecognized response
      fpState = FP_IDLE;
    }
    return;
  }

  case FP_INJECT_SENDING: {
    const uint16_t CHUNK = 128;
    uint16_t chunk = min((uint16_t)CHUNK, (uint16_t)(fpBufLen - fpInjectSent));
    bool isLast = (fpInjectSent + chunk >= fpBufLen);
    fpWritePacket(isLast ? 0x08 : 0x02, fpBuf + fpInjectSent, chunk);
    fpInjectSent += chunk;
    if (isLast) {
      delay(50); // Give sensor time to process the final data packet and send its ACK
      while (fpSerial.available()) fpSerial.read(); // Flush the data packet ACK so it doesn't confuse storeModel
      
      if (finger.storeModel(fpSyncPatientID) == FINGERPRINT_OK)
        Serial.printf("[FP_SYNC] Patient #%d synced to this bed.\n",
                      fpSyncPatientID);
      else
        Serial.printf("[FP_SYNC] Failed to store patient #%d in sensor memory!\n", fpSyncPatientID);
        
      fpState = FP_IDLE;
    }
    return;
  }

  default:
    return;
  }
}

void applyIncomingPayload(const String &jsonStr, uint8_t *outTemplate,
                          uint16_t &outLen, int &outPatientID) {
  DynamicJsonDocument doc(2048);
  if (deserializeJson(doc, jsonStr) != DeserializationError::Ok) {
    Serial.println("[FP_SYNC] JSON Parse Failed in applyIncomingPayload!");
    outPatientID = -1;
    return;
  }

  outPatientID = doc["patient_id"] | -1;

  dotEMA = doc["dotEMA"] | dotEMA;
  dotThreshold = doc["dotThreshold"] | dotThreshold;
  dashEMA = doc["dashEMA"] | dashEMA;
  dashThreshold = doc["dashThreshold"] | dashThreshold;
  dotS_high = doc["dotS_high"] | 0.0f;
  dotS_low = doc["dotS_low"] | 0.0f;
  dashS_high = doc["dashS_high"] | 0.0f;
  dashS_low = doc["dashS_low"] | 0.0f;

  if (doc.containsKey("template_b64")) {
    const char *b64 = doc["template_b64"];
    if (b64 != nullptr) {
      size_t tempLen = 0;
      mbedtls_base64_decode(outTemplate, FP_TEMPLATE_MAX, &tempLen,
                            (const unsigned char *)b64, strlen(b64));
      outLen = (uint16_t)tempLen;
    } else {
      outLen = 0;
    }
  } else {
    outLen = 0;
  }
}

// ================================================================
// FINGERPRINT ENROLLMENT
// ================================================================
void enrollFingerprint() {
  Serial.println(
      "\n============================================================");
  Serial.println(
      "                 FINGERPRINT ENROLLMENT MODE                ");
  Serial.println(
      "============================================================");
  Serial.println(" Enter Patient ID (1 to 127) and press Enter:");

  while (Serial.available())
    Serial.read();
    
  unsigned long waitStart = millis();
  while (!Serial.available()) {
    delay(10);
    if (millis() - waitStart > 10000) {
      Serial.println("[FAIL] Enrollment timed out waiting for ID.");
      return;
    }
  }

  int id = Serial.parseInt();
  if (id <= 0 || id > 127) {
    Serial.println("[FAIL] Invalid ID! Must be between 1 and 127.");
    return;
  }

  Serial.printf(">> Enrolling Patient ID #%d\n", id);

  // --- Scan 1 ---
  Serial.println("Step 1: Place finger on sensor...");
  int p = -1;
  waitStart = millis();
  while (p != FINGERPRINT_OK) {
    p = finger.getImage();
    if (p == FINGERPRINT_NOFINGER) {
      Serial.print(".");
      delay(300);
    } else if (p != FINGERPRINT_OK) {
      Serial.printf(" [ERR:0x%02X] ", p);
      delay(300);
    }
    if (millis() - waitStart > 20000) {
      Serial.println("\n[FAIL] Enrollment timed out waiting for finger.");
      return;
    }
  }
  Serial.println("\n [OK] Image 1 taken!");

  p = finger.image2Tz(1);
  if (p != FINGERPRINT_OK) {
    Serial.println("[FAIL] Poor image. Try again.");
    return;
  }

  Serial.println("Step 2: Remove your finger...");
  delay(1500);
  while (finger.getImage() != FINGERPRINT_NOFINGER)
    delay(100);

  // --- Scan 2 ---
  Serial.println("Step 3: Place the SAME finger again...");
  p = -1;
  waitStart = millis();
  while (p != FINGERPRINT_OK) {
    p = finger.getImage();
    if (p == FINGERPRINT_NOFINGER) {
      Serial.print(".");
      delay(300);
    }
    if (millis() - waitStart > 20000) {
      Serial.println("\n[FAIL] Enrollment timed out waiting for finger.");
      return;
    }
  }
  Serial.println("\n [OK] Image 2 taken!");

  p = finger.image2Tz(2);
  if (p != FINGERPRINT_OK) {
    Serial.println("[FAIL] Poor image. Try again.");
    return;
  }

  p = finger.createModel();
  if (p != FINGERPRINT_OK) {
    Serial.println("[FAIL] Scans did not match. Try again.");
    return;
  }

  // Clear out any old fingerprint at this ID before saving
  finger.deleteModel(id);
  delay(50);

  p = finger.storeModel(id);
  if (p == FINGERPRINT_OK) {
    Serial.println(
        "============================================================");
    Serial.printf(" [SUCCESS] Patient ID #%d saved in sensor memory!\n", id);
    Serial.println(" You can now scan this finger to start Morse input.");
    Serial.println(
        "============================================================\n");

    // ---- NEW: Extract the template for the central DB ----
    // This will pull the newly saved model out of the sensor and send it to the Pi
    startExtractTemplate(id);
  } else {
    Serial.println("[FAIL] Could not save to sensor memory.");
  }
}

// ================================================================
// FINGERPRINT AUTHENTICATION
// ================================================================
bool authenticateFingerprint() {
  Serial.println(
      "\n============================================================");
  Serial.println(
      "  PLACE REGISTERED FINGER ON SENSOR TO START MORSE INPUT    ");
  Serial.println(
      "  (Or type 'E' to enroll a new finger first)                ");
  Serial.println(
      "============================================================");

  while (true) {
    // We MUST call fpSyncUpdate here as well in case a sync arrives while
    // waiting to auth!
    fpSyncUpdate();

    if (Serial.available()) {
      String line = Serial.readStringUntil('\n');
      line.trim();
      if (line.length() > 0) {
        if (line.startsWith("FP_SYNC_JSON:")) {
          String payload = line.substring(13);
          uint8_t decoded[FP_TEMPLATE_MAX];
          uint16_t decLen = 0;
          int pid = -1;
          applyIncomingPayload(payload, decoded, decLen, pid);
          if (pid != -1) {
            startInjectTemplate(pid, decoded, decLen);
          }
          continue;
        } else if (line.startsWith("FP_DELETE:")) {
          int pid = line.substring(10).toInt();
          finger.deleteModel(pid);
          Serial.printf("[FP_SYNC] Deleted patient #%d locally.\n", pid);
          continue;
        }
        char c = toupper(line.charAt(0));
        if (c == 'E') {
          enrollFingerprint();
          Serial.println(
              "\n Now place your registered finger to authenticate...");
          continue;
        }
        if (c == 'D') {
          esp_task_wdt_reset(); // Prevent watchdog during long flash erase
          finger.emptyDatabase();
          delay(500);           // Let sensor settle after mass erase
          esp_task_wdt_reset();
          Serial.println("\n[ESP32] ======================================");
          Serial.println("[ESP32] ALL FINGERPRINTS ERASED FROM SENSOR!");
          Serial.println("[ESP32] ======================================");
          continue;
        }
      }
    }

    // ONLY poll the sensor for a new finger if we aren't currently dumping a
    // template over serial!
    if (fpState == FP_IDLE) {
      if (finger.getImage() == FINGERPRINT_OK) {
        if (finger.image2Tz() == FINGERPRINT_OK) {
          if (finger.fingerFastSearch() == FINGERPRINT_OK) {
            activePatientID = finger.fingerID;
            patientAuthenticated = true;
            Serial.println(
                "============================================================");
            Serial.printf(" [ACCESS GRANTED] Patient ID #%d authenticated.\n",
                          activePatientID);
            Serial.println(
                " Morse input is now ACTIVE. Use the 3 touch sensors.");
            Serial.println(" (Type 'E' anytime to re-enroll | 'L' to lock / "
                           "switch patient)");
            Serial.println("==================================================="
                           "=========\n");
            Serial.printf("[AUTH:OK] Patient #%d\n", activePatientID);
            return true;
          } else {
            Serial.println(
                " [LOCAL DENIED] Fingerprint not found in local memory.");
            Serial.println(" [CLOUD MATCH] Sending live 512-byte vector to "
                           "Raspberry Pi for cloud verification...");

            // Extract Buffer 1 (the live finger) and send it to the Pi
            startExtractTemplate(999);
            // After startExtractTemplate finishes (it blocks for ~1-2s), it will have emitted FP_ENROLL_JSON
            // The Python script will see ID 999 and run the Cloud Match logic!
          }
        }
      }
    }
    yield();
    delay(80);
  }
}

void printMenu() {
  Serial.println(
      "\n------------------------------------------------------------");
  Serial.println(" COMMANDS (type in Serial Monitor and press Enter):");
  Serial.println(" E -> Enroll a new fingerprint");
  Serial.println(" L -> Lock session (re-authentication required)");
  Serial.println(" D -> Delete ALL fingerprints from sensor memory");
  Serial.println(
      "------------------------------------------------------------\n");
}

// ================================================================
// SETUP
// ================================================================
void setup() {
  Serial.setRxBufferSize(2048);
  Serial.begin(115200);

  pinMode(dotPin, INPUT);
  pinMode(dashPin, INPUT);
  pinMode(controlPin, INPUT);

  fpSerial.begin(57600, SERIAL_8N1, RXD2, TXD2);
  delay(200);
  if (finger.verifyPassword()) {
    Serial.println("[OK] Fingerprint sensor ready on GPIO 25/26.");
  } else {
    fpSerial.begin(9600, SERIAL_8N1, RXD2, TXD2);
    delay(200);
    if (finger.verifyPassword()) {
      Serial.println("[OK] Fingerprint sensor ready at 9600 baud.");
    } else {
      Serial.println(
          "[!] Fingerprint sensor NOT found. Check GPIO 25/26 wiring.");
    }
  }

  Serial.printf("Letter auto-decode gap: %lums\n", LETTER_GAP);
  Serial.println(
      "\n============================================================");
  Serial.println(
      "       WELCOME TO ESP32 BIOMETRIC MORSE CODE SYSTEM         ");
  Serial.println(
      "============================================================");
  Serial.println(
      " FIRST TIME? Type 'E' and press Enter to enroll your finger.");
  Serial.println(
      " CLEAR MEMORY? Type 'D' and press Enter to erase all fingers.");
  Serial.println(" ALREADY ENROLLED? Place your finger on the sensor.");
  Serial.println(
      "============================================================");

  authenticateFingerprint();
  printMenu();
}

// ================================================================
// LOOP
// ================================================================
void loop() {
  // 1. NON-BLOCKING BIOMETRIC SYNC CHECK (Runs every loop instantly)
  fpSyncUpdate();

  unsigned long now = millis();

  // ---- Serial commands ----
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();

    if (line.startsWith("FP_SYNC_JSON:")) {
      String payload = line.substring(13);
      uint8_t decoded[FP_TEMPLATE_MAX];
      uint16_t decLen = 0;
      int pid = -1;
      applyIncomingPayload(payload, decoded, decLen, pid);
      if (pid != -1) {
        startInjectTemplate(pid, decoded, decLen);
      }
    } else if (line.startsWith("FP_DELETE:")) {
      int pid = line.substring(10).toInt();
      finger.deleteModel(pid);
      Serial.printf("[FP_SYNC] Deleted patient #%d locally.\n", pid);
    } else if (line.length() > 0) {
      char cmd = toupper(line.charAt(0));
      if (cmd == 'E') {
        enrollFingerprint();
        printMenu();
      } else if (cmd == 'L') {
        patientAuthenticated = false;
        activePatientID = -1;
        authenticateFingerprint();
        printMenu();
      } else if (cmd == 'D') {
        esp_task_wdt_reset(); // Prevent watchdog during long flash erase
        finger.emptyDatabase();
        delay(500);           // Let sensor settle after mass erase
        esp_task_wdt_reset();
        Serial.println("\n[ESP32] ======================================");
        Serial.println("[ESP32] ALL FINGERPRINTS ERASED FROM SENSOR!");
        Serial.println("[ESP32] ======================================");
        printMenu();
      } else {
        Serial.println("GPT: " + line);
      }
    }
  }

  // ---- Gate: block if not authenticated ----
  if (!patientAuthenticated) {
    authenticateFingerprint();
    return;
  }

  // ================================================================
  // TOUCH SENSOR LOGIC (UNCHANGED)
  // ================================================================
  int dotState = digitalRead(dotPin);
  int dashState = digitalRead(dashPin);
  int controlState = digitalRead(controlPin);

  // ---------- DOT (Short = Dot, Long = Space) ----------
  if (dotState == HIGH && !dotPressed) {
    dotPressed = true;
    dotStartTime = now;
  }
  if (dotState == LOW && dotPressed) {
    dotPressed = false;
    unsigned long duration = now - dotStartTime;

    if (duration >= 2000) {
      // LONG PRESS: SPACE
      sentenceBuffer += " ";
      Serial.println("\n<SPACE ADDED>");
      Serial.print("Current Buffer: ");
      Serial.println(sentenceBuffer);
    } else {
      // SHORT PRESS: DOT
      dotEMA = updateEMA((float)duration, dotEMA);
      updateCUSUM(dotEMA, dotThreshold, dotS_high, dotS_low);
      dotThreshold = max(50.0f, min(500.0f, dotThreshold));
      float conf = computeConfidence((float)duration, dotThreshold);
      accumulateConfidence(conf);
      currentMorse += ".";
      Serial.print(".");
    }
    lastInputTime = now;
    statusPrintedThisIdle = false;
  }

  // ---------- DASH ----------
  if (dashState == HIGH && !dashPressed) {
    dashPressed = true;
    dashStartTime = now;
  }
  if (dashState == LOW && dashPressed) {
    dashPressed = false;
    unsigned long duration = now - dashStartTime;
    dashEMA = updateEMA((float)duration, dashEMA);
    updateCUSUM(dashEMA, dashThreshold, dashS_high, dashS_low);
    dashThreshold = max(50.0f, min(500.0f, dashThreshold));
    float conf = computeConfidence((float)duration, dashThreshold);
    accumulateConfidence(conf);
    currentMorse += "-";
    Serial.print("-");
    lastInputTime = now;
    statusPrintedThisIdle = false;
  }

  // ---------- CONTROL (SEND TO RAG) ----------
  if (controlState == HIGH && !controlPressed) {
    controlPressed = true;
  }
  if (controlState == LOW && controlPressed) {
    controlPressed = false;

    // If they hit control while a letter was still being typed, decode it first
    if (currentMorse != "") {
      handleSpecialMorse(currentMorse);
      currentMorse = "";
    }

    // SEND TO AI SERVER
    Serial.println("\n<SENDING TO AI SERVER...>");
    Serial.print("TOUCH_TEXT:");
    Serial.println(sentenceBuffer);
    evaluateSentenceGate();
    sentenceBuffer = "";
    sentenceConfSum = 0.0f;
    sentenceSymCount = 0;
    statusPrintedThisIdle = false;
  }

  // ---------- AUTO-DECODE ----------
  if (currentMorse != "" && (now - lastInputTime > LETTER_GAP)) {
    Serial.println();
    Serial.printf(" [3s silence -> auto-decoding: \"%s\"]\n",
                  currentMorse.c_str());
    handleSpecialMorse(currentMorse);
    currentMorse = "";
  }

  // ---------- STATUS AFTER 15 SEC IDLE ----------
  if ((now - lastInputTime > IDLE_BEFORE_STATUS) && !statusPrintedThisIdle) {
    statusPrintedThisIdle = true;
    Serial.println("\n############ THRESHOLD STATUS (15s idle) ############");
    Serial.printf("DOT threshold : %.1fms (EMA: %.1fms)\n", dotThreshold,
                  dotEMA);
    Serial.printf("DASH threshold : %.1fms (EMA: %.1fms)\n", dashThreshold,
                  dashEMA);
    Serial.printf("Active Patient : ID #%d\n", activePatientID);
    Serial.println("#######################################################\n");
    Serial.println(" Waiting for touch input... (E=Enroll | L=Lock)");
  }
}

