import threading

import numpy as np
from fastembed import TextEmbedding

MODEL_ID     = "BAAI/bge-large-en-v1.5"
EMBEDDING_DIMS = 1024

_model: TextEmbedding | None = None
_lock = threading.Lock()


def _get_model() -> TextEmbedding:
    global _model

    if _model is None:
        with _lock:
            if _model is None:
                print(f"[Embedder] Loading local model {MODEL_ID}")
                _model = TextEmbedding(MODEL_ID)
                print(f"[Embedder] Model loaded ({EMBEDDING_DIMS} dims)")

    return _model


def embed_chunks(chunks: list[dict]) -> list[dict]:
    if not chunks:
        raise ValueError("[Embedder] Received empty chunks list")

    print(f"[Embedder] Embedding {len(chunks)} chunks "
          f"using {MODEL_ID} ({EMBEDDING_DIMS} dims)")

    embeddings = embed_texts([c["content"] for c in chunks])

    for chunk, embedding in zip(chunks, embeddings):
        chunk["embedding"] = embedding

    sample_dim = len(chunks[0]["embedding"])
    if sample_dim != EMBEDDING_DIMS:
        raise ValueError(
            f"[Embedder] Expected {EMBEDDING_DIMS} dims, got {sample_dim}. "
            f"Check model configuration."
        )

    print(f"[Embedder] Complete: {len(chunks)} chunks embedded "
          f"({EMBEDDING_DIMS} dimensions each)")

    return chunks


def embed_texts(texts: list[str]) -> list[list[float]]:
    print(f"[Embedder] Embedding {len(texts)} texts via {MODEL_ID}")

    model = _get_model()

    embeddings = []
    for i, vec in enumerate(model.embed(texts)):
        arr = np.asarray(vec, dtype=np.float32)
        norm = float(np.linalg.norm(arr))
        if norm > 0:
            arr = arr / norm
        embeddings.append(arr.tolist())

        if (i + 1) % 50 == 0:
            print(f"[Embedder] Progress: {i + 1}/{len(texts)} texts")

    return embeddings


def embed_single_text(text: str) -> list[float]:
    return embed_texts([text])[0]


def _embed_single(text: str) -> list[float]:
    return embed_single_text(text[:8000])
