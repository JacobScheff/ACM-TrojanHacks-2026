import { useState, useRef } from "react";


export default function App() {
  const [activeTab, setActiveTab] = useState("subjective");
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const [transcript, setTranscript] = useState("");


  const [analysis, setAnalysis] = useState(null);
  const [activeAnalysisTab, setActiveAnalysisTab] = useState("summary");
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mediaRecorder = new MediaRecorder(stream);

    mediaRecorderRef.current = mediaRecorder;
    audioChunksRef.current = [];

    mediaRecorder.ondataavailable = (event) => {
      audioChunksRef.current.push(event.data);
    };

    mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(audioChunksRef.current, {
        type: "audio/webm"
      });

      const formData = new FormData();
      formData.append("audio", audioBlob, "recording.webm");

      try {
        const res = await fetch("/api/transcribe", {
          method: "POST",
          body: formData,
        });

        const data = await res.json();
        console.log(data);
        setTranscript(data.transcript);

      } catch (err) {
        console.error("FETCH ERROR:", err);
      }
    };

    mediaRecorder.start();
    setIsRecording(true);
  };

  const stopRecording = () => {
    mediaRecorderRef.current.stop();
    setIsRecording(false);
  };

  const handleRecordClick = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  const handleAnalyze = async () => {
    if (!transcript) return;

    setLoadingAnalysis(true);
    setAnalysis(null);

    try {
      const res = await fetch("http://127.0.0.1:5000/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          transcript: transcript,
          medicalHistoryFiles: []
        }),
      });

      const data = await res.json();
      setAnalysis(data);

    } catch (err) {
      console.error("Analyze error:", err);
    }

    setLoadingAnalysis(false);
  };

  return (
    <div className="min-h-screen bg-gray-100">

      {/* Top Navbar */}
      <div className="bg-slate-800 text-white px-6 py-4 flex justify-between">
        <div className="font-bold text-lg">MedScribe AI Verifier</div>
        <div className="space-x-6">
          <span>Live Encounter</span>
          <span>Patient Charts</span>
          <span>Verified Logs</span>
          <span>Settings</span>
        </div>
      </div>

      {/* Main Content */}
      <div className="p-6 grid grid-cols-3 gap-6">

        {/* LEFT PANEL */}
        <div className="bg-white rounded-xl shadow p-4">
          
          {/* Audio Recording & Transcript */}
          <div className="flex flex-col items-center justify-center space-y-4">
            <button
              onClick={handleRecordClick}
              className={`w-16 h-16 rounded-full flex items-center justify-center transition-all duration-300 ${
                isRecording ? "bg-red-600" : "bg-gray-300"
              }`}
            >
              {isRecording ? (
                <div className="w-6 h-6 bg-white"></div>  // square
              ) : (
                <div className="w-6 h-6 bg-white rounded-full"></div> // circle
              )}
            </button>

            <span className="text-sm">
              {isRecording ? "Recording..." : "Click to Record"}
            </span>

          </div>
          
          <div className="mt-6 border-t pt-4">
            
            <h2 className="font-semibold text-lg mb-4">Transcript</h2>
              <div className="space-y-3 text-sm">
                <div className="space-y-3 text-sm">
                  {transcript ? (
                    <div>{transcript}</div>
                  ) : (
                    <div className="text-gray-400">
                      Transcript will appear here...
                    </div>
                  )}
                </div>
              </div>
          </div>
          
          <div className="mt-4">
            <button
              onClick={handleAnalyze}
              disabled={!transcript || loadingAnalysis}
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:bg-gray-400"
            >
              {loadingAnalysis ? "Analyzing..." : "Analyze Transcript"}
            </button>
          </div>
          {/* <div className="mt-6 border-t pt-4">
            <h3 className="font-medium mb-2">Audio</h3>
            <div className="h-16 bg-gray-200 rounded flex items-center justify-center">
              🎙 Audio Waveform Placeholder
            </div>
          </div> */}


        </div>

        {/* CENTER PANEL */}
        
        <div className="bg-white rounded-xl shadow p-4">
          <h2 className="font-semibold text-lg mb-4">
            AI Analysis
          </h2>

          {loadingAnalysis && (
            <p className="text-gray-500">Running AI analysis...</p>
          )}

          {!loadingAnalysis && analysis && (
            <>
              {/* Tabs */}
              <div className="flex space-x-6 border-b mb-4">
                {["summary", "thoughts", "critique", "flagged"].map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveAnalysisTab(tab)}
                    className={`pb-2 capitalize ${
                      activeAnalysisTab === tab
                        ? "border-b-2 border-blue-600 text-blue-600 font-medium"
                        : "text-gray-500"
                    }`}
                  >
                    {tab === "flagged" ? "Flags" :
                    tab === "thoughts" ? "Clinical Thoughts" :
                    tab.charAt(0).toUpperCase() + tab.slice(1)}
                  </button>
                ))}
              </div>

              {/* Content */}
              <div className="text-sm whitespace-pre-wrap max-h-[500px] overflow-y-auto">
                {analysis[activeAnalysisTab]}
              </div>
            </>
          )}

          {!loadingAnalysis && !analysis && (
            <p className="text-gray-400">
              Analysis will appear here after clicking "Analyze Transcript".
            </p>
          )}
        </div>
                


         

        {/* RIGHT PANEL */}
        <div className="bg-white rounded-xl shadow p-4">
          <h2 className="font-semibold text-lg mb-4">
            Verifier & Critical Checks
          </h2>

          <div className="space-y-4 text-sm">

            <div className="bg-red-100 border-l-4 border-red-500 p-3 rounded">
              <strong>Low Confidence</strong><br />
              Missing objective vitals.
            </div>

            <div className="bg-yellow-100 border-l-4 border-yellow-500 p-3 rounded">
              <strong>Clinical Consistency</strong><br />
              Chest pain not fully evaluated.
            </div>

            <div className="bg-gray-100 p-3 rounded">
              <strong>EHR Integration</strong><br />
              Status: Pending Signature
            </div>

          </div>
        </div>

      </div>
    </div>
  );
}