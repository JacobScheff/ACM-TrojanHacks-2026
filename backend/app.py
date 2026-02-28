from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  

@app.route("/")
def home():
    return jsonify({"message": "Medical Scribe API Running"})

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