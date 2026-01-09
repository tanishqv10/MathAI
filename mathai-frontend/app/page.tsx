"use client";

import { useState, useRef, useCallback } from "react";
import "katex/dist/katex.min.css";
import { InlineMath, BlockMath } from "react-katex";

// Backend response type
interface SolveResponse {
  success: boolean;
  query: string;
  operation: string;
  answer?: string;
  latex_answer?: string;
  explanation?: string;
  assumptions?: string[];
  citations?: string[];
  error?: string;
}

// Streaming event types
interface StreamAnswerEvent {
  type: "answer";
  data: {
    success: boolean;
    query: string;
    operation: string;
    answer?: string;
    latex_answer?: string;
    assumptions?: string[];
    citations?: string[];
  };
}

interface StreamExplanationEvent {
  type: "explanation";
  data: string;
}

interface StreamDoneEvent {
  type: "done";
}

interface StreamErrorEvent {
  type: "error";
  data: string;
}

type StreamEvent = StreamAnswerEvent | StreamExplanationEvent | StreamDoneEvent | StreamErrorEvent;

// Render text with inline LaTeX and markdown bold
function renderRichText(content: string): React.ReactNode[] {
  // First, split by LaTeX patterns: \[...\], \(...\), $$...$$, $...$
  const latexPattern = /(\\\[[\s\S]*?\\\]|\\\([\s\S]*?\\\)|\$\$[\s\S]*?\$\$|\$[^$\n]+\$)/g;
  const parts = content.split(latexPattern);

  return parts.map((part, index) => {
    // Block math: \[...\] or $$...$$
    if (part.startsWith("\\[") && part.endsWith("\\]")) {
      return <BlockMath key={index} math={part.slice(2, -2)} />;
    }
    if (part.startsWith("$$") && part.endsWith("$$")) {
      return <BlockMath key={index} math={part.slice(2, -2)} />;
    }
    // Inline math: \(...\) or $...$
    if (part.startsWith("\\(") && part.endsWith("\\)")) {
      return <InlineMath key={index} math={part.slice(2, -2)} />;
    }
    if (part.startsWith("$") && part.endsWith("$") && part.length > 2) {
      return <InlineMath key={index} math={part.slice(1, -1)} />;
    }
    // Plain text with markdown bold parsing
    return <span key={index}>{parseMarkdownBold(part)}</span>;
  });
}

// Parse **bold** markdown syntax
function parseMarkdownBold(text: string): React.ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    return <span key={index}>{part}</span>;
  });
}

// Render pure LaTeX (for latex_answer field which is always LaTeX)
function renderLatex(latex: string): React.ReactNode {
  try {
    return <BlockMath math={latex} />;
  } catch {
    return <code className="text-sm">{latex}</code>;
  }
}

// Parse explanation into structured sections
interface ExplanationSection {
  title: string;
  content: string;
}

function parseExplanation(explanation: string): ExplanationSection[] {
  const sections: ExplanationSection[] = [];
  const lines = explanation.split("\n");
  
  let currentSection: ExplanationSection | null = null;
  let currentContent: string[] = [];
  
  for (const line of lines) {
    const trimmed = line.trim();
    const match = trimmed.match(/^(\d+)\.\s+\*?\*?([^*:\n]+)\*?\*?:?\s*(.*)/);
    
    if (match) {
      // Save previous section
      if (currentSection) {
        currentSection.content = currentContent.join("\n").trim();
        if (currentSection.content || currentSection.title) {
          sections.push(currentSection);
        }
      }
      // Start new section
      currentSection = {
        title: match[2].trim(),
        content: match[3] || ""
      };
      currentContent = match[3] ? [match[3]] : [];
    } else if (currentSection && trimmed) {
      // Add to current section content
      currentContent.push(trimmed);
    }
  }
  
  // Don't forget last section
  if (currentSection) {
    currentSection.content = currentContent.join("\n").trim();
    if (currentSection.content || currentSection.title) {
      sections.push(currentSection);
    }
  }
  
  return sections;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<SolveResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [streamingExplanation, setStreamingExplanation] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Streaming submit handler
  const handleSubmitStream = useCallback(async () => {
    if (!query.trim()) return;
    setLoading(true);
    setStreaming(true);
    setResult(null);
    setStreamingExplanation("");

    // Abort any previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    try {
      const res = await fetch(`${API_BASE_URL}/solve/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
        signal: abortControllerRef.current.signal,
      });

      if (!res.ok) {
        throw new Error(`Server error: ${res.status}`);
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buffer = "";
      let explanationBuffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const event: StreamEvent = JSON.parse(line.slice(6));

              if (event.type === "answer") {
                // Show answer immediately
                setResult({
                  success: event.data.success,
                  query: event.data.query,
                  operation: event.data.operation,
                  answer: event.data.answer,
                  latex_answer: event.data.latex_answer,
                  assumptions: event.data.assumptions,
                  citations: event.data.citations,
                  explanation: "", // Will be streamed
                });
                setLoading(false); // Answer received, no longer "loading"
              } else if (event.type === "explanation") {
                explanationBuffer += event.data;
                setStreamingExplanation(explanationBuffer);
              } else if (event.type === "done") {
                // Finalize the result with complete explanation
                setResult((prev) =>
                  prev ? { ...prev, explanation: explanationBuffer } : null
                );
                setStreaming(false);
              } else if (event.type === "error") {
                setResult({
                  success: false,
                  query: query,
                  operation: "unknown",
                  error: event.data,
                });
                setStreaming(false);
                setLoading(false);
              }
            } catch {
              // Ignore parse errors for incomplete chunks
            }
          }
        }
      }
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      setResult({
        success: false,
        query: query,
        operation: "unknown",
        error: "Failed to connect to the server. Make sure the backend is running.",
      });
    } finally {
      setLoading(false);
      setStreaming(false);
    }
  }, [query]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSubmitStream();
    }
  };

  // Use streaming explanation while streaming, otherwise use result.explanation
  const displayExplanation = streaming ? streamingExplanation : result?.explanation;
  
  // Parse explanation into sections
  const explanationSections = displayExplanation ? parseExplanation(displayExplanation) : [];

  return (
    <main className="flex flex-col items-center justify-center min-h-screen bg-zinc-900 text-white px-4">
      <h1 className="text-3xl md:text-3xl font-bold mb-6 text-center">
        MathAI - <span className="text-blue-400">Algebra Tutor</span>
      </h1>

      <div className="w-full max-w-xl">
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          className="w-full px-4 py-3 text-xl border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 text-white bg-zinc-800"
          placeholder="Enter your math query..."
        />

        <div className="flex justify-center mt-6 space-x-4">
          <button
            onClick={handleSubmitStream}
            disabled={loading || streaming}
            className="bg-blue-600 hover:bg-blue-700 text-white text-l px-4 py-2 rounded disabled:opacity-70"
          >
            {loading ? "Computing..." : streaming ? "Explaining..." : "Submit"}
          </button>

          <button
            onClick={() => {
              if (abortControllerRef.current) {
                abortControllerRef.current.abort();
              }
              setQuery("");
              setResult(null);
              setStreamingExplanation("");
              setStreaming(false);
              setLoading(false);
              inputRef.current?.focus();
            }}
            disabled={false}
            className="bg-gray-600 hover:bg-gray-700 text-white text-l px-4 py-2 rounded"
          >
            Clear
          </button>
        </div>

        {result && (
          <div className="flex justify-center mt-8">
            <div className="bg-white p-6 rounded-2xl shadow max-w-[90%] w-full overflow-x-auto text-gray-800 space-y-4">
              {result.success ? (
                <div className="space-y-6">
                  {/* 📝 Original Query */}
                  <div>
                    <p className="font-semibold text-xl mb-2">📝 Problem:</p>
                    <div className="bg-gray-50 p-4 rounded-md text-gray-900">
                      {renderRichText(result.query)}
                    </div>
                  </div>

                  {/* 🔧 Operation Badge */}
                  {result.operation && (
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-500">Operation:</span>
                      <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium capitalize">
                        {result.operation}
                      </span>
                    </div>
                  )}

                  {/* ✅ Final Answer */}
                  {result.latex_answer ? (
                    <div>
                      <p className="font-semibold text-xl mb-2">✅ Final Answer:</p>
                      <div className="bg-green-100 p-4 rounded-md text-gray-900 flex justify-center">
                        {renderLatex(result.latex_answer)}
                      </div>
                    </div>
                  ) : result.answer && (
                    <div>
                      <p className="font-semibold text-xl mb-2">✅ Final Answer:</p>
                      <div className="bg-green-100 p-4 rounded-md text-gray-900">
                        {renderRichText(result.answer)}
                      </div>
                    </div>
                  )}

                  {/* 🧩 Step-by-step Explanation */}
                  {(displayExplanation || streaming) && (
                    <div>
                      <p className="font-semibold text-xl mb-2">
                        🧩 Explanation:
                        {streaming && (
                          <span className="ml-2 text-sm font-normal text-blue-500 animate-pulse">
                            (streaming...)
                          </span>
                        )}
                      </p>
                      {explanationSections.length > 0 ? (
                        <div className="space-y-4">
                          {explanationSections.map((section, i) => (
                            <div key={i} className="bg-gray-50 p-4 rounded-md">
                              <p className="font-semibold text-gray-800 mb-2">
                                {i + 1}. {section.title}
                              </p>
                              {section.content && (
                                <div className="text-gray-700 leading-relaxed pl-4">
                                  {renderRichText(section.content)}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      ) : displayExplanation ? (
                        <div className="bg-yellow-50 p-4 rounded-md text-gray-800 leading-relaxed whitespace-pre-wrap">
                          {renderRichText(displayExplanation)}
                        </div>
                      ) : streaming ? (
                        <div className="bg-gray-50 p-4 rounded-md text-gray-500 animate-pulse">
                          Generating explanation...
                        </div>
                      ) : null}
                    </div>
                  )}

                  {/* 📚 Assumptions */}
                  {result.assumptions && result.assumptions.length > 0 && (
                    <div>
                      <p className="font-semibold text-lg mb-2">📚 Assumptions:</p>
                      <ul className="list-disc ml-6 space-y-1 text-gray-700">
                        {result.assumptions.map((assumption, i) => (
                          <li key={i}>{assumption}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* 📖 Citations */}
                  {result.citations && result.citations.length > 0 && (
                    <div>
                      <p className="font-semibold text-lg mb-2">📖 References:</p>
                      <ul className="list-disc ml-6 space-y-1 text-gray-600 text-sm">
                        {result.citations.map((citation, i) => (
                          <li key={i}>{citation}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-red-500 font-semibold">
                  <p>❌ Error:</p>
                  <p className="mt-2">{result.error}</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
