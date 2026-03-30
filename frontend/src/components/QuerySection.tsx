import { useState } from "react";
import { queryPdf, pollRun, RunOutput } from "../api";
import LoadingDots from "./LoadingDots";

export default function QuerySection() {
  const [question, setQuestion] = useState("");
  const [topK, setTopK] = useState(5);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RunOutput | null>(null);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const eventId = await queryPdf(question.trim(), topK);
      const output = await pollRun(eventId);
      setResult(output);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Query failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">

      {/* Header */}
      <div className="mb-5">
        <h2 className="text-sm font-semibold text-zinc-100">Ask a Question</h2>
        <p className="mt-0.5 text-xs text-zinc-500">
          Answers are grounded in your uploaded documents.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">

        {/* Question textarea */}
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">
            Your question
          </label>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. What are the key findings of this paper?"
            rows={4}
            disabled={loading}
            className="w-full resize-none rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2.5
              text-sm text-zinc-100 placeholder-zinc-600 transition
              focus:border-indigo-500 focus:bg-zinc-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/20
              disabled:cursor-not-allowed disabled:opacity-40"
          />
        </div>

        {/* Controls row */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <label className="whitespace-nowrap text-xs font-medium text-zinc-400">
              Chunks
            </label>
            <input
              type="number"
              min={1}
              max={20}
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              disabled={loading}
              className="w-16 rounded-lg border border-zinc-700 bg-zinc-800 px-2.5 py-1.5
                text-center text-sm text-zinc-100 transition
                focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20
                disabled:cursor-not-allowed disabled:opacity-40"
            />
          </div>

          <button
            type="submit"
            disabled={loading || !question.trim()}
            className="ml-auto flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5
              text-sm font-medium text-white transition
              hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 focus:ring-offset-2
              focus:ring-offset-zinc-900 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {loading && (
              <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
            )}
            {loading ? "Searching…" : "Ask"}
          </button>
        </div>
      </form>

      {/* Loading state */}
      {loading && (
        <div className="mt-5 rounded-lg border border-zinc-800 bg-zinc-800/50 px-4 py-4">
          <div className="flex items-center gap-2.5 text-indigo-400">
            <LoadingDots />
            <span className="text-xs font-medium">Searching your documents</span>
          </div>
          <p className="mt-1.5 text-xs text-zinc-500">
            Generating a grounded answer…
          </p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mt-4 flex items-start gap-2 rounded-lg border border-red-900 bg-red-950/60 px-3 py-2.5">
          <svg className="mt-0.5 h-4 w-4 shrink-0 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
          <span className="text-xs text-red-400">{error}</span>
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="mt-5 space-y-4 border-t border-zinc-800 pt-5">

          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wider text-zinc-500">
              Answer
            </p>
            <p className="text-sm leading-relaxed text-zinc-200">
              {result.answer || "(No answer)"}
            </p>
          </div>

          {result.sources.length > 0 && (
            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wider text-zinc-500">
                Sources
              </p>
              <ul className="space-y-1.5">
                {result.sources.map((s) => (
                  <li key={s} className="flex items-center gap-2 text-xs text-zinc-400">
                    <span className="h-1 w-1 rounded-full bg-zinc-600" />
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          )}

        </div>
      )}

    </div>
  );
}
