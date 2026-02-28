from flask import Flask, request, jsonify
from flask_cors import CORS
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
        model="gemma-3-27b-it",
        contents="Summarize the transcript by removing any unnecessary words and details, keep only the important medical information, such as the patient's core complaints and issues. Focus on putting it in the form of notes that the doctor would make after the conversation.\n\n---\n\n" + transcript
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
        "Critique the doctor's response to the patient. This doesn't mean questioning their approach, but rather their conclusions. Did they miss anything important? Did they make any mistakes? Did they fail to account for other plausible explanations or diagnoses? Did they prescribe the correct medication if necessary? Or did they fail to prescribe necessary medication or did they prescribe the wrong medication? Is anything they said just incorrect, or maybe only partially incorrect> Don't forget to take into account the patient's medical history. Be as detailed as possible in your critique, and make sure to specifically list every single thing the doctor missed, and what they shoud have done instead. Attached is the transcript, the patient's medical history, and a list of drug interactions to help you with your critique.\n\n---\n\n" + transcript + "\n\n---\n\nDrug Interactions:\n" + drug_interactions
    ]
    critiqueContent.extend(fileContents)
    critiqueResponse = client.models.generate_content(
        model="gemma-3-27b-it",
        contents=critiqueContent
    )
    critique = critiqueResponse.text

    # List all important flags in a formatted, list manner with priorities (high, medium, low) based on how important they are for the doctor to address immediately. For example, if the doctor missed a critical diagnosis that could be fatal if not treated immediately, that would be a high priority flag. If the doctor missed a less critical diagnosis that still needs to be addressed but is not immediately life-threatening, that would be a medium priority flag. If the doctor made a minor mistake that does not have a significant impact on the patient's health, that would be a low priority flag.
    flagsContent = [
        "List all important flags in a formatted, list manner with priorities (high, medium, low) based on how important they are for the doctor to address immediately. Use the format: [(priority, flag details), (priority, flag details)]. Flag details is what will be displayed on the Ui for the doctor to read, so keep them short but detailed. Priority should only be just low, medium, or high. For example, if the doctor missed a critical diagnosis that could be fatal if not treated immediately, that would be a high priority flag. If the doctor missed a less critical diagnosis that still needs to be addressed but is not immediately life-threatening, that would be a medium priority flag. If the doctor made a minor mistake that does not have a significant impact on the patient's health, that would be a low priority flag. Remember, output it in the form of an array, and do not say anything else, not even a \"here is the list of flags:\" or a \"```json\". Attached is the transcript, the patient's medical history, and a list of drug interactions to help you with your analysis.\n\n---\n\n" + transcript + "\n\n---\n\nDrug Interactions:\n" + drug_interactions
    ]
    flagsContent.extend(fileContents)
    flagsResponse = client.models.generate_content(
        model="gemma-3-27b-it",
        contents=flagsContent
    )
    flagged = flagsResponse.text
    
    return jsonify({
        "summary": summary,
        "thoughts": thoughts,
        "critique": critique,
        "flagged": flagged
    })

@app.route("/generate-note", methods=["POST"])
def generate_note():
    data = request.json
    transcript = data.get("transcript", "")
# @app.route("/generate-note", methods=["POST"])
# def generate_note():
#     data = request.json
#     transcript = data.get("transcript", "")

#     return jsonify({
#         "soap_note": f"S: {transcript}\nO: ...\nA: ...\nP: ...",
#         "confidence": 0.85,
#         "warnings": ["Missing vitals"]
#     })

@app.route("/transcribe", methods=["POST"])
def transcribe_audio():
    audio_file = request.files["audio"]

    # save the audio file temporarily
    audio_file.save("temp_audio.webm")

    # TODO: process the audio file and generate transcript using a speech-to-text model
    transcript = "Patient reports chest pain for 2 days."

    return jsonify({
        "transcript": transcript
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)