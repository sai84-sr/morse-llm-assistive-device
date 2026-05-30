# API Reference Documentation

Complete API documentation for the Morse Code ESP32 Communication System with LLM Integration.

## Table of Contents

1. [Python API](#python-api)
2. [Perplexity AI Integration](#perplexity-ai-integration)
3. [Serial Communication Protocol](#serial-communication-protocol)
4. [Configuration Schema](#configuration-schema)
5. [Error Codes & Responses](#error-codes--responses)
6. [Code Examples](#code-examples)

---

## Python API

### Main Application Class

#### `MorseCommSystem`

Main controller class orchestrating the entire communication pipeline.

```python
class MorseCommSystem:
    """
    Morse code communication system with LLM integration.
    
    Attributes:
        config (dict): System configuration
        serial_handler (SerialHandler): Serial communication manager
        morse_decoder (MorseDecoder): Morse to text decoder
        error_corrector (ErrorCorrector): Two-stage error correction
        llm_interface (LLMInterface): Perplexity AI interface
        display_handler (DisplayHandler): OLED/LCD output handler
    """
    
    def __init__(self, config_file='config.json'):
        """
        Initialize the Morse communication system.
        
        Args:
            config_file (str): Path to configuration JSON file
            
        Raises:
            FileNotFoundError: If config file not found
            json.JSONDecodeError: If config file is invalid JSON
        """
        pass
    
    def start(self):
        """
        Start the main event loop for receiving Morse input.
        
        Returns:
            None
            
        Raises:
            SerialException: If serial connection fails
            RuntimeError: If initialization incomplete
        """
        pass
    
    def stop(self):
        """
        Stop the system gracefully.
        
        Closes all connections and saves metrics.
        
        Returns:
            None
        """
        pass
    
    def process_morse_input(self, morse_string: str) -> dict:
        """
        Process raw Morse code input through the pipeline.
        
        Args:
            morse_string (str): Raw Morse input (dots and dashes)
            
        Returns:
            dict: {
                'raw_text': str,
                'corrected_text': str,
                'llm_response': str,
                'confidence': float,
                'latency': float
            }
            
        Example:
            result = system.process_morse_input('· - · - ·')
            # Returns: {'raw_text': 'A', 'corrected_text': 'A', ...}
        """
        pass
```

### Serial Handler

#### `SerialHandler`

Manages USB serial communication with ESP32.

```python
class SerialHandler:
    """
    Handles serial communication with ESP32 microcontroller.
    
    Attributes:
        port (str): Serial port (e.g., '/dev/ttyUSB0')
        baudrate (int): Baud rate (default: 115200)
    """
    
    def __init__(self, port: str, baudrate: int = 115200):
        """
        Initialize serial connection.
        
        Args:
            port (str): Serial port path
            baudrate (int): Communication speed in bps
            
        Raises:
            SerialException: If port cannot be opened
        """
        pass
    
    def read_line(self, timeout: float = 1.0) -> str:
        """
        Read one line of data from serial port.
        
        Args:
            timeout (float): Read timeout in seconds
            
        Returns:
            str: One line of data (newline stripped)
            
        Raises:
            SerialTimeoutException: If no data within timeout
        """
        pass
    
    def write_data(self, data: str) -> int:
        """
        Write data to serial port.
        
        Args:
            data (str): Data to write
            
        Returns:
            int: Number of bytes written
            
        Raises:
            SerialException: If write fails
        """
        pass
    
    def close(self):
        """Close serial connection."""
        pass
```

### Morse Decoder

#### `MorseDecoder`

Decodes Morse patterns into characters.

```python
class MorseDecoder:
    """
    Converts Morse code sequences to alphanumeric text.
    
    Morse Convention:
        · = dot (short press < 500ms)
        - = dash (long press >= 500ms)
        | = letter separator
        || = word separator
    """
    
    def decode_character(self, morse_char: str) -> tuple:
        """
        Decode single Morse character.
        
        Args:
            morse_char (str): Morse pattern (e.g., '·-')
            
        Returns:
            tuple: (character, confidence_level)
                character (str): Decoded letter/number or '?'
                confidence_level (float): 0.0 to 1.0
                
        Example:
            char, conf = decoder.decode_character('·-')
            # Returns: ('A', 1.0)
        """
        pass
    
    def decode_word(self, morse_word: str) -> tuple:
        """
        Decode complete Morse word.
        
        Args:
            morse_word (str): Space-separated Morse characters
            
        Returns:
            tuple: (word, avg_confidence)
            
        Example:
            word, conf = decoder.decode_word('·- · ·-· · ·')
            # Returns: ('ALERT', 0.92)
        """
        pass
```

### Error Corrector

#### `ErrorCorrector`

Two-stage error correction system.

```python
class ErrorCorrector:
    """
    Two-stage uncertainty-aware error correction.
    
    Stage 1: Rule-based deterministic correction
    Stage 2: LLM-based semantic correction
    """
    
    def stage1_correct(self, text: str) -> tuple:
        """
        Stage 1: Deterministic rule-based correction.
        
        Detects and corrects:
        - Spelling errors
        - Invalid character sequences
        - Common Morse mistakes
        
        Args:
            text (str): Raw decoded text (may contain '?')
            
        Returns:
            tuple: (corrected_text, needs_stage2)
                corrected_text (str): Text after rule application
                needs_stage2 (bool): Whether to proceed to Stage 2
                
        Example:
            text, needs_llm = corrector.stage1_correct('HEL?O')
            # Returns: ('HELLO', False)
        """
        pass
    
    async def stage2_correct(self, text: str, llm_interface) -> str:
        """
        Stage 2: LLM-based semantic correction.
        
        Uses Sonar Pro LLM for context-aware correction.
        
        Args:
            text (str): Text from Stage 1
            llm_interface: LLM interface object
            
        Returns:
            str: Corrected and contextualized text
            
        Example:
            result = await corrector.stage2_correct('HE WNT', llm)
            # Returns: 'HE WENT'
        """
        pass
```

### LLM Interface

#### `LLMInterface`

Communicates with Perplexity AI API.

```python
class LLMInterface:
    """
    Interface to Sonar Pro LLM via Perplexity AI API.
    
    Attributes:
        model (str): Model name ('sonar-pro')
        api_key (str): Perplexity API key
        api_endpoint (str): API base URL
    """
    
    def __init__(self, api_key: str, model: str = 'sonar-pro'):
        """
        Initialize LLM interface.
        
        Args:
            api_key (str): Perplexity API key
            model (str): Model identifier
            
        Raises:
            ValueError: If API key is invalid
        """
        pass
    
    async def generate_response(self, text: str, max_tokens: int = 512) -> dict:
        """
        Generate LLM response for given text.
        
        Args:
            text (str): Input text
            max_tokens (int): Maximum response length
            
        Returns:
            dict: {
                'response': str,
                'tokens_used': int,
                'latency_ms': float,
                'model': str
            }
            
        Raises:
            requests.HTTPError: If API request fails
            asyncio.TimeoutError: If request exceeds timeout
            
        Example:
            result = await llm.generate_response('HELLO')
            # Returns: {'response': 'Hello! How can I help?', ...}
        """
        pass
    
    async def correct_text(self, text: str) -> str:
        """
        Use LLM to correct text errors.
        
        Args:
            text (str): Text to correct
            
        Returns:
            str: Corrected text
            
        Example:
            corrected = await llm.correct_text('HEL THRE')
            # Returns: 'HELLO THERE'
        """
        pass
```

### Display Handler

#### `DisplayHandler`

Manages OLED/LCD output.

```python
class DisplayHandler:
    """
    Handles display output to OLED/LCD screen.
    
    Attributes:
        display_type (str): 'oled' or 'lcd'
        rows (int): Display rows
        cols (int): Display columns
    """
    
    def __init__(self, display_type: str = 'oled', rows: int = 4, cols: int = 20):
        """
        Initialize display handler.
        
        Args:
            display_type (str): Type of display
            rows (int): Number of rows
            cols (int): Number of columns
        """
        pass
    
    def display_text(self, text: str, row: int = 0, clear: bool = False):
        """
        Display text on screen.
        
        Args:
            text (str): Text to display
            row (int): Row number (0-based)
            clear (bool): Clear screen before displaying
            
        Returns:
            None
        """
        pass
    
    def display_response(self, response: str, latency_ms: float):
        """
        Display LLM response with formatting.
        
        Args:
            response (str): Response text
            latency_ms (float): Response latency in milliseconds
            
        Returns:
            None
        """
        pass
    
    def clear_display(self):
        """Clear all text from display."""
        pass
```

---

## Perplexity AI Integration

### API Request Format

```python
import requests

# API endpoint
API_URL = "https://api.perplexity.ai/chat/completions"

# Request headers
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Request payload
payload = {
    "model": "sonar-pro",
    "messages": [
        {
            "role": "user",
            "content": "What is Morse code?"
        }
    ],
    "max_tokens": 512,
    "temperature": 0.7
}

# Send request
response = requests.post(API_URL, headers=headers, json=payload, timeout=15)
result = response.json()

# Response format
# {
#     "id": "cmpl-...",
#     "object": "text_completion",
#     "created": 1234567890,
#     "model": "sonar-pro",
#     "choices": [
#         {
#             "index": 0,
#             "message": {
#                 "role": "assistant",
#                 "content": "Morse code is a method of..."
#             },
#             "finish_reason": "stop"
#         }
#     ],
#     "usage": {
#         "prompt_tokens": 15,
#         "completion_tokens": 87,
#         "total_tokens": 102
#     }
# }
```

### API Rate Limits

| Tier | Requests/Min | Tokens/Min |
|------|--------------|-----------|
| Free | 10 | 5000 |
| Pro | 60 | 30000 |
| Business | Custom | Custom |

### Available Models

- `sonar-pro`: Latest Sonar Pro model (recommended)
- `sonar`: Standard Sonar model
- `sonar-long`: Long context variant

---

## Serial Communication Protocol

### ESP32 → Raspberry Pi Format

Data sent by ESP32 to Raspberry Pi via USB serial.

```
Format: [MORSE_DATA]\n

Example transmissions:
· · · ·|  (character: A)
· · · ·|− ·|  (character: B)
· − ·|  (character: K)
[pause ~2s]
− − −||  (character: O)

Full example for "HELP":
· · · ·|  (H)
·|  (E)
· − · ·|  (L)
· − − −|  (P)
```

### Character Set

**Letters (A-Z):**
```
A: · −     N: − ·
B: − · · · O: − − −
C: − · − · P: · − − ·
D: − · ·   Q: − − · −
E: ·       R: · − ·
F: · · − · S: · · ·
G: − − ·   T: −
H: · · · · U: · · −
I: · ·     V: · · · −
J: · − − − W: · − −
K: − · −   X: − · · −
L: · − · · Y: − · − −
M: − −     Z: − − · ·
```

**Numbers (0-9):**
```
0: − − − − −
1: · − − − −
2: · · − − −
3: · · · − −
4: · · · · −
5: · · · · ·
6: − · · · ·
7: − − · · ·
8: − − − · ·
9: − − − − ·
```

---

## Configuration Schema

### Complete Configuration Structure

```json
{
  "serial": {
    "port": "string (e.g., /dev/ttyUSB0)",
    "baudrate": "integer (default: 115200)",
    "timeout": "float in seconds (default: 1.0)"
  },
  
  "morse": {
    "dot_threshold_ms": "integer (milliseconds for dot, default: 500)",
    "letter_pause_ms": "integer (milliseconds, default: 1000)",
    "word_pause_ms": "integer (milliseconds, default: 2000)"
  },
  
  "llm": {
    "provider": "string (perplexity)",
    "model": "string (sonar-pro, sonar, sonar-long)",
    "api_key": "string (from environment or config)",
    "api_endpoint": "string (Perplexity API URL)",
    "timeout_sec": "integer (request timeout, default: 15)",
    "max_tokens": "integer (default: 512)",
    "temperature": "float 0.0-1.0 (default: 0.7)"
  },
  
  "error_correction": {
    "stage1_enabled": "boolean (default: true)",
    "stage2_enabled": "boolean (default: true)",
    "confidence_threshold": "float 0.0-1.0 (default: 0.85)",
    "spelling_check": "boolean (default: true)",
    "grammar_check": "boolean (default: false)"
  },
  
  "display": {
    "type": "string (oled, lcd)",
    "i2c_address": "string hex (0x3C)",
    "rows": "integer (default: 4)",
    "cols": "integer (default: 20)",
    "brightness": "integer 0-255 (default: 255)"
  },
  
  "logging": {
    "level": "string (DEBUG, INFO, WARNING, ERROR)",
    "log_file": "string (file path)",
    "max_file_size_mb": "integer",
    "backup_count": "integer"
  },
  
  "performance": {
    "measure_latency": "boolean",
    "measure_accuracy": "boolean",
    "save_metrics": "boolean",
    "metrics_file": "string (file path)"
  }
}
```

---

## Error Codes & Responses

### System Errors

| Code | Message | Cause | Solution |
|------|---------|-------|----------|
| `E001` | Serial connection failed | Port not available | Check USB cable, verify port in config |
| `E002` | Invalid API key | Authentication failed | Verify Perplexity API key |
| `E003` | LLM request timeout | Network or API slow | Increase timeout, check connection |
| `E004` | Display initialization failed | I2C error | Check OLED connections, verify address |
| `E005` | Configuration file missing | Config.json not found | Create config.json in root directory |

### Response Codes

```python
# Success response
{
    "status": "success",
    "data": {
        "morse_input": "· − · − ·",
        "decoded_text": "ALERT",
        "corrected_text": "ALERT",
        "llm_response": "Alert received. Emergency services notified.",
        "latency_ms": 4567,
        "confidence": 0.98
    }
}

# Error response
{
    "status": "error",
    "error_code": "E003",
    "error_message": "LLM request timeout",
    "timestamp": "2025-05-30T10:30:45Z"
}
```

---

## Code Examples

### Example 1: Basic Usage

```python
from morse_system import MorseCommSystem

# Initialize system
system = MorseCommSystem('config.json')

# Start receiving input
system.start()

# Process Morse input
result = system.process_morse_input('· − · − ·')
print(f"Decoded: {result['decoded_text']}")
print(f"Response: {result['llm_response']}")
print(f"Latency: {result['latency']}ms")

# Stop system
system.stop()
```

### Example 2: Custom Error Correction

```python
from error_correction import ErrorCorrector
from llm_interface import LLMInterface

corrector = ErrorCorrector()
llm = LLMInterface(api_key="sk-...")

# Stage 1: Rule-based
text, needs_llm = corrector.stage1_correct("HEL?O")
print(f"After Stage 1: {text}")  # "HELLO"

# Stage 2: LLM-based (if needed)
if needs_llm:
    final_text = corrector.stage2_correct(text, llm)
    print(f"After Stage 2: {final_text}")
```

### Example 3: Display Output

```python
from display_handler import DisplayHandler

display = DisplayHandler(display_type='oled', rows=4, cols=20)

# Display input
display.display_text("INPUT: HELLO", row=0, clear=True)

# Display response
display.display_response(
    response="Hello! How are you?",
    latency_ms=4567
)

# Clear display
display.clear_display()
```

### Example 4: Direct LLM API Call

```python
import requests
import asyncio

async def test_llm():
    api_key = "sk-..."
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "sonar-pro",
        "messages": [
            {"role": "user", "content": "Hello, can you help me?"}
        ],
        "max_tokens": 200
    }
    
    response = requests.post(
        "https://api.perplexity.ai/chat/completions",
        headers=headers,
        json=payload,
        timeout=15
    )
    
    if response.status_code == 200:
        result = response.json()
        message = result['choices'][0]['message']['content']
        print(f"LLM Response: {message}")
    else:
        print(f"Error: {response.status_code}")

# Run
asyncio.run(test_llm())
```

### Example 5: Custom Configuration

```python
import json

# Create custom config
config = {
    "serial": {
        "port": "/dev/ttyUSB0",
        "baudrate": 115200
    },
    "morse": {
        "dot_threshold_ms": 450,  # Adjusted
        "letter_pause_ms": 1200,  # Adjusted
        "word_pause_ms": 2500     # Adjusted
    },
    "llm": {
        "model": "sonar-pro",
        "max_tokens": 256,        # Limited output
        "temperature": 0.5        # More deterministic
    }
}

# Save config
with open('custom_config.json', 'w') as f:
    json.dump(config, f, indent=2)

# Use custom config
system = MorseCommSystem('custom_config.json')
system.start()
```

---

**Last Updated:** May 2025
