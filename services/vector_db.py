"""Persistent FAISS storage with hybrid semantic and BM25-style retrieval."""

from __future__ import annotations

from collections import Counter
import json
import logging
import math
import os
from pathlib import Path
import shutil
import tempfile
import threading
from typing import Any

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from services.preprocessing import tokenize

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:  # Backward-compatible fallback for existing installations.
    from langchain_community.embeddings import HuggingFaceEmbeddings


logger = logging.getLogger(__name__)


class VectorDBManager:
    """Own the vector store lifecycle and combine semantic and lexical ranking."""

    def __init__(self, db_path: str | Path | None = None, embeddings: Any = None):
        project_root = Path(__file__).resolve().parent.parent
        self.db_path = Path(db_path or project_root / "vectorstore" / "db_faiss")
        self._embeddings = embeddings
        self.model_name = (
            f"custom:{type(embeddings).__name__}"
            if embeddings is not None
            else os.getenv(
                "RAGIFY_EMBEDDING_MODEL",
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            )
        )
        self._cached_db: FAISS | None = None
        self._lock = threading.RLock()
        logger.info("Local hybrid FAISS manager initialized.")

    @property
    def has_index(self) -> bool:
        return (self.db_path / "index.faiss").exists()

    @property
    def embeddings(self) -> Any:
        """Load the local embedding model only when indexing or searching starts."""
        if self._embeddings is None:
            self._embeddings = HuggingFaceEmbeddings(
                model_name=self.model_name,
                encode_kwargs={"normalize_embeddings": True},
            )
        return self._embeddings

    def _load_db(self) -> FAISS | None:
        if self._cached_db is not None:
            return self._cached_db
        if not self.has_index:
            return None
        try:
            loaded_db = FAISS.load_local(
                str(self.db_path),
                self.embeddings,
                allow_dangerous_deserialization=True,
            )
            config_path = self.db_path / "config.json"
            stored_model = None
            if config_path.exists():
                try:
                    stored_model = json.loads(config_path.read_text(encoding="utf-8")).get(
                        "embedding_model"
                    )
                except (OSError, json.JSONDecodeError):
                    stored_model = None

            if stored_model != self.model_name:
                documents = self._documents(loaded_db)
                logger.info(
                    "Migrating %s chunk(s) from embedding model '%s' to '%s'.",
                    len(documents),
                    stored_model or "legacy/unknown",
                    self.model_name,
                )
                self._persist_documents(documents)
            else:
                self._cached_db = loaded_db
            return self._cached_db
        except Exception as exc:
            logger.error("Failed to load FAISS database: %s", exc)
            return None

    @staticmethod
    def _documents(db: FAISS | None) -> list[Document]:
        if db is None:
            return []
        documents: list[Document] = []
        for doc_id in db.index_to_docstore_id.values():
            document = db.docstore.search(doc_id)
            if isinstance(document, Document):
                documents.append(document)
        return documents

    def _persist_documents(self, documents: list[Document]) -> None:
        if not documents:
            self._cached_db = None
            if self.db_path.exists():
                shutil.rmtree(self.db_path)
            return

        new_db = FAISS.from_documents(documents, self.embeddings)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = Path(tempfile.mkdtemp(prefix="ragify-faiss-", dir=self.db_path.parent))
        try:
            new_db.save_local(str(temp_path))
            (temp_path / "config.json").write_text(
                json.dumps({"embedding_model": self.model_name}, indent=2),
                encoding="utf-8",
            )
            if self.db_path.exists():
                shutil.rmtree(self.db_path)
            os.replace(temp_path, self.db_path)
        finally:
            if temp_path.exists():
                shutil.rmtree(temp_path)
        self._cached_db = new_db

    def _replace_file_chunks(self, chunks: list[Document], filename: str) -> None:
        """Atomically replace a file's chunks so repeat uploads do not duplicate it."""
        if not chunks:
            raise ValueError("Cannot index an empty document.")
        existing = [
            document
            for document in self._documents(self._load_db())
            if document.metadata.get("source") != filename
        ]
        for index, chunk in enumerate(chunks):
            chunk.metadata.update(
                {
                    "source": filename,
                    "chunk_index": index,
                    "is_current": bool(chunk.metadata.get("is_current", True)),
                }
            )
        self._persist_documents([*existing, *chunks])
        logger.info("Indexed %s chunk(s) from '%s'.", len(chunks), filename)

    def replace_file_chunks(self, chunks: list[Document], filename: str) -> None:
        with self._lock:
            self._replace_file_chunks(chunks, filename)

    def add_chunks(self, chunks: list[Document], filename: str = "unknown") -> None:
        """Compatibility alias; uploads replace prior chunks from the same file."""
        self.replace_file_chunks(chunks, filename)

    @staticmethod
    def _min_max(scores: list[float]) -> list[float]:
        if not scores:
            return []
        low, high = min(scores), max(scores)
        if math.isclose(low, high):
            return [1.0 if high > 0 else 0.0 for _ in scores]
        return [(score - low) / (high - low) for score in scores]

    @staticmethod
    def _bm25_scores(query_tokens: list[str], corpus: list[list[str]]) -> list[float]:
        if not query_tokens or not corpus:
            return [0.0] * len(corpus)
        average_length = sum(len(tokens) for tokens in corpus) / max(len(corpus), 1)
        document_frequency = Counter(
            token for tokens in corpus for token in set(tokens)
        )
        scores: list[float] = []
        k1, b = 1.5, 0.75
        for tokens in corpus:
            frequencies = Counter(tokens)
            score = 0.0
            for token in query_tokens:
                frequency = frequencies[token]
                if not frequency:
                    continue
                df = document_frequency[token]
                idf = math.log(1 + (len(corpus) - df + 0.5) / (df + 0.5))
                denominator = frequency + k1 * (
                    1 - b + b * len(tokens) / max(average_length, 1)
                )
                score += idf * (frequency * (k1 + 1)) / denominator
            scores.append(score)
        return scores

    def _hybrid_search(
        self,
        query_text: str,
        *,
        top_k: int = 8,
        semantic_weight: float = 0.6,
    ) -> list[dict[str, Any]]:
        db = self._load_db()
        documents = self._documents(db)
        if db is None or not documents:
            return []

        query_tokens = tokenize(query_text)
        lexical_raw = self._bm25_scores(
            query_tokens,
            [tokenize(document.page_content) for document in documents],
        )
        lexical = self._min_max(lexical_raw)

        semantic_by_key: dict[tuple[str, int, str], float] = {}
        candidate_count = min(len(documents), max(top_k * 4, 12))
        for document, distance in db.similarity_search_with_score(
            query_text, k=candidate_count
        ):
            key = (
                str(document.metadata.get("source", "")),
                int(document.metadata.get("chunk_index", -1)),
                document.page_content,
            )
            # Normalized MiniLM vectors use squared L2 distance: cosine = 1 - d/2.
            semantic_by_key[key] = max(0.0, 1.0 - float(distance) / 2.0)

        semantic_raw = [
            semantic_by_key.get(
                (
                    str(document.metadata.get("source", "")),
                    int(document.metadata.get("chunk_index", -1)),
                    document.page_content,
                ),
                0.0,
            )
            for document in documents
        ]
        semantic = self._min_max(semantic_raw)

        ranked: list[dict[str, Any]] = []
        for index, document in enumerate(documents):
            # Ignore wholly unrelated candidates instead of forcing arbitrary context.
            if lexical_raw[index] <= 0 and semantic_raw[index] < 0.15:
                continue
            score = (1 - semantic_weight) * lexical[index] + semantic_weight * semantic[index]
            if document.metadata.get("is_current", True):
                score += 0.02
            ranked.append(
                {
                    "text": document.page_content,
                    "metadata": dict(document.metadata),
                    "score": score,
                    "semantic_score": semantic_raw[index],
                    "lexical_score": lexical_raw[index],
                }
            )
        ranked.sort(key=lambda row: row["score"], reverse=True)
        return ranked[:top_k]

    def hybrid_search(
        self,
        query_text: str,
        *,
        top_k: int = 8,
        semantic_weight: float = 0.6,
    ) -> list[dict[str, Any]]:
        with self._lock:
            return self._hybrid_search(
                query_text,
                top_k=top_k,
                semantic_weight=semantic_weight,
            )

    def query(self, query_text: str, top_k: int = 5) -> dict[str, list[dict[str, Any]]]:
        """Compatibility response for older callers."""
        return {
            "matches": [
                {"metadata": {"text": row["text"], **row["metadata"]}, "score": row["score"]}
                for row in self.hybrid_search(query_text, top_k=top_k)
            ]
        }

    def delete_by_filename(self, filename: str) -> bool:
        with self._lock:
            return self._delete_by_filename(filename)

    def _delete_by_filename(self, filename: str) -> bool:
        documents = self._documents(self._load_db())
        remaining = [doc for doc in documents if doc.metadata.get("source") != filename]
        if len(remaining) == len(documents):
            return False
        self._persist_documents(remaining)
        return True

    def reset(self) -> None:
        with self._lock:
            self._persist_documents([])


vector_db = VectorDBManager()
