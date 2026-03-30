import UploadSection from "./components/UploadSection";
import QuerySection from "./components/QuerySection";

export default function App() {
  return (
    <div className="min-h-screen bg-zinc-950 px-4 py-12">
      <div className="mx-auto max-w-4xl">

        {/* Header */}
        <div className="mb-10">
          <h1 className="text-xl font-semibold tracking-tight text-zinc-100">
            RAG Chatbot
          </h1>
          <p className="mt-1 text-sm text-zinc-500">
            Upload a PDF, then ask questions about its contents.
          </p>
        </div>

        {/* Two-column layout */}
        <div className="grid gap-4 md:grid-cols-2 md:items-start">
          <UploadSection />
          <QuerySection />
        </div>

      </div>
    </div>
  );
}
