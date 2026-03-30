const BASE = "";

export interface RunOutput {
  answer: string;
  sources: string[];
  num_contexts: number;
}

export async function ingestPdf(file: File): Promise<string> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/api/ingest`, { method: "POST", body: form });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail ?? `Ingest failed (${res.status})`);
  }
  const data = await res.json();
  return data.event_id as string;
}

export async function queryPdf(question: string, topK: number): Promise<string> {
  const res = await fetch(`${BASE}/api/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k: topK }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail ?? `Query failed (${res.status})`);
  }
  const data = await res.json();
  return data.event_id as string;
}

const COMPLETED = new Set(["Completed", "Succeeded", "Success", "Finished"]);
const FAILED = new Set(["Failed", "Cancelled"]);

export async function pollRun(eventId: string, timeoutMs = 120_000): Promise<RunOutput> {
  const deadline = Date.now() + timeoutMs;
  let interval = 500;

  while (Date.now() < deadline) {
    const res = await fetch(`${BASE}/api/runs/${eventId}`);
    if (res.ok) {
      const data = await res.json();
      const runs: { status: string; output: RunOutput }[] = data.data ?? [];
      if (runs.length > 0) {
        const { status, output } = runs[0];
        if (COMPLETED.has(status)) return output;
        if (FAILED.has(status)) throw new Error(`Run ${status}`);
      }
    }
    await new Promise((r) => setTimeout(r, interval));
    interval = Math.min(interval * 1.5, 5000);
  }

  throw new Error("Timed out waiting for result");
}
