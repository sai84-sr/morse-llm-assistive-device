"""
BIATS V3 Production Hospital Server
- V1 Core: SentenceTransformer (Bio_ClinicalBERT) embedding engine — same as V1 base
- V3 New: BP + RR + ECG vitals, Pain scale, Nurse assignment, Audit CSV
- V3 New: Full intent-to-sentence natural language output
- V3 New: Triage sorting, RL feedback healing, BioBot fallback
"""

import os, argparse, sqlite3, random, time, math, csv, io, json
from flask import Flask, render_template, request, jsonify, Response
from flask_socketio import SocketIO, emit, join_room
from chromadb.utils import embedding_functions
import chromadb
import threading

app = Flask(__name__)
# FORCE threading mode to completely prevent Eventlet from freezing the server on the Raspberry Pi
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

chroma_client   = None
collection      = None

chroma_lock = threading.Lock()

def safe_chroma_query(text, n=3):
    # Queries using query_texts — chromadb handles embedding internally via
    # SentenceTransformerEmbeddingFunction (same as V1 base system)
    with chroma_lock:
        return collection.query(query_texts=[text], n_results=n)

# In-memory nurse assignment store: {patient_id: nurse_name}
nurse_assignments = {}
emergency_mode = False

def get_db():
    conn = sqlite3.connect('biats_v3.db', check_same_thread=False, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    
    # Auto-initialize database tables if they do not exist
    cursor = conn.cursor()
    cursor.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='patients'")
    if cursor.fetchone()[0] == 0:
        print("[BIATS V3] Initializing fresh SQL database (biats_v3.db)...")
        conn.execute('''CREATE TABLE patients (
            patient_id INTEGER PRIMARY KEY,
            name TEXT,
            room_number TEXT,
            ward_id INTEGER,
            doctor_rank INTEGER DEFAULT 0
        )''')
        conn.execute('''CREATE TABLE conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            ward_id INTEGER,
            raw_input TEXT,
            rag_output TEXT,
            triage TEXT,
            probability REAL,
            secondary_rag_output TEXT,
            secondary_probability REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            responded_nurse_id INTEGER,
            nurse_responded_at TIMESTAMP,
            response_time_sec INTEGER,
            nurse_feedback TEXT
        )''')
        # Insert some dummy patients so we don't crash when Patient #1 or #2 connects
        for i in range(1, 11):
            conn.execute("INSERT INTO patients (patient_id, name, ward_id, room_number) VALUES (?, ?, ?, ?)", 
                         (i, f"Patient {i}", 1, f"Room {100+i}"))
        conn.commit()
        
    return conn

def get_fp_db():
    """V3 RAG Backend - Dedicated Fingerprint Template Database"""
    conn = sqlite3.connect('fp_templates.db', check_same_thread=False)
    conn.execute("""CREATE TABLE IF NOT EXISTS fp_templates (
        patient_id INTEGER PRIMARY KEY,
        template_b64 TEXT NOT NULL,
        payload_json TEXT,
        updated_at REAL NOT NULL,
        deleted INTEGER DEFAULT 0
    )""")
    return conn

def calculate_probability(distance):
    return round(max(0.0, 100.0 - (distance * 20.0)), 1)

def get_triage(intent, hr=None, spo2=None):
    """Triage classification with optional vitals-aware override (5-level ESI)."""
    intent = intent.lower()
    
    if any(kw in intent for kw in ["cardiac arrest", "respiratory failure", "choking", "seizure", "unresponsive", "code"]):
        base = "CODE"
    elif any(kw in intent for kw in ["chest pain", "need suction", "suction", "difficulty breathing", "severe pain", "hemorrhage", "stroke", "anaphylaxis", "trauma", "loss of consciousness", "pain"]):
        base = "CRITICAL"
    elif any(kw in intent for kw in ["need bathroom", "bathroom", "medication", "vomiting", "dizziness", "fever", "bleeding", "allergic", "call nurse", "nurse", "iv issue", "catheter", "confusion", "headache"]):
        base = "URGENT"
    elif any(kw in intent for kw in ["bed", "hot", "cold", "hungry", "thirsty", "doctor", "family", "blanket", "position", "nausea"]):
        base = "ROUTINE"
    else:
        base = "STABLE"

    # V2: vitals-aware override
    if hr and hr > 150:
        base = "CODE"
    elif hr and hr > 130:
        base = "CRITICAL"
        
    if spo2 and spo2 < 85:
        base = "CODE"
    elif spo2 and spo2 < 90:
        base = "CRITICAL"

    return base

# ── INTENT → FULL SENTENCE LOOKUP (The Heart of V1 Output) ─────────
INTENT_SENTENCES = {
    # Emergency / Critical
    "cardiac arrest":          "EMERGENCY: Patient may be experiencing CARDIAC ARREST. Call code team immediately!",
    "respiratory failure":     "EMERGENCY: Patient is in RESPIRATORY FAILURE. Immediate airway intervention needed!",
    "choking":                 "EMERGENCY: Patient is CHOKING and cannot breathe. Immediate assistance required!",
    "seizure":                 "EMERGENCY: Patient is having a SEIZURE. Clear the area and call for help immediately!",
    "unresponsive":            "EMERGENCY: Patient is UNRESPONSIVE. Check pulse and breathing immediately!",
    "hemorrhage":              "EMERGENCY: Patient is experiencing SEVERE BLEEDING. Apply pressure and call for help!",
    "stroke symptoms":         "EMERGENCY: Patient is showing STROKE symptoms (FAST). Call code team now!",
    "anaphylaxis":             "EMERGENCY: Patient is in ANAPHYLACTIC SHOCK. Administer epinephrine immediately!",
    "loss of consciousness":   "EMERGENCY: Patient has LOST CONSCIOUSNESS. Do not leave patient alone!",

    # Critical
    "chest pain":              "CRITICAL: Patient is experiencing CHEST PAIN. ECG and cardiac assessment needed urgently.",
    "need suction":            "CRITICAL: Patient needs SUCTIONING immediately. Airway is compromised.",
    "difficulty breathing":    "CRITICAL: Patient is having DIFFICULTY BREATHING. Oxygen and respiratory assessment needed.",
    "severe pain":             "CRITICAL: Patient is in SEVERE PAIN. Pain assessment and medication review needed.",
    "fall trauma":             "CRITICAL: Patient has suffered a FALL or TRAUMA. Assess for injuries immediately.",

    # Urgent — Physical Needs
    "need bathroom":           "URGENT: Patient needs to use the BATHROOM. Please assist immediately.",
    "medication":              "URGENT: Patient is requesting MEDICATION. Please check prescription and administer.",
    "vomiting":                "URGENT: Patient is VOMITING. Provide basin, fluids, and antiemetic if prescribed.",
    "dizziness":               "URGENT: Patient is feeling DIZZY. Ensure patient is safely positioned and assess vitals.",
    "fever":                   "URGENT: Patient has a FEVER. Measure temperature and administer antipyretics as prescribed.",
    "mild bleeding":           "URGENT: Patient reports MILD BLEEDING. Please inspect wound and apply appropriate dressing.",
    "allergic reaction":       "URGENT: Patient is having an ALLERGIC REACTION. Assess severity and administer antihistamine.",
    "iv issue":                "URGENT: Patient reports an issue with their IV LINE. Please check and re-site if necessary.",
    "catheter issue":          "URGENT: Patient reports CATHETER discomfort or blockage. Please inspect and resolve.",
    "confusion":               "URGENT: Patient is experiencing CONFUSION. Assess orientation and check for underlying cause.",
    "headache":                "URGENT: Patient is experiencing a HEADACHE. Assess severity and pain scale.",

    # Nurse / Doctor calls
    "call nurse":              "Patient is calling for a NURSE. Please attend to the patient's room.",
    "call doctor":             "Patient is requesting to speak with the DOCTOR. Please notify the attending physician.",

    # Comfort / Routine
    "thirsty":                 "Patient is THIRSTY and would like water or a drink. Please bring fluids.",
    "water":                   "Patient wants WATER. Please bring a glass of water to the room.",
    "need water":              "Patient needs WATER urgently. Please assist.",
    "hungry":                  "Patient is HUNGRY and would like something to eat. Please arrange a meal.",
    "food":                    "Patient is requesting FOOD. Please arrange a meal or snack.",
    "hot":                     "Patient feels too HOT. Please adjust the room temperature or provide a fan.",
    "cold":                    "Patient feels COLD. Please bring an extra blanket or adjust the room temperature.",
    "blanket":                 "Patient is requesting a BLANKET. Please bring one to the patient's room.",
    "nausea":                  "Patient is feeling NAUSEOUS. Please bring an emesis basin and notify for antiemetic.",
    "bed up":                  "Patient requests the HEAD OF BED to be raised. Please adjust the bed position.",
    "bed lower":               "Patient requests the bed to be LOWERED or flattened. Please adjust the bed position.",
    "change position":         "Patient needs to be RE-POSITIONED to prevent pressure sores. Please assist.",
    "family":                  "Patient is requesting FAMILY VISIT. Please check visiting hours and notify family.",

    # Entertainment / Wellness
    "take me outside":         "Patient would like to go OUTSIDE or to a common area. Please arrange if possible.",
    "tv on":                   "Patient wants to turn the TV ON. Please assist with the remote or controls.",
    "tv off":                  "Patient wants to turn the TV OFF. Please assist.",
    "lights on":               "Patient wants the LIGHTS ON. Please turn on the room lights.",
    "lights off":              "Patient wants the LIGHTS OFF. Please dim or turn off the room lights.",
    "music":                   "Patient would like to listen to MUSIC. Please assist with playing music.",
    "reading":                 "Patient would like something to READ. Please bring books or magazines.",
    "bored":                   "Patient is BORED and needs engagement. Consider activities, TV, or family visits.",

    # Social
    "thank you":               "Patient is expressing GRATITUDE. Thank you acknowledged!",
    "hello":                   "Patient says HELLO. Please check in on the patient.",

    # Mouse is a known false-positive from Morse code confusion
    "mouse":                   "Patient sent an unclear signal. Please visit and check on patient's needs.",
}

def get_sentence(intent: str) -> str:
    """Convert an intent label to a full natural-language sentence."""
    intent_lower = intent.lower().strip()
    # Direct lookup
    if intent_lower in INTENT_SENTENCES:
        return INTENT_SENTENCES[intent_lower]
    # Fuzzy partial match
    for key, sentence in INTENT_SENTENCES.items():
        if key in intent_lower or intent_lower in key:
            return sentence
    # Fallback: humanize the intent label
    return f"Patient is requesting: {intent.replace('_', ' ').title()}. Please attend to the patient."

# ── ROUTES ────────────────────────────────────────────────────────


@app.route('/')
def index():
    return "BIATS-II V2 Ward Hub. Navigate to /patient, /ward/1, or /admin"

@app.route('/patient')
def patient_lobby_view():
    conn = get_db()
    patients = conn.execute("SELECT * FROM patients").fetchall()
    conn.close()
    return render_template('patient_lobby.html', patients=patients)

@app.route('/patient/<int:patient_id>')
def patient_view(patient_id):
    conn = get_db()
    pt = conn.execute("SELECT * FROM patients WHERE patient_id=?", (patient_id,)).fetchone()
    all_patients = conn.execute("SELECT * FROM patients ORDER BY patient_id ASC").fetchall()
    conn.close()
    if not pt:
        return "Patient not found", 404
    return render_template('patient.html',
                           patient_id=patient_id,
                           ward=pt['ward_id'],
                           all_patients=all_patients,
                           current_patient_name=pt['name'],
                           current_room=pt['room_number'])

@app.route('/ward/<int:ward_id>')
def ward_view(ward_id):
    conn = get_db()
    patients = conn.execute("SELECT * FROM patients WHERE ward_id=? ORDER BY doctor_rank DESC", (ward_id,)).fetchall()
    conn.close()
    nurses = [f"Nurse {ward_id}.{i}" for i in range(1, 16)]
    return render_template('ward.html', ward_id=ward_id, patients=patients, nurses=nurses)

@app.route('/admin')
def admin_view():
    conn = get_db()
    patients = conn.execute("SELECT * FROM patients ORDER BY ward_id ASC, doctor_rank DESC").fetchall()
    conn.close()
    return render_template('admin.html', patients=patients)

# ── REST API ENDPOINTS (V2 NEW) ────────────────────────────────────

@app.route('/api/conversations/<int:patient_id>')
def api_get_conversations(patient_id):
    conn = get_db()
    data = [dict(r) for r in conn.execute(
        "SELECT * FROM conversations WHERE patient_id=? ORDER BY created_at DESC", (patient_id,)
    ).fetchall()]
    conn.close()
    return jsonify(data)

@app.route('/health')
def health_check():
    try:
        conn = get_db()
        pt_count = conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
        try:
            conv_count = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        except:
            conv_count = 0
        conn.close()
        chroma_count = collection.count() if collection else 0
        return jsonify({
            'status': 'healthy',
            'patients': pt_count,
            'conversations': conv_count,
            'chroma_vectors': chroma_count,
            'emergency_mode': emergency_mode,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

@app.route('/api/pain_scale', methods=['POST'])
def api_pain_scale():
    """V2: Patient pain scale input (1-10) — bypasses Morse, sends directly as CRITICAL."""
    data       = request.get_json()
    patient_id = int(data.get('patient_id'))
    pain_level = int(data.get('pain_level', 5))
    
    conn = get_db()
    pt = conn.execute("SELECT * FROM patients WHERE patient_id=?", (patient_id,)).fetchone()
    ward_id = pt['ward_id'] if pt else 1
    name    = pt['name'] if pt else f"Patient {patient_id}"
    room    = pt['room_number'] if pt else f"10{patient_id}"
    
    intent  = f"pain_level_{pain_level}"
    triage  = "CRITICAL" if pain_level >= 7 else ("URGENT" if pain_level >= 4 else "ROUTINE")
    raw_inp = f"PAIN SCALE: {pain_level}/10"
    
    conn.execute("""
        INSERT INTO conversations (patient_id, ward_id, raw_input, rag_output, triage, probability)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (patient_id, ward_id, raw_inp, intent, triage, 100.0))
    conn.commit()
    conv_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    
    socketio.emit('new_request', {
        'conv_id': conv_id, 'patient_id': patient_id, 'patient_name': name,
        'room_number': room, 'ward_id': ward_id, 'raw_input': raw_inp,
        'rag_output': intent, 'probability': 100.0,
        'triage': triage, 'created_at': time.strftime("%Y-%m-%d %H:%M:%S"),
        'source': 'pain_scale', 'pain_level': pain_level
    })
    return jsonify({'status': 'ok', 'triage': triage, 'pain_level': pain_level})

@app.route('/api/override_priority', methods=['POST'])
def api_override_priority():
    """V2: Admin overrides a patient's doctor_rank priority."""
    data       = request.get_json()
    patient_id = int(data.get('patient_id'))
    new_rank   = int(data.get('rank', 5))
    new_rank   = max(1, min(10, new_rank))
    
    conn = get_db()
    conn.execute("UPDATE patients SET doctor_rank=? WHERE patient_id=?", (new_rank, patient_id))
    conn.commit()
    conn.close()
    
    socketio.emit('priority_updated', {'patient_id': patient_id, 'new_rank': new_rank})
    return jsonify({'status': 'ok', 'patient_id': patient_id, 'new_rank': new_rank})

@app.route('/api/audit_log.csv')
def api_audit_log_csv():
    """V2: Export all conversations as CSV for medical records."""
    conn = get_db()
    rows = conn.execute("""
        SELECT c.*, p.name as patient_name, p.room_number, p.ward_id as ward
        FROM conversations c
        LEFT JOIN patients p ON c.patient_id = p.patient_id
        ORDER BY c.created_at DESC
    """).fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Patient', 'Room', 'Ward', 'Input', 'Intent', 'Triage',
                     'Probability', 'Nurse', 'Response Time (s)', 'Feedback', 'Timestamp'])
    for r in rows:
        writer.writerow([
            r['id'], r['patient_name'] or r['patient_id'], r['room_number'],
            r['ward_id'], r['raw_input'], r['rag_output'], r['triage'],
            r['probability'], r['responded_nurse_id'], r['response_time_sec'],
            r['nurse_feedback'], r['created_at']
        ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=biats_audit_log.csv'}
    )

@app.route('/api/nurse_assignments')
def api_nurse_assignments():
    """V2: Get current nurse-to-patient assignments."""
    return jsonify(nurse_assignments)

@app.route('/api/admin_metrics')
def api_admin_metrics():
    conn = get_db()
    active_count = conn.execute("SELECT count(*) FROM conversations WHERE responded_nurse_id IS NULL OR responded_nurse_id = ''").fetchone()[0]
    busiest_ward_row = conn.execute("SELECT ward_id, count(*) as c FROM conversations WHERE responded_nurse_id IS NULL GROUP BY ward_id ORDER BY c DESC LIMIT 1").fetchone()
    busiest_ward = busiest_ward_row['ward_id'] if busiest_ward_row else "None"
    avg_resp = conn.execute("SELECT avg(response_time_sec) FROM conversations WHERE response_time_sec IS NOT NULL").fetchone()[0]
    avg_resp = round(avg_resp, 1) if avg_resp else 0.0
    conn.close()
    return jsonify({
        'active_requests': active_count,
        'busiest_ward': busiest_ward,
        'avg_response_time': avg_resp,
        'emergency_mode': emergency_mode
    })

# ── SOCKETIO EVENTS ────────────────────────────────────────────────

@socketio.on('join_patient')
def on_join_patient(data):
    join_room(f"patient_{data['patient_id']}")

@socketio.on('join_ward')
def on_join_ward(data):
    join_room(f"ward_{data['ward_id']}")

@socketio.on('patient_message')
def handle_patient_message(data):
    try:
        pid       = int(data.get('patient_id'))
        raw_input = data.get('text', '').strip()
        
        conn = get_db()
        row  = conn.execute("SELECT ward_id, name, room_number FROM patients WHERE patient_id=?", (pid,)).fetchone()
        ward_id      = row['ward_id']      if row else 1
        patient_name = row['name']         if row else f"Patient {pid}"
        room_number  = row['room_number']  if row else f"10{pid}"

        results   = safe_chroma_query(raw_input, n=3)
        meta_list = results['metadatas'][0]
        dist_list = results['distances'][0]

        primary_intent = meta_list[0]['intent']
        prob1  = calculate_probability(dist_list[0])
        triage = get_triage(primary_intent)

        sec_intent, prob2, ter_intent, prob3 = None, None, None, None
        if prob1 < 60.0 and len(meta_list) > 1:
            sec_intent = meta_list[1]['intent']
            prob2      = calculate_probability(dist_list[1])
        if prob1 < 50.0 and len(meta_list) > 2:
            ter_intent = meta_list[2]['intent']
            prob3      = calculate_probability(dist_list[2])

        conn.execute("""
            INSERT INTO conversations
            (patient_id, ward_id, raw_input, rag_output, triage, probability, secondary_rag_output, secondary_probability)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (pid, ward_id, raw_input, primary_intent, triage, prob1, sec_intent, prob2))
        conn.commit()
        conv_id    = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        created_at = conn.execute("SELECT created_at FROM conversations WHERE id=?", (conv_id,)).fetchone()['created_at']
        conn.close()

        emit('new_request', {
            'conv_id': conv_id, 'patient_id': pid, 'patient_name': patient_name,
            'room_number': room_number, 'ward_id': ward_id, 'raw_input': raw_input,
            'rag_output': primary_intent,
            'rag_sentence': get_sentence(primary_intent),
            'probability': prob1,
            'secondary_rag_output': sec_intent, 'secondary_probability': prob2,
            'tertiary_rag_output': ter_intent, 'tertiary_probability': prob3,
            'triage': triage, 'created_at': created_at,
            'emergency_mode': emergency_mode
        }, broadcast=True)

        # Task 13: BioBot Fallback (Non-blocking)
        if prob1 < 70.0:
            def run_biobot():
                try:
                    time.sleep(1.5) # Simulate BioBot LLM inference latency
                    biobot_output = f"[BioBot LLM] Clarified request from '{raw_input}'"
                    socketio.emit('biobot_fallback', {
                        'conv_id': conv_id,
                        'patient_id': pid,
                        'biobot_output': biobot_output
                    }, broadcast=True)
                except Exception as e:
                    print("BioBot error:", e)
            
            threading.Thread(target=run_biobot, daemon=True).start()

    except Exception as e:
        import traceback; traceback.print_exc()

@socketio.on('hub_dispatch')
def handle_hub_dispatch(data):
    conv_id = data['conv_id']
    nurse   = data['nurse_id']
    conn = get_db()
    row  = conn.execute("SELECT patient_id FROM conversations WHERE id=?", (conv_id,)).fetchone()
    pid  = row['patient_id'] if row else None
    conn.close()
    
    if pid:
        nurse_assignments[str(pid)] = nurse
    
    emit('request_handled', {'conv_id': conv_id, 'responded_nurse_id': nurse, 'patient_id': pid}, broadcast=True)

@socketio.on('hub_feedback')
def handle_hub_feedback(data):
    conv_id       = data['conv_id']
    status        = data['status']
    correct_intent = data.get('correct_intent')
    nurse_id      = data.get('responded_nurse_id')

    conn = get_db()
    row  = conn.execute("SELECT raw_input, patient_id FROM conversations WHERE id=?", (conv_id,)).fetchone()
    if row:
        if status == 'incorrect' and correct_intent:
            doc_id = f"healed_{int(time.time())}_{random.randint(100,999)}"
            emb = embedding_model.encode([row['raw_input']])
            collection.add(documents=[row['raw_input']], embeddings=emb.tolist(), metadatas=[{'intent': correct_intent}], ids=[doc_id])
            print(f"[HEALING RAG] '{row['raw_input']}' -> {correct_intent}")
        conn.execute("""
            UPDATE conversations
            SET responded_nurse_id=?, nurse_responded_at=CURRENT_TIMESTAMP,
                response_time_sec=CAST((julianday(CURRENT_TIMESTAMP)-julianday(created_at))*86400 AS INTEGER),
                nurse_feedback=?
            WHERE id=?
        """, (nurse_id, status, conv_id))
        conn.commit()
    conn.close()

@socketio.on('nurse_assign')
def handle_nurse_assign(data):
    """V2: Real-time nurse-to-patient assignment."""
    pid   = str(data.get('patient_id'))
    nurse = data.get('nurse_name')
    nurse_assignments[pid] = nurse
    emit('nurse_assignment_updated', {'patient_id': pid, 'nurse': nurse}, broadcast=True)

@socketio.on('admin_ward_alert')
def handle_admin_ward_alert(data):
    ward_id    = data.get('ward_id')
    patient_id = data.get('patient_id')
    message    = data.get('message')
    targets    = data.get('targets', ['ward', 'patient'])
    alert_id   = f"alert_{int(time.time())}_{random.randint(1000, 9999)}"

    conn = get_db()
    row  = conn.execute("SELECT name, room_number FROM patients WHERE patient_id=?", (patient_id,)).fetchone()
    patient_name = row['name']        if row else f"Patient {patient_id}"
    room_number  = row['room_number'] if row else f"10{patient_id}"
    conn.close()

    emit('incoming_admin_alert', {
        'alert_id': alert_id, 'ward_id': ward_id, 'patient_id': patient_id,
        'patient_name': patient_name, 'room_number': room_number,
        'message': message, 'targets': targets,
        'timestamp': time.strftime("%H:%M:%S")
    }, broadcast=True)

@socketio.on('ward_alert_ack')
def handle_ward_alert_ack(data):
    emit('admin_alert_update', {
        'alert_id': data.get('alert_id'),
        'status':   data.get('status'),
        'ward_id':  data.get('ward_id'),
        'nurse_id': data.get('nurse_id')
    }, broadcast=True)

@socketio.on('admin_message')
def handle_admin_message(data):
    room = f"patient_{data['patient_id']}"
    emit('admin_alert', {'message': data['message']}, room=room)

@socketio.on('toggle_emergency')
def toggle_emergency(data):
    global emergency_mode
    emergency_mode = data.get('enabled', False)
    emit('emergency_mode_update', {'enabled': emergency_mode}, broadcast=True)

@socketio.on('reallocate_staff')
def handle_reallocate_staff(data):
    emit('staff_reallocated', {'nurse': data.get('nurse'), 'ward': data.get('to_ward')}, broadcast=True)

# ── FINGERPRINT SYNC (Cross-Bed Roaming) ──────────────────────────

@socketio.on('fp_upload')
def handle_fp_upload(data):
    pid = int(data['patient_id'])
    b64 = data['template_b64']
    
    # NEW: Export the 512-byte Fingerprint Vector to a CSV file for the user to see!
    import base64
    binary_vector = base64.b64decode(b64)
    csv_filename = f"fingerprint_vector_patient_{pid}.csv"
    with open(csv_filename, "w") as f:
        f.write("Byte_Index,Binary_Value,Hex_Value,Integer_Value\n")
        for i, b in enumerate(binary_vector):
            f.write(f"{i},{bin(b)},{hex(b)},{b}\n")
    print(f"\n[FINGERPRINT DATABASE] Captured 512-byte vector for Patient {pid}!")
    print(f"[FINGERPRINT DATABASE] Saved full binary vector to: {csv_filename}\n")
    
    conn = get_fp_db()
    conn.execute("""INSERT INTO fp_templates (patient_id, template_b64, payload_json, updated_at, deleted)
                     VALUES (?, ?, ?, ?, 0)
                     ON CONFLICT(patient_id) DO UPDATE SET
                       template_b64=excluded.template_b64, payload_json=excluded.payload_json,
                       updated_at=excluded.updated_at, deleted=0""",
                 (pid, b64, json.dumps(data), time.time()))
    conn.commit()
    conn.close()
    emit('fp_push', data, broadcast=True, include_self=False)   # instant fan-out to every connected bridge

@socketio.on('fp_delete')
def handle_fp_delete(data):
    pid = int(data['patient_id'])
    conn = get_fp_db()
    conn.execute("UPDATE fp_templates SET deleted=1, updated_at=? WHERE patient_id=?", (time.time(), pid))
    conn.commit()
    conn.close()
    emit('fp_push', {'patient_id': pid, 'deleted': True}, broadcast=True, include_self=False)

@socketio.on('fp_request_full_sync')
def handle_fp_full_sync():
    conn = get_fp_db()
    rows = conn.execute("SELECT payload_json FROM fp_templates WHERE deleted=0").fetchall()
    conn.close()
    for r in rows:
        if r[0]:
            emit('fp_push', json.loads(r[0]))   # unicast back to just this reconnecting bridge

# ── BACKGROUND VITALS THREAD (V2: adds BP, RR, ECG) ──────────────

def vitals_background_thread():
    profiles = ['stable', 'tachycardia', 'bradycardia', 'respiratory_distress']
    mem = {}

    for i in range(1, 41):
        prof = random.choices(profiles, weights=[70, 10, 10, 10])[0]
        if prof == 'stable':
            base_hr, base_spo2, base_sbp, base_rr = random.randint(65,80), random.randint(97,100), random.randint(110,130), random.randint(14,18)
        elif prof == 'tachycardia':
            base_hr, base_spo2, base_sbp, base_rr = random.randint(100,130), random.randint(95,98), random.randint(125,150), random.randint(16,22)
        elif prof == 'bradycardia':
            base_hr, base_spo2, base_sbp, base_rr = random.randint(45,55), random.randint(96,99), random.randint(95,110), random.randint(12,16)
        else:
            base_hr, base_spo2, base_sbp, base_rr = random.randint(85,110), random.randint(85,92), random.randint(130,160), random.randint(20,28)

        mem[i] = {
            'profile': prof, 'phase': random.uniform(0, 2*math.pi),
            'base_hr': base_hr, 'hr': float(base_hr),
            'base_spo2': base_spo2, 'spo2': float(base_spo2),
            'base_sbp': base_sbp, 'sbp': float(base_sbp),
            'base_rr': base_rr, 'rr': float(base_rr),
            'ecg_phase': random.uniform(0, 2*math.pi),
            'hist_spo2': []
        }

    while True:
        payload = {}
        for i in range(1, 41):
            v = mem[i]
            v['phase']     += 0.2
            v['ecg_phase'] += 0.5

            hr_variation = math.sin(v['phase']) * 2.5
            hr_noise     = random.uniform(-1.5, 1.5)
            spo2_noise   = random.uniform(-0.4, 0.4)
            sbp_noise    = random.uniform(-2.0, 2.0)
            rr_noise     = random.uniform(-0.3, 0.3)

            if v['profile'] == 'respiratory_distress' and random.random() < 0.08:
                spo2_noise -= random.uniform(1.0, 3.0)
                rr_noise   += random.uniform(1.0, 3.0)
            if v['profile'] == 'tachycardia' and random.random() < 0.08:
                hr_noise   += random.uniform(3.0, 8.0)
                sbp_noise  += random.uniform(5.0, 15.0)

            v['hr']  = v['hr']  * 0.6 + (v['base_hr']  + hr_variation + hr_noise) * 0.4
            v['spo2']= v['spo2']* 0.8 + (v['base_spo2']+ spo2_noise)              * 0.2
            v['sbp'] = v['sbp'] * 0.7 + (v['base_sbp'] + sbp_noise)               * 0.3
            v['rr']  = v['rr']  * 0.8 + (v['base_rr']  + rr_noise)                * 0.2

            final_hr   = max(30,  min(220, round(v['hr'])))
            final_spo2 = max(50,  min(100, round(v['spo2'])))
            final_sbp  = max(70,  min(200, round(v['sbp'])))
            final_dbp  = max(40,  min(130, round(final_sbp * 0.65 + random.uniform(-3,3))))
            final_rr   = max(8,   min(40,  round(v['rr'])))

            # ECG waveform point: QRS complex simulation
            ecg_val = (
                math.sin(v['ecg_phase']) * 0.3 +              # P wave
                math.exp(-((v['ecg_phase'] % (2*math.pi) - 1.5)**2) / 0.05) * 1.8 +  # QRS
                math.sin(v['ecg_phase'] * 0.5) * 0.15         # T wave
            )
            ecg_val = round(ecg_val + random.uniform(-0.03, 0.03), 3)

            v['hist_spo2'].append(final_spo2)
            if len(v['hist_spo2']) > 5:
                v['hist_spo2'].pop(0)
            deteriorating = False
            if len(v['hist_spo2']) == 5 and v['hist_spo2'][0] - v['hist_spo2'][-1] >= 4:
                deteriorating = True

            payload[str(i)] = {
                'hr': final_hr, 'spo2': final_spo2,
                'sbp': final_sbp, 'dbp': final_dbp,
                'rr': final_rr, 'ecg': ecg_val,
                'profile': v['profile'],
                'deteriorating': deteriorating
            }

        socketio.emit('vitals_update', payload)
        socketio.sleep(2)

# ── STARTUP ────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_path",      type=str, default="embaas/sentence-transformers-clinical-bert")
    parser.add_argument("--db_path",         type=str, default="./chroma_db")
    parser.add_argument("--collection_name", type=str, default="patient_intents_5tier_100")
    parser.add_argument("--port",            default=5055, type=int)
    parser.add_argument("--open_browser",    action="store_true", help="Automatically open browser terminals when server is ready")
    args = parser.parse_args()

    # ── V1-IDENTICAL EMBEDDING SETUP ──────────────────────────────────
    # Use SentenceTransformerEmbeddingFunction exactly like V1 base system.
    # This means chromadb handles all embedding internally via query_texts=[].
    # The model is Bio_ClinicalBERT (sentence-transformers compatible).
    print(f"[BIATS V3] Loading Bio_ClinicalBERT embedding model from {args.model_path}...")
    sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=args.model_path,
        device="cpu"
    )

    print(f"[BIATS V3] Connecting to ChromaDB at {args.db_path}...")
    chroma_client = chromadb.PersistentClient(path=args.db_path)
    try:
        # Attach the embedding function so query_texts works correctly (V1 behaviour)
        collection = chroma_client.get_collection(
            args.collection_name,
            embedding_function=sentence_transformer_ef
        )
    except Exception as e:
        print(f"  Collection not found, creating: {e}")
        collection = chroma_client.get_or_create_collection(
            args.collection_name,
            embedding_function=sentence_transformer_ef
        )
    print(f"[BIATS V3] AI Database loaded. {collection.count():,} vectors indexed.")

    socketio.start_background_task(vitals_background_thread)
    print("[BIATS V3] Background vitals engine started (40 patients).")
    print(f"[BIATS V3] Server starting on port {args.port}...")
    print(f"[BIATS V3] Patient:  http://127.0.0.1:{args.port}/patient/1")
    print(f"[BIATS V3] Ward:     http://127.0.0.1:{args.port}/ward/1")
    print(f"[BIATS V3] Admin:    http://127.0.0.1:{args.port}/admin")
    print(f"[BIATS V3] Audit:    http://127.0.0.1:{args.port}/api/audit_log.csv")

    if args.open_browser:
        def open_tabs():
            import webbrowser, urllib.request
            url = f"http://127.0.0.1:{args.port}/"
            for _ in range(30):
                time.sleep(1)
                try:
                    with urllib.request.urlopen(url, timeout=1) as resp:
                        if resp.status == 200:
                            break
                except Exception:
                    pass
            print(f"[BIATS V3] Launching browser terminals (Ward, Admin, Patient)...")
            webbrowser.open(f"http://127.0.0.1:{args.port}/ward/1")
            time.sleep(0.5)
            webbrowser.open(f"http://127.0.0.1:{args.port}/admin")
            time.sleep(0.5)
            webbrowser.open(f"http://127.0.0.1:{args.port}/patient/1")
            print(f"[BIATS V3] All terminals opened successfully! System is LIVE.")

        threading.Thread(target=open_tabs, daemon=True).start()

    socketio.run(app, host='0.0.0.0', port=args.port, debug=False, use_reloader=False)
