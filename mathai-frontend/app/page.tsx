"use client";

import { useState } from "react";
import { BlockMath } from "react-katex";

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
                <p>
                  <span className="font-semibold">Answer:</span> {result.result}
                </p>
              )}
              {result.chain_of_thought && (
                <details className="mt-4">
                  <summary className="cursor-pointer text-blue-600 font-semibold">View Reasoning (Chain of Thought)</summary>
                  <pre className="whitespace-pre-wrap mt-2 text-sm bg-gray-100 p-3 rounded-md text-gray-800">
                    {result.chain_of_thought}
                  </pre>
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
