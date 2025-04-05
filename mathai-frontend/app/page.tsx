"use client";

import { useState, useRef } from "react";
import "katex/dist/katex.min.css";
import { InlineMath, BlockMath } from "react-katex";

function renderMixedLatex(content: string) {
  const parts = content.split(/(\\\[.*?\\\]|\\\(.*?\\\))/g);

  return parts.map((part, index) => {
    if (part.startsWith("\\[") && part.endsWith("\\]")) {
      return <BlockMath key={index} math={part.slice(2, -2)} />;
    } else if (part.startsWith("\\(") && part.endsWith("\\)")) {
      return <InlineMath key={index} math={part.slice(2, -2)} />;
    } else {
      return <span key={index}>{part}</span>;
    }
  });
}

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL;

export default function Home() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setResult(null);

    try {
      const res = await fetch(`${apiBaseUrl}/solve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });

      const data = await res.json();
      setResult(data);
    } catch (error) {
      setResult({ error: "Failed to fetch result." });
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSubmit();
    }
  };

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
            onClick={handleSubmit}
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 text-white text-l px-4 py-2 rounded disabled:opacity-70"
          >
            {loading ? "Solving..." : "Submit"}
          </button>

          <button
            onClick={() => {
              setQuery("");
              setResult(null);
              inputRef.current?.focus();
            }}
            disabled={loading}
            className="bg-gray-600 hover:bg-gray-700 text-white text-l px-4 py-2 rounded disabled:opacity-70"
          >
            Clear
          </button>
        </div>

        {result && (
          <div className="flex justify-center mt-8">
            <div className="bg-white p-6 rounded-2xl shadow max-w-[90%] w-full overflow-x-auto text-gray-800 space-y-4">
              {result.result && (() => {
                const rawResult = result.result;
                const input = rawResult.input || "";
                const output = rawResult.output || "";

                // ✅ Always extract first line as final answer
                const [firstLine, ...rest] = output.split("\n");
                const finalAnswer = firstLine.trim();

                // ✅ Try to extract step-by-step explanation from the rest
                const restJoined = rest.join("\n").trim();
                let steps: string[] = [];

                const explanationMatch = restJoined.match(/Explanation:\s*([\s\S]*)/i);
                if (explanationMatch) {
                  const explanation = explanationMatch[1].trim();
                  steps = explanation
                    .split(/\n(?=\d+\.)/)
                    .filter((line: string) => /^\d+\.\s+/.test(line.trim()));
                } else {
                  const possibleSteps = restJoined.split(/\n(?=\d+\.)/);
                  steps = possibleSteps.filter((line: string) => /^\d+\.\s+/.test(line.trim()));
                }

                return (
                  <div className="space-y-6">
                    {/* 📝 Original Query */}
                    {input && (
                      <div>
                        <p className="font-semibold text-xl mb-2">📝 Problem:</p>
                        <div className="bg-gray-50 p-4 rounded-md text-gray-900">
                          {renderMixedLatex(input)}
                        </div>
                      </div>
                    )}

                    {/* ✅ Final Answer */}
                    {finalAnswer && (
                      <div>
                        <p className="font-semibold text-xl mb-2">✅ Final Answer:</p>
                        <div className="bg-green-100 p-4 rounded-md text-gray-900">
                          {renderMixedLatex(finalAnswer)}
                        </div>
                      </div>
                    )}

                    {/* 🧩 Step-by-step Explanation */}
                    {steps.length > 0 ? (
                      <div>
                        <p className="font-semibold text-xl mb-2">🧩 Step-by-step Explanation:</p>
                        <ol className="list-decimal ml-6 space-y-2 text-gray-800 leading-relaxed">
                          {steps.map((step: string, i: number) => {
                            const match = step.match(/^(\d+\.)\s*(.*)/);
                            const content = match?.[2] || step;
                            return (
                              <li key={i}>
                                {renderMixedLatex(content)}
                              </li>
                            );
                          })}
                        </ol>
                      </div>
                    ) : restJoined ? (
                      <div>
                        <p className="font-semibold text-xl mb-2">🧩 Explanation:</p>
                        <div className="bg-yellow-100 p-4 rounded-md text-gray-800">
                          {renderMixedLatex(restJoined)}
                        </div>
                      </div>
                    ) : null}
                  </div>
                );
              })()}

              {result.error && (
                <p className="text-red-500 font-semibold">Error: {result.error}</p>
              )}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
