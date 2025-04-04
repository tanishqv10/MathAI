"use client";

import { useState } from "react";
import { BlockMath } from "react-katex";
import "katex/dist/katex.min.css";

export default function Home() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    setLoading(true);
    setResult(null);

    try {
      const res = await fetch("https://uiobb5kz8i.execute-api.us-west-2.amazonaws.com/solve", {
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

  return (
    <main className="flex flex-col items-center justify-center min-h-screen bg-zinc-900 text-white px-4">
      <h1 className="text-3xl md:text-3xl font-bold mb-6 text-center">
        MathAI - <span className="text-blue-400">Algebra Tutor</span>
      </h1>
  
      <div className="w-full max-w-xl">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full px-4 py-3 text-xl border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 text-white"
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
              {result.result && (
                <div>
                  <p className="font-semibold">Answer:</p>
                  <p className="mb-2">{result.result}</p>

                  {result.latex && (
                    <div className="bg-gray-50 p-3 rounded-md border mt-2 text-center">
                      <BlockMath math={result.latex} />
                    </div>
                  )}
                </div>
              )}

              {result.chain_of_thought && (
                <details className="mt-4">
                  <summary className="cursor-pointer text-blue-600 font-semibold">Full Reasoning Trace</summary>
                  <div className="mt-2 text-sm bg-gray-100 p-3 rounded-md text-gray-800 space-y-6">
                    {
                      Array.from(result.chain_of_thought.matchAll(/Observation: ({.*?})\nThought:(.*?)\n/g) as RegExpMatchArray[]).map((match, index) => {
                        const obsText = match[1].replace(/'/g, '"');
                        const thoughtText = match[2]?.trim();

                        try {
                          const obs = JSON.parse(obsText);

                          let label = "Tool";

                          if (obs.derivative) {
                            label = "Differentiation";
                          } else if (obs.integral) {
                            label = "Integration";
                          } else if (obs.simplified) {
                            label = "Simplification";
                          } else if (obs.solution) {
                            label = "Solving Equation";
                          }

                          return (
                            <div key={index} className="border-l-4 border-blue-400 pl-4">
                              <p className="font-semibold mb-2">{label}</p>

                              {obs.input && (
                                <p><span className="font-semibold">Input:</span> <code>{obs.input}</code></p>
                              )}

                              {thoughtText && (
                                <p className="italic text-gray-600 mt-2">{thoughtText}</p>
                              )}

                              {obs.steps && obs.steps.length > 0 && (
                                <div className="mt-2">
                                  <p className="font-semibold mb-1">Steps:</p>
                                  <ul className="list-disc ml-6">
                                    {obs.steps.map((step: string, i: number) => (
                                      <li key={i}>{step}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}

                              {obs.derivative && (
                                <p className="mt-2"><span className="font-semibold">Derivative:</span> <code>{obs.derivative}</code></p>
                              )}
                              {obs.integral && (
                                <p className="mt-2"><span className="font-semibold">Integral:</span> <code>{obs.integral}</code></p>
                              )}
                              {obs.simplified && (
                                <p className="mt-2"><span className="font-semibold">Simplified:</span> <code>{obs.simplified}</code></p>
                              )}
                              {obs.solution && (
                                <p className="mt-2"><span className="font-semibold">Solution:</span> <code>{obs.solution}</code></p>
                              )}
                            </div>
                          );
                        } catch (e) {
                          return <p key={index} className="text-red-600">Failed to parse reasoning step.</p>;
                        }
                      })
                    }
                  </div>
                </details>
              )}

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
