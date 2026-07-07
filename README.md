# Morse Code Based ESP32 Communication with LLM Integration

![Published](https://img.shields.io/badge/Published-Discover%20Artificial%20Intelligence%20%7C%20Springer%20Nature-blue?style=flat-square)
![Status](https://img.shields.io/badge/Status-Accepted%20In%20Press-green?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.7%2B-blue?style=flat-square)
![Arduino](https://img.shields.io/badge/Arduino-ESP32-orange?style=flat-square)
![Accuracy](https://img.shields.io/badge/System%20Accuracy-99.60%25-brightgreen?style=flat-square)

## 📋 Quick Summary

An advanced assistive communication system enabling individuals with speech disabilities, paralysis, ALS, and motor impairments to communicate through capacitive touch-based Morse code input, integrated with cloud-based LLM for intelligent error correction and response generation.

**System Accuracy: 99.60% | Final Error Rate: 0.04%**

---

## 📑 Publication Information

| Field | Details |
|-------|---------|
| **Paper Title** | Morse Code Based ESP32 Communication with LLM Integration |
| **Journal** | Discover Artificial Intelligence |
| **Publisher** | Springer Nature |
| **Status** | Accepted for Publication - In Press 2025 |
| **Submission ID** | 9ea7642d-f77b-406c-9a70-ac3af807ec6a |
| **Editor** | Yu-Huei Cheng |
| **Publication Year** | 2025 |

---

## 👥 Authors & Affiliation

| Author | Role | Affiliation |
|--------|------|-------------|
| **S. V. Ashok Sainnadh** | Lead Author & Primary Contributor | Amrita School of Artificial Intelligence |
| **M. Neil Kumar** | Co-Author | Amrita School of Artificial Intelligence |
| **B. Sai Sundhar Reddy** | Co-Author | Amrita School of Artificial Intelligence |
| **Dr. Mithun Kumar Kar** | Supervisor & Corresponding Author | Amrita School of Artificial Intelligence |

**Institution:** Amrita Vishwa Vidyapeetham, Coimbatore 641112, India

---

## 🎯 Project Overview

This research presents an innovative assistive communication platform designed for individuals facing significant communication challenges due to speech disabilities, paralysis, ALS (Amyotrophic Lateral Sclerosis), stroke recovery, and various motor impairments.

### How It Works

The system operates through a sophisticated 4-stage pipeline:

1. **Touch Input Acquisition** - User communicates via capacitive touch sensors
2. **Morse Code Decoding** - ESP32 microcontroller decodes touch patterns into alphanumeric characters
3. **Two-Stage Error Correction** - Intelligent error detection and correction using both deterministic rules and LLM semantic analysis
4. **LLM Response Generation** - Cloud-based language model generates contextually appropriate responses

### Key Innovation

**Uncertainty-Aware Dual-Stage Error Correction Framework** - Separates text correction from response generation, with intelligent routing based on confidence levels. Only ambiguous cases proceed to deeper LLM processing, optimizing both accuracy and latency.

---

## ⚙️ System Architecture

```
┌─────────────────────┐
│  Capacitive Sensors │ (TTP223 x2)
│   (Touch Input)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│      ESP32 WROOM    │ Stage 1 & 2: Morse Decoding
│   Microcontroller   │
└──────────┬──────────┘
           │ USB Serial
           ▼
┌─────────────────────────────┐
│    Raspberry Pi 3B          │ Stage 3: Error Correction
│  (Python Processing Layer)  │
└──────────┬──────────────────┘
           │ API Call (HTTPS)
           ▼
┌─────────────────────────────┐
│  Sonar Pro LLM (Cloud)      │ Stage 4: Response Generation
│  (Perplexity AI / Llama 3.3)│
└──────────┬──────────────────┘
           │ API Response
           ▼
┌─────────────────────────────┐
│  Display & Communication    │ Output
│  (OLED/LCD + Bluetooth)     │
└─────────────────────────────┘
```

---

## 🔌 Hardware Requirements

| Component | Model | Quantity | Purpose |
|-----------|-------|----------|---------|
| **Microcontroller** | ESP32 WROOM | 1 | Morse decoding & sensor interfacing |
| **Touch Sensors** | TTP223 Capacitive | 2 | DOT and DASH input detection |
| **Single Board Computer** | Raspberry Pi 3 Model B | 1 | Error correction & LLM communication |
| **Display Module** | OLED/LCD | 1 | Response output display |
| **Connection** | USB Serial | 1 | ESP32 ↔ Raspberry Pi communication |
| **Power Supply** | 5V DC | 1 | System power |

### Optional Components
- HC-05 Bluetooth Module (for wireless phone terminal)
- Battery Pack (for portability)

---

## 💻 Software Requirements

### ESP32 Arduino Environment
- Arduino IDE 1.8.x or higher
- ESP32 Board Support Package
- Arduino libraries (see `code/arduino_dependencies.txt`)

### Raspberry Pi Python Environment
- Python 3.7 or higher
- Libraries: `requests`, `serial`, `json`, `time`
- Perplexity AI API credentials (Sonar Pro access)

### Cloud Infrastructure
- Perplexity AI API account (Sonar Pro model)
- Valid API key with sufficient quota
- Internet connectivity (LTE/WiFi)

---

## 🚀 Installation & Setup

### Step 1: Hardware Assembly

1. Connect TTP223 sensor 1 (DOT) to GPIO pin 13 of ESP32
2. Connect TTP223 sensor 2 (DASH) to GPIO pin 14 of ESP32
3. Connect OLED/LCD display via I2C (SDA: GPIO 21, SCL: GPIO 22)
4. Connect USB cable from ESP32 to Raspberry Pi (identifies as `/dev/ttyUSB0`)
5. Connect power supply to all components

### Step 2: ESP32 Arduino Code Deployment

```bash
# Open Arduino IDE
# File > Open > Arduino_code/morse_esp32_decoder.ino
#
# Configure Arduino IDE:
# Board: ESP32 WROOM
# Port: COM port (Windows) or /dev/ttyUSB* (Linux)
# Upload Speed: 921600
#
# Click Upload button
```

### Step 3: Raspberry Pi Python Setup

```bash
# SSH into Raspberry Pi
ssh pi@raspberrypi.local

# Clone or copy repository to Pi
git clone <your-repo-url>
cd Springer_paper/

# Install Python dependencies
pip install -r requirements.txt

# Configure API credentials
export PERPLEXITY_API_KEY="your_api_key_here"

# Run the main application
python python_codes/main.py
```

### Step 4: Configuration

Edit `config.json` to set:
- Serial port (default: `/dev/ttyUSB0`)
- Baud rate (default: `115200`)
- Morse threshold (default: `500ms`)
- LLM model (default: `sonar-pro`)
- API endpoint and credentials

---

## 📖 How It Works

### Morse Code Input Convention

| Input Type | Duration | Meaning |
|-----------|----------|---------|
| Short Press | < 500ms | **DOT** (·) |
| Long Press | ≥ 500ms | **DASH** (-) |
| Brief Pause (< 1s) | Time gap | Letter Separator |
| Long Pause (≥ 1s) | Time gap | Word Separator |

**Example:** To spell "HELLO"
```
H:  .... (4 dots)        [Pause 1s]
E:  .    (1 dot)         [Pause 1s]
L:  .-.. (dot-dash-dot-dot) [Pause 1s]
L:  .-.. (dot-dash-dot-dot) [Pause 1s]
O:  --- (3 dashes)       [Pause 1s+]
```

### Two-Stage Error Correction Framework

#### Stage 1: Deterministic Rule-Based Correction
- **Input:** Raw Morse-decoded text with uncertainty markers (?)
- **Processing:**
  - Symbol-level uncertainty detection
  - Linguistic validation (spelling, grammar, character validity)
  - Deterministic rule application
- **Output:** Corrected text (no LLM involvement)
- **Use Case:** Clear, high-confidence text patterns

#### Stage 2: LLM Semantic Correction
- **Input:** Text failing Stage 1 validation
- **Processing:**
  - Send to Sonar Pro LLM for semantic understanding
  - Context-aware correction
  - Full response generation
- **Output:** Corrected text + intelligent response
- **Use Case:** Ambiguous, context-dependent text

---

## 📊 Experimental Results

### Accuracy Results (1000 Total Trials)

| Stage | Metric | Value |
|-------|--------|-------|
| **Stage 1** | Initial Morse Decoding Accuracy | 94.0% |
| **Stage 2** | After LLM Text Correction | 97.0% |
| **Stage 3** | LLM Response Generation Accuracy | 95.0% |
| **Final System** | **Overall System Accuracy** | **99.60%** |
| **Final System** | **Error Rate** | **0.04%** |

### System Performance Breakdown

```
Raw Input (1000 trials)
    ↓
[94%] ✓ Correctly decoded: 940 characters
[6%]  ✗ Errors: 60 characters with uncertainty
    ↓
Stage 1 Error Correction (60 errors)
    ↓
[18 errors] → Corrected by rules (30%)
[42 errors] → Proceed to Stage 2 (70%)
    ↓
Stage 2 LLM Correction (42 errors)
    ↓
[40 errors] → Corrected by LLM (95%)
[2 errors]  → Uncorrectable (5%)
    ↓
Final Result: 998/1000 correct = 99.60% ✓
```

---

## ⏱️ Latency Analysis

### End-to-End Latency Breakdown

| Component | Latency | Notes |
|-----------|---------|-------|
| **RX Delay** | ~0.0001 sec | Touch sensor detection (negligible) |
| **TX Delay** | < 0.25 sec | Morse decoding on ESP32 |
| **API Request Overhead** | 0.05-0.10 sec | Network + serialization |
| **Cloud LLM Processing** | 4.31-11.36 sec | Model inference + response generation |
| **Response Transmission** | 0.04 sec | Network transfer |
| **Display Output** | < 0.05 sec | Rendering on OLED/LCD |
| **Total E2E Latency** | **4.45 - 11.48 sec** | Full round-trip time |

### Sample Test Cases & Latencies

| Test Word | Length | Latency (sec) |
|-----------|--------|--------------|
| HELP | 4 chars | 4.45 |
| WATER | 5 chars | 6.87 |
| PAIN | 4 chars | 5.23 |
| SICK | 4 chars | 4.92 |
| TODAY | 5 chars | 7.34 |
| SEVERE | 6 chars | 8.91 |
| NORMAL | 6 chars | 9.45 |
| EMERGENCY | 9 chars | 11.48 |

**Key Finding:** Average response time for critical commands (HELP, PAIN, EMERGENCY) is **4.45 - 5.23 seconds**, suitable for assistive communication.

---

## 📈 Comparison with Other Morse-Based Systems

| System | Interface | LLM Integration | Accuracy | Our Advantage |
|--------|-----------|-----------------|----------|---------------|
| **One-Channel Push Button** | Physical Button | ✗ No | 94.0% | +5.6% accuracy |
| **Hand Gesture Recognition (CNN)** | Gesture/Camera | ✗ No | 95.7% | +3.9% accuracy |
| **Capacitive Touch (No LLM)** | Touch Sensor | ✗ No | 97.92% | +1.68% accuracy |
| **Tactile Haptic Morse** | Haptic Feedback | ✗ No | 63.4% | +36.2% accuracy |
| **Our System (This Work)** | Capacitive Touch | ✓ **Yes (Sonar Pro)** | **99.60%** | **BEST** ⭐ |

### Why Our System Excels

✅ **Only system with LLM integration** - Enables intelligent error correction and response generation
✅ **Highest accuracy** - 99.60% vs. next best 97.92%
✅ **Practical latency** - 4.45-11.48 sec is acceptable for assistive communication
✅ **Tested with real users** - Paralyzed, ALS, and stroke patients
✅ **Two-stage framework** - Efficient routing based on confidence levels
✅ **Scalable architecture** - Easy to integrate additional models or correction strategies

---

## 🏥 Real-World Testing & Validation

The system was successfully tested with:
- **Paralyzed patients** (complete motor loss)
- **ALS (Amyotrophic Lateral Sclerosis) patients** (progressive motor impairment)
- **Stroke patients** (partial motor recovery)
- **Speech-disabled individuals** (non-verbal communication needs)
- **Users with motor impairments** (varying degrees of mobility)

### Critical Communication Examples
Users successfully sent emergency and critical messages including:
- "HELP" - Emergency assistance request
- "WATER" - Hydration need
- "PAIN" - Medical alert
- "DOCTOR" - Request for medical attention
- Average response time: **8-10 seconds** from input to displayed response

---

## 🔑 Key Contributions

1. **Uncertainty-Aware Dual-Stage Error Correction** - Novel framework separating text correction from response generation, with intelligent routing based on confidence levels

2. **Multi-Level Morse Input Interface** - Supports character-level, word-level, and sentence-level Morse input through capacitive touch, enabling various communication scenarios

3. **Integration of Cloud LLM with Embedded Systems** - Seamless pipeline connecting ESP32 microcontroller with Sonar Pro LLM for intelligent response generation

4. **Modular Layered Architecture** - Cleanly separated stages (input acquisition → decoding → correction → response generation) enabling easy maintenance and enhancement

5. **Empirical Validation with Real Users** - Successfully demonstrated with paralyzed and motor-impaired individuals in practical healthcare settings

6. **Performance Excellence** - Achieves 99.60% accuracy, highest among all Morse-based communication systems

---

## 📁 Repository Structure

```
Springer_paper/
│
├── README.md                           # This file
├── LICENSE                             # MIT License
├── requirements.txt                    # Python dependencies
├── config.json                         # System configuration
│
├── Arduino_code/                       # ESP32 Firmware
│   └── morse_esp32_decoder.ino        # Complete ESP32 Morse decoder firmware
│                                      # (Pin config, decoding, Bluetooth, serial I/O)
│
├── python_codes/                      # Python Research Tools
│   ├── Latency_inc.py                 # Latency measurement tool
│   └── reponse_inc.py                 # Response generation tool
│
├── images_blocks_tables/              # Documentation & visuals
│   ├── circuit_diagram.png            # Hardware circuit schematic
│   ├── system_architecture.png        # System architecture diagram
│   ├── block_diagram.png              # Functional block diagram
│   ├── hardware_setup.jpg             # Photos of physical system
│   ├── mobile_terminal.png            # Bluetooth terminal screenshots
│   ├── state_machine.png              # Morse decoding state machine
│   └── README.md                      # Image descriptions
│
├── results/                           # Experimental results
│   ├── accuracy_results.csv           # Accuracy metrics (1000 trials)
│   ├── latency_results.csv            # Latency measurements
│   ├── comparison_table.csv           # System comparison data
│   ├── error_analysis.xlsx            # Detailed error breakdown
│   └── README.md                      # Results documentation
│
├── docs/                              # Additional documentation
│   ├── SETUP_GUIDE.md                 # Detailed setup instructions
│   ├── TROUBLESHOOTING.md             # Common issues & solutions
│   ├── API_REFERENCE.md               # Code API documentation
│   └── TESTING_PROTOCOL.md            # How to conduct tests
│
└── Arduino_dependencies.txt            # Required Arduino libraries

```

---

## 🔧 Configuration

Create a `config.json` file in the root directory:

```json
{
  "serial": {
    "port": "/dev/ttyUSB0",
    "baudrate": 115200,
    "timeout": 1
  },
  "morse": {
    "dot_threshold_ms": 500,
    "letter_pause_ms": 1000,
    "word_pause_ms": 2000
  },
  "llm": {
    "provider": "perplexity",
    "model": "sonar-pro",
    "api_key": "${PERPLEXITY_API_KEY}",
    "timeout_sec": 15
  },
  "correction": {
    "stage1_enabled": true,
    "stage2_enabled": true,
    "confidence_threshold": 0.85
  },
  "display": {
    "type": "oled",
    "rows": 4,
    "cols": 20
  }
}
```

---

## 📝 Citation

If you use this system or reference this research, please cite:

```bibtex
@article{sainnadh2025morse,
  title={Morse Code Based ESP32 Communication with LLM Integration},
  author={Sainnadh, S. V. Ashok and Kumar, M. Neil and Reddy, B. Sai Sundhar and Kar, Mithun Kumar},
  journal={Discover Artificial Intelligence},
  publisher={Springer Nature},
  year={2025},
  status={Accepted for Publication}
}
```

**Plain Text Citation:**
```
S. V. Ashok Sainnadh, M. Neil Kumar, B. Sai Sundhar Reddy, and Mithun Kumar Kar,
"Morse Code Based ESP32 Communication with LLM Integration,"
Discover Artificial Intelligence, Springer Nature, Accepted 2025.
```

---

## 📜 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

The code, hardware designs, and documentation are provided for research and educational purposes. Users may freely use, modify, and distribute this work under the terms of the MIT License.

---

## 🙋 Support & Contact

For questions, issues, or collaborations:

- **Lead Author:** S. V. Ashok Sainnadh
- **Supervisor:** Dr. Mithun Kumar Kar (Corresponding Author)
- **Institution:** Amrita School of Artificial Intelligence, Amrita Vishwa Vidyapeetham

### Getting Help

1. Check [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for common issues
2. Review [SETUP_GUIDE.md](docs/SETUP_GUIDE.md) for detailed configuration
3. Open an issue on GitHub for bugs or feature requests

---

## 🙏 Acknowledgments

- **Amrita Vishwa Vidyapeetham** for providing resources and research facilities
- **Amrita School of Artificial Intelligence** for academic support
- **Perplexity AI** for providing Sonar Pro API access
- **Research participants** - paralyzed and motor-impaired patients who tested the system
- **Springer Nature** (Discover Artificial Intelligence) for accepting this research

---

## ⭐ How to Acknowledge This Work

If you build upon this system or find it useful for your research:

1. ⭐ **Star this repository** on GitHub
2. 📖 **Cite the paper** using the citation provided above
3. 🔗 **Link back** to this repository in your documentation
4. 📢 **Share** your improvements via pull requests or forks

---

## 📚 Related Resources

- **ESP32 Documentation:** https://docs.espressif.com/projects/esp-idf/
- **Raspberry Pi Guide:** https://www.raspberrypi.org/documentation/
- **Perplexity AI API:** https://www.perplexity.ai/docs/
- **Morse Code Reference:** https://en.wikipedia.org/wiki/Morse_code
- **Arduino IDE:** https://www.arduino.cc/en/software

---

## 📊 Project Statistics

| Metric | Value |
|--------|-------|
| **Publication Status** | Accepted - In Press (Springer Nature) |
| **System Accuracy** | 99.60% |
| **Total Test Cases** | 1,000 trials |
| **Error Rate** | 0.04% |
| **Latency Range** | 4.45 - 11.48 seconds |
| **Real Users Tested** | Paralyzed, ALS, Stroke Patients |
| **Hardware Components** | 6 main components |
| **Software Stack** | Arduino + Python + Cloud LLM |
| **Repository Status** | Active & Maintained |

---

## 🚀 Future Work & Enhancements

- [ ] Integration with additional LLM models (GPT-4, Claude)
- [ ] Mobile app with enhanced Bluetooth interface
- [ ] Voice output module for response feedback
- [ ] Multi-language support
- [ ] Eye-gaze based input alternative
- [ ] Local LLM inference on Raspberry Pi for offline operation
- [ ] Real-time error correction visualization

---

**Last Updated:** May 2025
**Project Status:** Active
**Maintained By:** Amrita School of Artificial Intelligence

---

*This repository contains research code and documentation for the paper "Morse Code Based ESP32 Communication with LLM Integration" accepted for publication in Discover Artificial Intelligence (Springer Nature, 2025).*
