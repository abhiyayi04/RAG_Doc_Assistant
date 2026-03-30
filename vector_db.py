import logging
from functools import lru_cache
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

logger = logging.getLogger("rag.vector_db")

class QdrantStorage:
    def __init__(self, url="http://localhost:6333", collection="docs", dim=384):
        try:
            self.client = QdrantClient(url=url, timeout=30)
            self.collection = collection
            if not self.client.collection_exists(self.collection):
                self.client.create_collection(
                    collection_name=self.collection,
                    vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
                )
                logger.info("Created Qdrant collection: %s", self.collection)
        except Exception as exc:
            logger.error("Qdrant connection failed: %s", exc)
            raise RuntimeError("Could not connect to Qdrant") from exc

    def upsert(self, ids: list, vectors: list, payloads: list) -> None:
        if not (len(ids) == len(vectors) == len(payloads)):
            raise ValueError(
                f"Length mismatch: ids={len(ids)}, vectors={len(vectors)}, payloads={len(payloads)}"
            )
        try:
            points = [PointStruct(id=ids[i], vector=vectors[i], payload=payloads[i]) for i in range(len(ids))]
            self.client.upsert(self.collection, points=points)
            logger.info("Upserted %d points to collection '%s'", len(ids), self.collection)
        except Exception as exc:
            logger.error("Upsert failed: %s", exc)
            raise

    def search(self, query_vector, top_k: int = 5, score_threshold: float = 0.3):
        result_obj = self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            with_payload=True,
            limit=top_k,
            score_threshold=score_threshold,
        )

        results = result_obj.points

        contexts = []
        sources = set()

        for r in results:
            payload = getattr(r, "payload", None) or {}
            text = payload.get("text", "")
            source = payload.get("source", "")

            if text:
                contexts.append(text)
                sources.add(source)

        if not contexts:
            logger.warning("All results filtered by score_threshold=%.2f", score_threshold)

        return {"contexts": contexts, "sources": list(sources)}


@lru_cache(maxsize=1)
def get_storage(url: str = "http://localhost:6333", collection: str = "docs", dim: int = 384) -> QdrantStorage:
    return QdrantStorage(url=url, collection=collection, dim=dim)
