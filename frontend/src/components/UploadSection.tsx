import { useRef, useState } from "react";
import { ingestPdf, pollRun } from "../api";
import LoadingDots from "./LoadingDots";

type Status = "idle" | "uploading" | "processing" | "done" | "error";

const STAGE_LABEL: Record<Status, string> = {
  idle:       "Ingest",
  uploading:  "Uploading…",
  processing: "Indexing…",
  done:       "Ingest",
  error:      "Ingest",
};

const STAGE_HINT: Partial<Record<Status, string>> = {
  uploading:  "Uploading file to server",
  processing: "Embedding and storing chunks",
};

export default function UploadSection() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [fileName, setFileName] = useState("");
  const [error, setError] = useState("");

  async function handleUpload() {
    const file = inputRef.current?.files?.[0];
    if (!file) return;

    setStatus("uploading");
    setError("");
    setFileName(file.name);

    try {
      const eventId = await ingestPdf(file);
      setStatus("processing");
      await pollRun(eventId);
      setStatus("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setStatus("error");
    }
  }

  const busy = status === "uploading" || status === "processing";

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">

      {/* Header */}
      <div className="mb-5">
        <h2 className="text-sm font-semibold text-zinc-100">Upload a PDF</h2>
        <p className="mt-0.5 text-xs text-zinc-500">
          Supported format: PDF · Max 50 MB
        </p>
      </div>

      {/* File input */}
      <div className="mb-4">
        <label className="mb-1.5 block text-xs font-medium text-zinc-400">
          Select file
        </label>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          disabled={busy}
          onChange={() => setStatus("idle")}
          className="block w-full rounded-lg border border-zinc-700 bg-zinc-800 text-sm text-zinc-400
            transition
            file:mr-3 file:cursor-pointer file:rounded-md file:border-0
            file:bg-zinc-700 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-zinc-200
            hover:file:bg-zinc-600
            focus:outline-none disabled:cursor-not-allowed disabled:opacity-40"
        />
      </div>

      {/* Ingest button */}
      <button
        onClick={handleUpload}
        disabled={busy}
        className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5
          text-sm font-medium text-white transition
          hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 focus:ring-offset-2
          focus:ring-offset-zinc-900 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {busy && (
          <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
        )}
        {STAGE_LABEL[status]}
      </button>

      {/* Loading hint */}
      {busy && (
        <div className="mt-4 flex items-center gap-2.5 text-indigo-400">
          <LoadingDots />
          <span className="text-xs">{STAGE_HINT[status]}</span>
        </div>
      )}

      {/* Success */}
      {status === "done" && (
        <div className="mt-4 flex items-start gap-2 rounded-lg border border-emerald-800 bg-emerald-950/60 px-3 py-2.5">
          <svg className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
          <span className="text-xs text-emerald-400">
            <span className="font-medium">{fileName}</span> ingested successfully.
          </span>
        </div>
      )}

      {/* Error */}
      {status === "error" && (
        <div className="mt-4 flex items-start gap-2 rounded-lg border border-red-900 bg-red-950/60 px-3 py-2.5">
          <svg className="mt-0.5 h-4 w-4 shrink-0 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
          <span className="text-xs text-red-400">{error}</span>
        </div>
      )}

    </div>
  );
}
