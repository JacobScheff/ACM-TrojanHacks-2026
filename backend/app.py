from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

app = Flask(__name__)
CORS(app)

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

    # TODO! Delete this
    with open(os.path.join(os.path.dirname(__file__), "sampleTranscript.txt")) as f:
        transcript = f.read()
    with open(os.path.join(os.path.dirname(__file__), "Sample Patient Medical History.pdf"), "rb") as f:
        medicalHistoryFiles.append({
            "filename": "Sample Patient Medical History.pdf",
            "data": f.read()
        })

    # Import lsit from drug_interactions_list.json
    with open(os.path.join(os.path.dirname(__file__), "drug_interactions_list.json")) as f:
        drug_interactions = json.load(f)
    drug_interactions = str(drug_interactions)

    # Summarize the transcript
    summaryResponse = client.models.generate_content(
        model="gemini-3-flash-preview",
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
        model="gemini-3-flash-preview",
        contents=thoughtsContent
    )
    thoughts = thoughtsResponse.text

    # Critique the doctor
    critiqueContent = [
        "Critique the doctor's approach to the patient's case. What did they do well? What could they have done better? Be brutally honest and critical. Don't worry about being nice, just be accurate and truthful. If you think the doctor made a mistake, say what it is and how it could have been done better.\n\n---\n\n" + transcript
    ]
    critiqueContent.extend(fileContents)
    # critiqueContent.append(
    
    return jsonify({
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

if __name__ == "__main__":
    app.run(debug=True, port=5000)