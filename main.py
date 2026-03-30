import logging
from functools import lru_cache
from fastapi import FastAPI
import inngest
import inngest.fast_api
from inngest.experimental import ai
from dotenv import load_dotenv
import uuid
import os
from sentence_transformers import CrossEncoder
from data_loader import load_and_chunk_pdf, embed_texts
from vector_db import get_storage
from custom_types import RAGChunkAndSrc, RAGSearchResult, RAGUpsertResult

load_dotenv()

logger = logging.getLogger("rag.main")

inngest_client = inngest.Inngest(
    app_id="rag_app",
    logger=logging.getLogger("uvicorn"),
    is_production=False,
    serializer=inngest.PydanticSerializer()
)


@lru_cache(maxsize=1)
def _get_reranker() -> CrossEncoder:
    logger.info("Loading reranker model")
    return CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")


def _rerank(question: str, contexts: list[str]) -> list[str]:
    if not contexts:
        return contexts
    reranker = _get_reranker()
    pairs = [(question, c) for c in contexts]
    scores = reranker.predict(pairs)
    ranked = sorted(zip(scores, contexts), key=lambda x: x[0], reverse=True)
    logger.info("Reranked %d contexts", len(ranked))
    return [c for _, c in ranked]


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
    reranked_contexts = await ctx.step.run("rerank", lambda: _rerank(question, found.contexts))

    context_block = "\n\n".join(f"- {c}" for c in reranked_contexts)
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
    return {"answer": answer, "sources": found.sources, "num_contexts": len(reranked_contexts)}

app = FastAPI()

@app.get("/healthz")
def health():
    return {"status": "ok"}

inngest.fast_api.serve(app, inngest_client, [rag_ingest_pdf, rag_query_pdf_ai])
