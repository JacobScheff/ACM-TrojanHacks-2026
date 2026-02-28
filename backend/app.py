from flask import Flask, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return jsonify({"message": "Medical Scribe API Running"})

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