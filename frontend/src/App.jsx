import { useState, useRef, useEffect } from "react";

/** Renders basic markdown (headers, bold, lists, code) without external deps */
function MarkdownBlock({ text }) {
  if (!text || typeof text !== "string") return null;
  const lines = text.split("\n");
  const out = [];
  let i = 0;
  let listItems = [];
  let listOrdered = null; // true = ol, false = ul
  const flushList = () => {
    if (listItems.length === 0) return;
    const Tag = listOrdered ? "ol" : "ul";
    out.push(
      <Tag key={out.length} className={listOrdered ? "list-decimal pl-6 my-2" : "list-disc pl-6 my-2"}>
        {listItems.map((item, j) => (
          <li key={j}>{item}</li>
        ))}
      </Tag>
    );
    listItems = [];
    listOrdered = null;
  };
  while (i < lines.length) {
    const line = lines[i];
    const ulMatch = line.match(/^\s*[-*]\s+(.*)$/);
    const olMatch = line.match(/^\s*\d+\.\s+(.*)$/);
    if (line.startsWith("### ")) {
      flushList();
      out.push(<h3 key={out.length} className="text-sm font-semibold mt-2 mb-1">{line.slice(4)}</h3>);
    } else if (line.startsWith("## ")) {
      flushList();
      out.push(<h2 key={out.length} className="text-base font-semibold mt-3 mb-1">{line.slice(3)}</h2>);
    } else if (line.startsWith("# ")) {
      flushList();
      out.push(<h1 key={out.length} className="text-lg font-semibold mt-3 mb-1">{line.slice(2)}</h1>);
    } else if (ulMatch) {
      if (listOrdered === true) flushList();
      listOrdered = false;
      listItems.push(parseInline(ulMatch[1]));
    } else if (olMatch) {
      if (listOrdered === false) flushList();
      listOrdered = true;
      listItems.push(parseInline(olMatch[1]));
    } else if (line.startsWith("```")) {
      flushList();
      const block = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) {
        block.push(lines[i]);
        i++;
      }
      out.push(
        <pre key={out.length} className="bg-gray-100 p-3 rounded-lg overflow-x-auto my-2 text-xs">
          <code>{block.join("\n")}</code>
        </pre>
      );
    } else {
      flushList();
      if (line.trim()) out.push(<p key={out.length} className="my-2">{parseInline(line)}</p>);
    }
    i++;
  }
  flushList();
  return <div className="[&_strong]:font-semibold [&_code]:bg-gray-100 [&_code]:px-1 [&_code]:rounded">{out}</div>;
}

function parseInline(str) {
  const parts = [];
  let rest = str;
  let key = 0;
  while (rest.length) {
    const bold = rest.match(/\*\*(.+?)\*\*/);
    const code = rest.match(/`([^`]+)`/);
    let match = null;
    let type = null;
    let index = rest.length;
    if (bold && bold.index < index) { match = bold; type = "bold"; index = bold.index; }
    if (code && code.index < index) { match = code; type = "code"; index = code.index; }
    if (index > 0) {
      parts.push(<span key={key++}>{rest.slice(0, index)}</span>);
    }
    if (match && type === "bold") {
      parts.push(<strong key={key++}>{match[1]}</strong>);
      rest = rest.slice(index + match[0].length);
    } else if (match && type === "code") {
      parts.push(<code key={key++} className="bg-gray-100 px-1 rounded">{match[1]}</code>);
      rest = rest.slice(index + match[0].length);
    } else {
      rest = rest.slice(index);
    }
  }
  return parts.length === 1 ? parts[0] : <>{parts}</>;
}


export default function App() {
  const [activeTab, setActiveTab] = useState("subjective");
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const [transcript, setTranscript] = useState("");


  const [analysis, setAnalysis] = useState(null);
  const [activeAnalysisTab, setActiveAnalysisTab] = useState("summary");
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [medicalHistoryFiles, setMedicalHistoryFiles] = useState([]);
  const [dismissedFlagIndices, setDismissedFlagIndices] = useState(new Set());
  const [exitingFlagIndices, setExitingFlagIndices] = useState(new Set());
  const [chatOpen, setChatOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);

  /** Parse backend flagged string (JSON or Python-style tuples) into { priority, details }[] */
  const parseFlagged = (flagged) => {
    if (!flagged || typeof flagged !== "string") return [];
    const trimmed = flagged.trim();
    if (!trimmed) return [];

    try {
      const parsed = JSON.parse(trimmed);
      if (!Array.isArray(parsed)) return [];
      return parsed.map((item) => {
        if (Array.isArray(item) && item.length >= 2) {
          return { priority: String(item[0]).toLowerCase(), details: String(item[1]) };
        }
        if (item && typeof item === "object" && (item.priority || item.details)) {
          return {
            priority: String(item.priority || "medium").toLowerCase(),
            details: String(item.details || ""),
          };
        }
        return null;
      }).filter(Boolean);
    } catch {
      // Fallback: Python-style [("high", "detail"), ("medium", "detail")]
      const tuples = trimmed.match(/\(\s*["'](high|medium|low)["']\s*,\s*["']((?:[^"'\\]|\\.)*)["']\s*\)/gi);
      if (tuples) {
        return tuples.map((t) => {
          const m = t.match(/\(\s*["'](high|medium|low)["']\s*,\s*["']((?:[^"'\\]|\\.)*)["']\s*\)/i);
          return m ? { priority: m[1].toLowerCase(), details: m[2].replace(/\\./g, (c) => c === '\\"' ? '"' : c) } : null;
        }).filter(Boolean);
      }
      return [];
    }
  };

  const flaggedList = analysis?.flagged ? parseFlagged(analysis.flagged) : [];

  useEffect(() => {
    setDismissedFlagIndices(new Set());
    setExitingFlagIndices(new Set());
  }, [analysis]);

  const dismissFlag = (index) => {
    setExitingFlagIndices((prev) => new Set(prev).add(index));
  };

  const handleFlagTransitionEnd = (index) => {
    setExitingFlagIndices((prev) => {
      if (!prev.has(index)) return prev;
      const next = new Set(prev);
      next.delete(index);
      return next;
    });
    setDismissedFlagIndices((prev) => (prev.has(index) ? prev : new Set(prev).add(index)));
  };

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

  const fileInputRef = useRef(null);

  const readFileAsBase64 = (file) =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = reader.result.split(",")[1] || reader.result;
        resolve({ filename: file.name, data: base64 });
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });

  const handleAnalyze = async () => {
    if (!transcript) return;

    setLoadingAnalysis(true);
    setAnalysis(null);

    try {
      const filesPayload = await Promise.all(
        medicalHistoryFiles.map(readFileAsBase64)
      );

      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          transcript,
          medicalHistoryFiles: filesPayload,
        }),
      });

      const data = await res.json();
      setAnalysis(data);
    } catch (err) {
      console.error("Analyze error:", err);
    }

    setLoadingAnalysis(false);
  };

  const handleFileChange = (e) => {
    const chosen = Array.from(e.target.files || []);
    setMedicalHistoryFiles((prev) => [...prev, ...chosen]);
    e.target.value = "";
  };

  const removeMedicalFile = (index) => {
    setMedicalHistoryFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const sendChatMessage = async () => {
    const msg = chatInput.trim();
    if (!msg || chatLoading) return;

    setChatInput("");
    setChatMessages((prev) => [...prev, { role: "doctor", text: msg }]);
    setChatLoading(true);

    try {
      const history = chatMessages.flatMap((m) =>
        m.role === "doctor" ? [`Doctor: ${m.text}`] : [`AI: ${m.text}`]
      );

      const patientDataPayload = await Promise.all(
        medicalHistoryFiles.map(readFileAsBase64)
      );

      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          doctor_message: msg,
          transcript: transcript || "",
          thoughts: analysis?.thoughts || "",
          critiques: analysis?.critique || "",
          patient_data: patientDataPayload,
          history,
        }),
      });

      const data = await res.json();
      const answer =
        typeof data.response === "string"
          ? data.response
          : data.response?.answer ?? (data.response?.error ? `Error: ${data.response.message ?? data.response.error}` : String(data.response ?? "No response"));

      setChatMessages((prev) => [...prev, { role: "ai", text: answer }]);
    } catch (err) {
      setChatMessages((prev) => [
        ...prev,
        { role: "ai", text: `Error: ${err.message || "Request failed"}` },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const chatEndRef = useRef(null);
  useEffect(() => {
    if (chatOpen && chatEndRef.current) chatEndRef.current.scrollIntoView({ behavior: "smooth" });
  }, [chatOpen, chatMessages]);

  return (
    <div className="min-h-screen bg-gray-100">

      {/* Top Navbar */}
      <div className="bg-slate-800 text-white px-6 py-4 flex justify-between items-center">
        <div className="font-bold text-lg">MedScribe AI Verifier</div>
        <button
          type="button"
          onClick={() => setChatOpen(true)}
          className="px-4 py-2 rounded-lg bg-slate-600 hover:bg-slate-500 text-sm font-medium transition-colors"
        >
          Chat with AI
        </button>
      </div>

      {/* Main Content */}
      <div className="p-6 grid grid-cols-3 gap-6">

        {/* LEFT PANEL */}
        <div className="bg-white rounded-xl shadow p-4 flex flex-col min-h-0 max-h-[calc(100vh-8rem)] overflow-y-auto">
          
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
                {transcript ? (
                  <div className="leading-relaxed">
                    {transcript.split(/\n\n+/).map((block, i) => (
                      <div key={i} className="mb-3 last:mb-0 whitespace-pre-line">
                        {block}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-gray-400">
                    Transcript will appear here...
                  </div>
                )}
              </div>
          </div>
          
          <div className="mt-4 space-y-3">
            <button
              onClick={handleAnalyze}
              disabled={!transcript || loadingAnalysis}
              className="w-full bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:bg-gray-400"
            >
              {loadingAnalysis ? "Analyzing..." : "Analyze Transcript"}
            </button>

            <div>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.jpg,.jpeg,.png"
                className="hidden"
                onChange={handleFileChange}
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="w-full border border-gray-300 text-gray-700 px-4 py-2 rounded hover:bg-gray-50"
              >
                Upload files (patient medical history)
              </button>
              {medicalHistoryFiles.length > 0 && (
                <ul className="mt-2 text-sm text-gray-600 space-y-1">
                  {medicalHistoryFiles.map((file, i) => (
                    <li key={i} className="flex items-center justify-between gap-2">
                      <span className="truncate">{file.name}</span>
                      <button
                        type="button"
                        onClick={() => removeMedicalFile(i)}
                        className="text-red-600 hover:text-red-700 shrink-0"
                        aria-label="Remove file"
                      >
                        Remove
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
          {/* <div className="mt-6 border-t pt-4">
            <h3 className="font-medium mb-2">Audio</h3>
            <div className="h-16 bg-gray-200 rounded flex items-center justify-center">
              🎙 Audio Waveform Placeholder
            </div>
          </div> */}


        </div>

        {/* CENTER PANEL */}
        
        <div className="bg-white rounded-xl shadow p-4 flex flex-col min-h-0 max-h-[calc(100vh-8rem)]">
          <h2 className="font-semibold text-lg mb-4 shrink-0">
            AI Analysis
          </h2>

          {loadingAnalysis && (
            <p className="text-gray-500">Running AI analysis...</p>
          )}

          {!loadingAnalysis && analysis && (
            <>
              {/* Tabs — Flags moved to right panel */}
              <div className="flex space-x-6 border-b mb-4 shrink-0">
                {["summary", "thoughts", "critique"].map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveAnalysisTab(tab)}
                    className={`pb-2 capitalize ${
                      activeAnalysisTab === tab
                        ? "border-b-2 border-blue-600 text-blue-600 font-medium"
                        : "text-gray-500"
                    }`}
                  >
                    {tab === "thoughts" ? "Clinical Thoughts" : tab.charAt(0).toUpperCase() + tab.slice(1)}
                  </button>
                ))}
              </div>

              {/* Content — scrollable, markdown rendered */}
              <div className="text-sm min-h-0 flex-1 overflow-y-auto">
                <MarkdownBlock text={analysis[activeAnalysisTab] ?? ""} />
              </div>
            </>
          )}

          {!loadingAnalysis && !analysis && (
            <p className="text-gray-400">
              Analysis will appear here after clicking "Analyze Transcript".
            </p>
          )}
        </div>
                


         

        {/* RIGHT PANEL — Verifier & Critical Checks + Flags */}
        <div className="bg-white rounded-xl shadow p-4 flex flex-col min-h-0 max-h-[calc(100vh-8rem)]">
          <h2 className="font-semibold text-lg mb-4 shrink-0">
            Verifier & Critical Checks
          </h2>

          <div className="space-y-3 text-sm min-h-0 flex-1 overflow-y-auto">
            {loadingAnalysis && (
              <p className="text-gray-500 py-2">Running checks...</p>
            )}

            {!loadingAnalysis && flaggedList.length > 0 && (
              <>
                {flaggedList.map((flag, i) => {
                  if (dismissedFlagIndices.has(i)) return null;
                  const isExiting = exitingFlagIndices.has(i);
                  const isHigh = flag.priority === "high";
                  const isMedium = flag.priority === "medium";
                  const bg = isHigh ? "bg-red-50" : isMedium ? "bg-amber-50" : "bg-gray-50";
                  const border = isHigh ? "border-red-500" : isMedium ? "border-amber-500" : "border-gray-400";
                  const title = flag.priority.charAt(0).toUpperCase() + flag.priority.slice(1) + " priority";
                  return (
                    <div
                      key={i}
                      onTransitionEnd={() => isExiting && handleFlagTransitionEnd(i)}
                      className={`${bg} border-l-4 ${border} rounded-r-md shadow-sm relative pr-8 transition-all duration-300 ease-out overflow-hidden ${
                        isExiting ? "max-h-0 opacity-0 py-0 my-0 border-0" : "max-h-[300px] p-3"
                      }`}
                    >
                      <button
                        type="button"
                        onClick={() => dismissFlag(i)}
                        className="absolute top-2 right-2 w-6 h-6 flex items-center justify-center rounded-full text-gray-500 hover:text-gray-800 hover:bg-black/5 transition-colors"
                        aria-label="Dismiss flag"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                      <strong className="text-gray-900 block pr-2">{title}</strong>
                      <p className="mt-1 text-gray-700 leading-snug pr-2">{flag.details}</p>
                    </div>
                  );
                })}
              </>
            )}

            {!loadingAnalysis && (!analysis || flaggedList.length === 0) && (
              <>
                <div className="bg-gray-50 border-l-4 border-gray-400 p-3 rounded-r-md">
                  <strong className="text-gray-900">Low Confidence</strong>
                  <p className="mt-1 text-gray-600">Missing objective vitals.</p>
                </div>
                <div className="bg-amber-50 border-l-4 border-amber-500 p-3 rounded-r-md">
                  <strong className="text-gray-900">Clinical Consistency</strong>
                  <p className="mt-1 text-gray-600">Chest pain not fully evaluated.</p>
                </div>
                <div className="bg-gray-50 border-l-4 border-gray-400 p-3 rounded-r-md">
                  <strong className="text-gray-900">EHR Integration</strong>
                  <p className="mt-1 text-gray-600">Status: Pending Signature</p>
                </div>
              </>
            )}
          </div>
        </div>

      </div>

      {/* Chat tab — slides in from the right */}
      <div
        className={`fixed inset-y-0 right-0 z-50 w-full sm:w-[28rem] max-w-[100vw] bg-[#F2F2F7] flex flex-col shadow-2xl transition-transform duration-300 ease-out ${
          chatOpen ? "translate-x-0" : "translate-x-full"
        }`}
        role="dialog"
        aria-modal="true"
        aria-label="Chat with AI"
      >
        {/* Header */}
        <div className="flex items-center gap-3 px-4 py-3 bg-white border-b border-gray-200 shrink-0">
          <button
            type="button"
            onClick={() => setChatOpen(false)}
            className="p-2 -ml-2 rounded-full hover:bg-gray-100 transition-colors"
            aria-label="Close chat"
          >
            <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <h3 className="font-semibold text-gray-900">Chat with AI</h3>
        </div>

        {/* Messages — iMessage style */}
        <div className="flex-1 min-h-0 overflow-y-auto px-3 py-4 space-y-2">
          {chatMessages.length === 0 && (
            <p className="text-center text-gray-400 text-sm py-8">
              Ask about this encounter. Transcript and analysis are sent as context.
            </p>
          )}
          {chatMessages.map((m, i) => (
            <div
              key={i}
              className={`flex ${m.role === "doctor" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] px-4 py-2.5 text-[15px] leading-snug whitespace-pre-wrap ${
                  m.role === "doctor"
                    ? "bg-[#007AFF] text-white rounded-[18px] rounded-br-[4px]"
                    : "bg-[#E5E5EA] text-gray-900 rounded-[18px] rounded-bl-[4px]"
                }`}
              >
                {m.text}
              </div>
            </div>
          ))}
          {chatLoading && (
            <div className="flex justify-start">
              <div className="max-w-[85%] px-4 py-2.5 rounded-[18px] rounded-bl-[4px] bg-[#E5E5EA] text-gray-500 text-[15px]">
                …
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Input bar — iMessage style */}
        <div className="p-3 pb-6 bg-[#F2F2F7] shrink-0">
          <div className="flex items-end gap-2 bg-white rounded-[20px] pl-4 pr-2 py-2 min-h-[44px] border border-gray-200">
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendChatMessage()}
              placeholder="Message"
              className="flex-1 min-w-0 bg-transparent text-[15px] text-gray-900 placeholder-gray-400 focus:outline-none py-1.5"
            />
            <button
              type="button"
              onClick={sendChatMessage}
              disabled={chatLoading || !chatInput.trim()}
              className="shrink-0 w-8 h-8 rounded-full bg-[#007AFF] flex items-center justify-center disabled:opacity-40 disabled:cursor-not-allowed active:opacity-80 transition-opacity"
              aria-label="Send"
            >
              <svg className="w-4 h-4 text-white ml-0.5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Backdrop when chat is open (optional tap to close on mobile) */}
      <div
        className={`fixed inset-0 bg-black/20 z-40 transition-opacity duration-300 ${
          chatOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        }`}
        onClick={() => setChatOpen(false)}
        aria-hidden="true"
      />
    </div>
  );
}