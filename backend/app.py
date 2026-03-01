from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from google import genai
from google.genai import types
import whisper

app = Flask(__name__)
CORS(app)  

# Load environment variables from .env file
load_dotenv()

client = genai.Client(api_key=os.getenv("GENAI_API_KEY"))
whisperModel = whisper.load_model("base", device="cpu")

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

@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.json
    transcript = data.get("transcript", "")
    medicalHistoryFiles = data.get("medicalHistoryFiles", [])

#     # TODO! Delete this
#     with open(os.path.join(os.path.dirname(__file__), "sampleTranscript.txt")) as f:
#         transcript = f.read()
#     with open(os.path.join(os.path.dirname(__file__), "Sample Patient Medical History.pdf"), "rb") as f:
#         medicalHistoryFiles.append({
#             "filename": "Sample Patient Medical History.pdf",
#             "data": f.read()
#         })

    # Import list from drug_interactions_list.json
    with open(os.path.join(os.path.dirname(__file__), "drug_interactions_list.json")) as f:
        drug_interactions = json.load(f)
    drug_interactions = str(drug_interactions)

    fileContents = []
    for file in medicalHistoryFiles:
        fileContents.append(
            types.Part.from_bytes(
                data=file["data"],
                mime_type=getMimeType(file["filename"]) if "filename" in file else "application/octet-stream",
            )
        )

    def run_summary():
        r = client.models.generate_content(
            model="gemma-3-27b-it",
            contents="Summarize the transcript by removing any unnecessary words and details, keep only the important medical information, such as the patient's core complaints and issues. Focus on putting it in the form of notes that the doctor would make after the conversation.\n\n---\n\n" + transcript
        )
        return r.text

    def run_thoughts():
        thoughtsContent = [
            "Based on the info the patient provided in the transcript, ignoring the doctor's opinions, state your thoughts on what the patient is experiencing. What do you think are plausible explanations? Is there a clear diagnosis or are there next steps that need to be taken? Should any medications be given? Don't forget to take into account the patient's medical history. Do not worry about critiquing the docor yet. That process will be later, if necessary.\n\n---\n\n" + transcript
        ]
        thoughtsContent.extend(fileContents)
        r = client.models.generate_content(model="gemma-3-27b-it", contents=thoughtsContent)
        return r.text

    def run_critique(thoughts_text):
        critiqueContent = [
            "Critique the doctor's response to the patient. This doesn't mean questioning their approach, but rather their conclusions. Did they miss anything important? Did they make any mistakes? Did they fail to account for other plausible explanations or diagnoses? Did they prescribe the correct medication if necessary? Or did they fail to prescribe necessary medication or did they prescribe the wrong medication? Is anything they said just incorrect, or maybe only partially incorrect> Don't forget to take into account the patient's medical history. Be as detailed as possible in your critique, and make sure to specifically list every single thing the doctor missed, and what they shoud have done instead. Use the following analysis of what the patient is experiencing to inform your critique. Most importantly, focus on what the doctor said that was factually wrong instead of how their processes or questions could have been better. Attached is the transcript, the patient's medical history, and a list of drug interactions to help you with your critique.\n\n---\n\nAnalysis (thoughts on the patient):\n" + thoughts_text + "\n\n---\n\nTranscript:\n" + transcript + "\n\n---\n\nDrug Interactions:\n" + drug_interactions
        ]
        critiqueContent.extend(fileContents)
        r = client.models.generate_content(model="gemma-3-27b-it", contents=critiqueContent)
        return r.text

    def run_flags(critique_text):
        flagsContent = [
            "List all important flags in a formatted, list manner with priorities (high, medium, low) based on how important they are for the doctor to address immediately. Use the format: [(priority, flag details), (priority, flag details)]. Flag details is what will be displayed on the Ui for the doctor to read, so keep them short but detailed. Priority should only be just low, medium, or high. For example, if the doctor missed a critical diagnosis that could be fatal if not treated immediately, that would be a high priority flag. If the doctor missed a less critical diagnosis that still needs to be addressed but is not immediately life-threatening, that would be a medium priority flag. If the doctor made a minor mistake that does not have a significant impact on the patient's health, that would be a low priority flag. Remember, output it in the form of an array, and do not say anything else, not even a \"here is the list of flags:\" or a \"```json\". Base your flags on the following critique of the doctor. Attached is the transcript, the patient's medical history, and a list of drug interactions.\n\n---\n\nCritique:\n" + critique_text + "\n\n---\n\nTranscript:\n" + transcript + "\n\n---\n\nDrug Interactions:\n" + drug_interactions
        ]
        flagsContent.extend(fileContents)
        r = client.models.generate_content(model="gemma-3-27b-it", contents=flagsContent)
        rText = r.text
        # Remove ```json from start of rText if it exists, and ``` from end of rText if it exists
        if rText.startswith("```json"):
            rText = rText[len("```json"):]
        if rText.endswith("```"):
            rText = rText[:-len("```")]
        rText = rText.strip()
        return rText

    # Summary runs in parallel; thoughts -> critique -> flags run in sequence (each needs the previous)
    summary = None
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_summary = executor.submit(run_summary)
        thoughts = run_thoughts()
        critique = run_critique(thoughts)
        flagged = run_flags(critique)
        summary = future_summary.result()

    return jsonify({
        "summary": summary,
        "thoughts": thoughts,
        "critique": critique,
        "flagged": flagged
    })

@app.before_request
def handle_options():
    if request.method == "OPTIONS":
        return '', 200

@app.route("/api/transcribe", methods=["POST"])
def transcribe_audio():
    audio_file = request.files.get("audio")
    if not audio_file or audio_file.filename == "":
        return jsonify({"error": "No audio file provided"}), 400

    # Save the uploaded audio file to a temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        audio_file.save(temp_audio.name)
        temp_audio_path = temp_audio.name

    try:
        result = whisperModel.transcribe(temp_audio_path)
        transcript = result["text"]
        return jsonify({"transcript": transcript})
    except (FileNotFoundError, OSError) as e:
        err_str = str(e)
        if "WinError 2" in err_str or "cannot find the file" in err_str.lower():
            return jsonify({
                "error": "ffmpeg is required for audio transcription but was not found. Install ffmpeg and add it to your PATH (e.g. winget install ffmpeg, choco install ffmpeg, or scoop install ffmpeg)."
            }), 500
        return jsonify({"error": err_str}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(temp_audio_path):
            try:
                os.unlink(temp_audio_path)
            except OSError:
                pass

if __name__ == "__main__":
    app.run(debug=True, port=5000)