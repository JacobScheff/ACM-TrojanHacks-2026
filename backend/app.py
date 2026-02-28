from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from google import genai

app = Flask(__name__)
CORS(app)

client = genai.Client()

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