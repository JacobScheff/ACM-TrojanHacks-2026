from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

from uuid import uuid4
from datetime import datetime
import re
import json
from typing import Tuple, Optional

app = Flask(__name__)
CORS(app)

CHAT_SESSIONS = {}  # key: session_id -> list of {"role":"doctor"|"ai"|"system","text":...}
SESSION_TRANSCRIPT = {}   # session_id -> {"summary": ..., "thoughts": ...}

# Load environment variables from .env file
load_dotenv()

client = genai.Client(api_key=os.getenv("GENAI_API_KEY"))

@app.route("/")
def home():
    return jsonify({"message": "Medical Scribe API Running"})

def getMimeType(filename):
    ext = filename.split(".")[-1].lower()
    if ext == "pdf":
        return "application/pdf"
    elif ext in ["jpg", "jpeg"]:
        return "image/jpeg"
    elif ext == "png":
        return "image/png"
    else:
        return "application/octet-stream"
    


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json
    transcript = data.get("transcript", "")
    medicalHistoryFiles = data.get("medicalHistoryFiles", [])

    sample_path = os.path.join(os.path.dirname(__file__), "sampleTranscript.txt")
    try:
        with open(sample_path, "r", encoding="utf-8") as f:
            transcript = f.read()
    except UnicodeDecodeError:
        # 如果真的不是 utf-8，再試試 latin-1 或 cp1252
        with open(sample_path, "r", encoding="cp1252", errors="replace") as f:
            transcript = f.read()

    # Import lsit from drug_interactions_list.json
    with open(os.path.join(os.path.dirname(__file__), "drug_interactions_list.json")) as f:
        drug_interactions = json.load(f)
    drug_interactions = str(drug_interactions)

    # Summarize the transcript
    summaryResponse = client.models.generate_content(
        model="gemma-3-27b-it",
        contents="Summarize the transcript by removing any unnecessary words and details, keep only the important medical information, such as the patient's core complains and issues.\n\n---\n\n" + transcript
    )
    summary = summaryResponse.text

    fileContents = []
    for file in medicalHistoryFiles:
        fileContents.append(
            types.Part.from_bytes(
                data= file["data"],
                mime_type=getMimeType(file["filename"]) if "filename" in file else "application/octet-stream",
            )
        )

    # Create its own thoughts
    thoughtsContent = [
        "Based on the info the patient provided in the transcript, ignoring the doctor's opinions, state your thoughts on what the patient is experiencing. What do you think are plausible explanations? Is there a clear diagnosis or are there next steps that need to be taken? Should any medications be given? Don't forget to take into account the patient's medical history. Do not worry about critiquing the docor yet. That process will be later, if necessary.\n\n---\n\n" + transcript
    ]
    thoughtsContent.extend(fileContents)
    
    thoughtsResponse = client.models.generate_content(
        model="gemma-3-27b-it",
        contents=thoughtsContent
    )
    thoughts = thoughtsResponse.text

    # Critique the doctor
    critiqueContent = [
        "Critique the doctor's approach to the patient's case. What did they do well? What could they have done better? Be brutally honest and critical. Don't worry about being nice, just be accurate and truthful. If you think the doctor made a mistake, say what it is and how it could have been done better.\n\n---\n\n" + transcript
    ]
    critiqueContent.extend(fileContents)
    # critiqueContent.append(
    
    
    session_id = data.get("session_id")
    if not session_id:
        session_id = str(uuid4())
    if session_id not in CHAT_SESSIONS:
        CHAT_SESSIONS[session_id] = []

    SESSION_TRANSCRIPT[session_id] = {
        "summary": summary,
        "thoughts": thoughts,
        "timestamp": datetime.utcnow().isoformat()
    }

    
    return jsonify({
        "session_id": session_id,
        "summary": summary,
        "thoughts": thoughts,
    })

# fetch('http://127.0.0.1:5000/analyze', {
#   method: 'POST',
#   headers: { 'Content-Type': 'application/json' },
#   body: JSON.stringify({ transcript: 'Hello! This is a sentence. This is another word. I am an unncessessary sentence!' })
# })
# .then(response => response.json())
# .then(data => console.log(data));

@app.route("/generate-note", methods=["POST"])
def generate_note():
    data = request.json
    transcript = data.get("transcript", "")

    # ⚠️ MVP mock SOAP note generator
    soap_note = f"""
    S: Patient reports {transcript}

    O: No objective data provided.

    A: Possible condition based on transcript.

    P: Further evaluation recommended.
    """

    return jsonify({
        "soap_note": soap_note,
        "confidence": 0.72,
        "warnings": [
            "No vitals documented",
            "Medication list not verified"
        ]
    })
    
    
    
def sanitize_and_parse_json(raw_text: str) -> Tuple[Optional[dict], Optional[str]]:
    """
    Try to turn a raw model output into a Python dict.
    Returns (parsed_dict, error_message). If parsed_dict is not None => success.
    Tries multiple sanitization steps:
      1) strip code fences (```json ... ``` or ``` ... ```)
      2) remove leading/trailing markdown (```), and any leading language tags
      3) trim whitespace, BOM
      4) if still failing, extract the first {...} block
    """
    if raw_text is None:
        return None, "raw_text is None"

    s = raw_text.strip()

    # Remove common triple-backtick fences, with optional language after opening fence
    # Examples: ```json\n{...}\n```  OR ```\n{...}\n```
    s = re.sub(r"^```(?:[\w+-]*)\s*", "", s, flags=re.IGNORECASE)   # remove opening fence
    s = re.sub(r"\s*```$", "", s, flags=re.IGNORECASE)              # remove closing fence

    # Some models include fenced blocks with indentation / leading newlines - strip again
    s = s.strip()

    # Remove any leading "json" markers like "json\n{...}"
    s = re.sub(r"^json\s*", "", s, flags=re.IGNORECASE).strip()

    # Remove common quoting artifacts (e.g. surrounding single or double tick blocks)
    if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
        # only strip if both ends match and content likely JSON
        inner = s[1:-1].strip()
        if inner.startswith("{") or inner.startswith("["):
            s = inner

    # Try direct JSON load first
    try:
        parsed = json.loads(s)
        return parsed, None
    except Exception as e:
        # fallback: try to find first { ... } or [ ... ] block and parse that
        m = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", s)
        if m:
            candidate = m.group(1)
            try:
                parsed = json.loads(candidate)
                return parsed, None
            except Exception as e2:
                return None, f"json.loads failed on candidate block: {e2}; original error: {e}"
        else:
            return None, f"json.loads failed and no JSON-like block found. original error: {e}"
        
            
@app.route("/chat", methods=["POST"])
def chat():
    body = request.get_json() or {}
    session_id = body.get("session_id")
    doctor_msg = body.get("doctor_message", "").strip()
    patient_id = body.get("patient_id")
    patient_record = body.get("patient_record")  # optional full JSON

    # get or create session
    if not session_id:
        session_id = str(uuid4())
        CHAT_SESSIONS[session_id] = []
    if session_id not in CHAT_SESSIONS:
        CHAT_SESSIONS[session_id] = []

    # load patient record if provided id and not full record
    if patient_id and not patient_record:
        try:
            from .epic_dummy import load_patient_record
            patient_record = load_patient_record(patient_id)
        except Exception:
            patient_record = None

    # append doctor's message to history
    CHAT_SESSIONS[session_id].append({"role": "doctor", "text": doctor_msg, "time": datetime.utcnow().isoformat()})

    # Build system instruction + history for model
    system_prompt = (
        "You are a concise clinical assistant. Use the patient history and prior chat messages. "
        "Answer the doctor's question directly. Return JSON EXACTLY matching the schema provided. "
        "If you suggest medications or orders, include rationale and confidence_percent."
    )

    schema = {
        "answer": "string concise answer to doctor's question",
        "summary": ["... up to 3 bullets"],
        "differentials": [{"name":"", "confidence_percent":0, "rationale":""}],
        "recommended_actions": [{"action_type":"note|order|test|refer","details":""}],
        "recommended_prescriptions": [{"drug":"", "dose":"", "rationale":""}],
        "flags": [{"type":"drug-interaction|allergy|missing-data|implausible-dx","severity":"low|moderate|high","details":""}]
    }

    # Build the contents list: system, patient_record, analysis summary/thoughts (if any), prior messages (last N), current doctor message
    contents = []
    contents.append(f"SYSTEM: {system_prompt}\nSCHEMA: {json.dumps(schema)}")
    if patient_record:
        contents.append(f"PATIENT_RECORD: {json.dumps(patient_record)}")

    # --- NEW: inject analysis summary/thoughts from SESSION_TRANSCRIPT if available ---
    transcript_struct = None
    if session_id and session_id in SESSION_TRANSCRIPT:
        transcript_struct = SESSION_TRANSCRIPT[session_id]
    # (optional) fallback: if patient_id keyed storage used elsewhere, you could check that too

    if transcript_struct:
        # take summary and thoughts (if exist); truncate to avoid oversized prompts
        def _safe_trunc(s, limit=2000):
            if not s:
                return ""
            s = s if isinstance(s, str) else json.dumps(s)
            return s if len(s) <= limit else s[:limit] + " ...[truncated]"

        summary_text = transcript_struct.get("summary")
        thoughts_text = transcript_struct.get("thoughts")

        # If summary is a structured object (e.g., list), stringify it
        if isinstance(summary_text, (list, dict)):
            summary_text = json.dumps(summary_text)

        # append to contents
        if summary_text:
            contents.append(f"ANALYSIS_SUMMARY: {_safe_trunc(summary_text)}")
        if thoughts_text:
            contents.append(f"ANALYSIS_THOUGHTS: {_safe_trunc(thoughts_text)}")
    # --- END NEW ---

    # include last up to 8 chat messages for context
    history_msgs = CHAT_SESSIONS[session_id][-8:]
    history_text = "\n".join([f"{m['role'].upper()}: {m['text']}" for m in history_msgs])
    if history_text:
        contents.append(f"CHAT_HISTORY:\n{history_text}")
    contents.append(f"DOCTOR_QUESTION: {doctor_msg}")

    # Call Gemini (gemma-3-27b-it)
    try:
        resp = client.models.generate_content(
            model="gemma-3-27b-it",
            contents=contents
        )
        # raw = getattr(resp, "text", None) or str(resp)
        # # expect model to return JSON only. Try parse
        # parsed = json.loads(raw)
        
        # after you get resp and raw:
        raw = getattr(resp, "text", None) or str(resp)

        parsed, parse_err = sanitize_and_parse_json(raw)
        if parsed is None:
            # helpful debug response, don't crash
            parsed = {
                "error": "model_error_or_parse_fail",
                "message": parse_err,
                "raw": raw
            }
        
    except Exception as e:
        # on parse fail, return raw text for debugging
        parsed = {"error": "model_error_or_parse_fail", "message": str(e), "raw": raw}

    # save AI reply into session history
    try:
        ai_text = parsed.get("answer") if isinstance(parsed, dict) and parsed.get("answer") else (raw if isinstance(raw, str) else str(raw))
    except Exception:
        ai_text = raw if isinstance(raw, str) else str(raw)
    CHAT_SESSIONS[session_id].append({"role": "ai", "text": ai_text, "time": datetime.utcnow().isoformat()})

    # run drug-interaction checks if model recommended prescriptions
    try:
        rec_rx = parsed.get("recommended_prescriptions", []) if isinstance(parsed, dict) else []
        # patient meds
        patient_meds = patient_record.get("medications", []) if patient_record else []
        from .drugcheck import check_drug_interactions
        extra_flags = []
        for rx in rec_rx:
            drug = rx.get("drug") if isinstance(rx, dict) else None
            if drug:
                extra_flags.extend(check_drug_interactions(patient_meds, drug))
        if extra_flags:
            parsed_flags = parsed.get("flags", []) if isinstance(parsed, dict) else []
            parsed["flags"] = parsed_flags + extra_flags
    except Exception:
        pass

    return jsonify({"session_id": session_id, "response": parsed})


if __name__ == "__main__":
    app.run(debug=True, port=5000)