from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from dotenv import load_dotenv
from google import genai

app = Flask(__name__)
CORS(app)

# Load environment variables from .env file
load_dotenv()

client = genai.Client(api_key=os.getenv("GENAI_API_KEY"))

@app.route("/")
def home():
    return jsonify({"message": "Medical Scribe API Running"})

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json
    transcript = data.get("transcript", "")
    medicalHistoryFiles = data.get("medicalHistoryFiles", [])

    # Import lsit from drug_interactions_list.json
    with open(os.path.join(os.path.dirname(__file__), "drug_interactions_list.json")) as f:
        drug_interactions = json.load(f)

    # Summarize the transcript
    summaryResponse = response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents="Summarize the transcript by removing any unnecessary words and details, keep only the important medical information.\n\n---\n\n" + transcript
    )
    summary = summaryResponse.text

    return jsonify({
        "summary": summary,
        "drugInteractions": drug_interactions
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

if __name__ == "__main__":
    app.run(debug=True, port=5000)