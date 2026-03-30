import { useRef, useState } from "react";
import { ingestPdf, pollRun } from "../api";

type Status = "idle" | "uploading" | "processing" | "done" | "error";

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
    <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
      <h2 className="mb-4 text-xl font-semibold text-gray-800">Upload a PDF</h2>

      <div className="flex items-center gap-3">
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          disabled={busy}
          onChange={() => setStatus("idle")}
          className="block w-full text-sm text-gray-500 file:mr-3 file:rounded-lg file:border-0 file:bg-indigo-50 file:px-4 file:py-2 file:text-sm file:font-medium file:text-indigo-700 hover:file:bg-indigo-100 disabled:opacity-50"
        />
        <button
          onClick={handleUpload}
          disabled={busy}
          className="shrink-0 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {busy ? "Processing…" : "Ingest"}
        </button>
      </div>

      {status === "done" && (
        <p className="mt-3 text-sm text-green-600">
          ✓ <span className="font-medium">{fileName}</span> ingested successfully.
        </p>
      )}
      {status === "error" && (
        <p className="mt-3 text-sm text-red-600">{error}</p>
      )}
    </div>
  );
}
