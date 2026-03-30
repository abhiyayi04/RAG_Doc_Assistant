import UploadSection from "./components/UploadSection";
import QuerySection from "./components/QuerySection";

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50 px-4 py-10">
      <div className="mx-auto max-w-5xl">
        <h1 className="mb-8 text-3xl font-bold text-gray-900">RAG Chatbot</h1>
        <div className="grid gap-6 md:grid-cols-2">
          <UploadSection />
          <QuerySection />
        </div>
      </div>
    </div>
  );
}
