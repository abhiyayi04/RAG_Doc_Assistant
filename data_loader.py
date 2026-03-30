import logging
from pathlib import Path
from llama_index.readers.file import PDFReader
from llama_index.core.node_parser import SentenceSplitter
from sentence_transformers import SentenceTransformer

logger = logging.getLogger("rag.data_loader")

EMBED_MODEL = "all-MiniLM-L6-v2"
EMBED_DIM = 384

_model = SentenceTransformer(EMBED_MODEL)
splitter = SentenceSplitter(chunk_size=1000, chunk_overlap=200)

def load_and_chunk_pdf(path: str) -> list[str]:
    logger.info("Loading PDF: %s", path)
    try:
        docs = PDFReader().load_data(file=Path(path))
    except FileNotFoundError:
        logger.error("PDF not found: %s", path)
        raise
    except Exception as exc:
        logger.error("Failed to load PDF %s: %s", path, exc)
        raise RuntimeError(f"Could not load PDF '{path}'") from exc

    texts = [d.text for d in docs if getattr(d, "text", None)]
    chunks = []
    for t in texts:
        chunks.extend(splitter.split_text(t))

    chunks = [c for c in chunks if c.strip()]
    logger.info("Extracted %d chunks from %s", len(chunks), path)
    return chunks


def embed_texts(texts: list[str]) -> list[list[float]]:
    embeddings = _model.encode(texts, convert_to_numpy=True)
    return embeddings.tolist()
