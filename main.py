import logging
from functools import lru_cache
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import inngest
import inngest.fast_api
from inngest.experimental import ai
from dotenv import load_dotenv
import uuid
import os
import httpx
from data_loader import load_and_chunk_pdf, embed_texts, _get_model
from vector_db import get_storage
from custom_types import RAGChunkAndSrc, RAGSearchResult, RAGUpsertResult

load_dotenv()

logger = logging.getLogger("rag.main")

INNGEST_API_BASE = os.getenv("INNGEST_API_BASE", "http://127.0.0.1:8288/v1")
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))

inngest_client = inngest.Inngest(
    app_id="rag_app",
    logger=logging.getLogger("uvicorn"),
    is_production=False,
    serializer=inngest.PydanticSerializer()
)


@inngest_client.create_function(
    fn_id="RAG: Ingest PDF",
    trigger=inngest.TriggerEvent(event="rag/ingest_pdf")
)
async def rag_ingest_pdf(ctx: inngest.Context):
    def _load(ctx: inngest.Context) -> RAGChunkAndSrc:
        pdf_path = ctx.event.data["pdf_path"]
        source_id = ctx.event.data.get("source_id", pdf_path)
        logger.info("Loading PDF: %s", pdf_path)
        chunks = load_and_chunk_pdf(pdf_path)
        return RAGChunkAndSrc(chunks=chunks, source_id=source_id)

    def _upsert(chunks_and_src: RAGChunkAndSrc) -> RAGUpsertResult:
        chunks = chunks_and_src.chunks
        source_id = chunks_and_src.source_id
        logger.info("Embedding and upserting %d chunks for source: %s", len(chunks), source_id)
        vecs = embed_texts(chunks)
        ids = [str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}:{i}")) for i in range(len(chunks))]
        payloads = [{"source": source_id, "text": chunks[i]} for i in range(len(chunks))]
        get_storage().upsert(ids, vecs, payloads)
        return RAGUpsertResult(ingested=len(chunks))

    chunks_and_src = await ctx.step.run("load-and-chunk", lambda: _load(ctx), output_type=RAGChunkAndSrc)
    ingested = await ctx.step.run("embed-and-upsert", lambda: _upsert(chunks_and_src), output_type=RAGUpsertResult)
    return ingested.model_dump()


@inngest_client.create_function(
    fn_id="RAG: Query PDF",
    trigger=inngest.TriggerEvent(event="rag/query_pdf_ai")
)
async def rag_query_pdf_ai(ctx: inngest.Context):
    def _search(question: str, top_k: int = 5) -> RAGSearchResult:
        logger.info("Searching for: %s (top_k=%d)", question, top_k)
        query_vec = embed_texts([question])[0]
        found = get_storage().search(query_vec, top_k)
        return RAGSearchResult(contexts=found["contexts"], sources=found["sources"])

    question = ctx.event.data["question"]
    top_k = int(ctx.event.data.get("top_k", 5))

    found = await ctx.step.run("embed-and-search", lambda: _search(question, top_k), output_type=RAGSearchResult)

    logger.info("Retrieved %d contexts for question: %s", len(found.contexts), question)
    if not found.contexts:
        logger.info("No contexts found — skipping LLM call")
        return {
            "answer": "I couldn't find relevant context in the uploaded documents.",
            "sources": [],
            "num_contexts": 0,
        }

    context_block = "\n\n".join(f"- {c}" for c in found.contexts)
    user_content = (
        "Use the following context to answer the question.\n\n"
        f"Context:\n{context_block}\n\n"
        f"Question: {question}\n"
        "Answer concisely using the context above."
    )

    adapter = ai.openai.Adapter(
        auth_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o-mini"
    )

    res = await ctx.step.ai.infer(
        "llm-answer",
        adapter=adapter,
        body={
            "max_tokens": 1024,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": "You answer questions using only the provided context."},
                {"role": "user", "content": user_content}
            ]
        }
    )

    try:
        answer = res["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        logger.warning("Unexpected LLM response shape: %s | raw: %s", exc, res)
        answer = "Sorry, I could not generate an answer."

    logger.info("Answer generated for question: %s", question)
    return {"answer": answer, "sources": found.sources, "num_contexts": len(found.contexts)}


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def preload_models() -> None:
    logger.info("Preloading models at startup...")
    try:
        _get_model()
        logger.info("Models preloaded successfully")
    except Exception as exc:
        logger.error("Model preloading failed (app will continue): %s", exc)


@app.get("/healthz")
def health():
    return {"status": "ok"}


@app.post("/api/ingest")
async def api_ingest(file: UploadFile = File(...)):
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_UPLOAD_MB} MB limit")

    uploads_dir = Path("uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename).name
    file_path = (uploads_dir / safe_name).resolve()
    if not str(file_path).startswith(str(uploads_dir.resolve())):
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path.write_bytes(contents)
    logger.info("Saved uploaded file: %s", file_path)

    events = await inngest_client.send(
        inngest.Event(
            name="rag/ingest_pdf",
            data={"pdf_path": str(file_path), "source_id": safe_name},
        )
    )
    return {"event_id": events[0]}


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5


@app.post("/api/query")
async def api_query(body: QueryRequest):
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    events = await inngest_client.send(
        inngest.Event(
            name="rag/query_pdf_ai",
            data={"question": body.question.strip(), "top_k": body.top_k},
        )
    )
    return {"event_id": events[0]}


@app.get("/api/runs/{event_id}")
async def api_runs(event_id: str):
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{INNGEST_API_BASE}/events/{event_id}/runs", timeout=10)
            r.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("Failed to fetch runs for event %s: %s", event_id, exc)
            raise HTTPException(status_code=502, detail="Could not reach Inngest dev server")
    return r.json()


inngest.fast_api.serve(app, inngest_client, [rag_ingest_pdf, rag_query_pdf_ai])
