import numpy as np


def mmr_rerank(
    query_embedding:  list,
    chunks:           list[dict],
    top_k:            int   = 3,
    lambda_mult:      float = 0.7,
) -> list[dict]:
    if not chunks:
        return []

    if len(chunks) <= top_k:
        print(f"[MMR] Only {len(chunks)} candidates — returning all")
        return chunks

    print(f"[MMR] Applying MMR: {len(chunks)} candidates → top {top_k} "
          f"(lambda_mult={lambda_mult})")

    parsed_query = _parse_vector(query_embedding)

    if not parsed_query:
        print(f"[MMR] Could not parse query embedding — "
              f"returning top {top_k} by RRF score")
        return chunks[:top_k]

    chunks_with_embeddings = []
    chunks_without_embeddings = []

    for chunk in chunks:
        raw_vec = chunk.get("embedding")
        parsed  = _parse_vector(raw_vec)

        if parsed:
            chunk["_parsed_embedding"] = parsed
            chunks_with_embeddings.append(chunk)
        else:
            chunks_without_embeddings.append(chunk)

    if chunks_without_embeddings:
        print(f"[MMR] {len(chunks_without_embeddings)} chunks have no embedding — "
              f"skipping them for MMR diversity calculation")

    if not chunks_with_embeddings:
        print(f"[MMR] No chunks have embeddings — "
              f"returning top {top_k} by RRF score")
        return chunks[:top_k]

    selected_indices  = []
    remaining_indices = list(range(len(chunks_with_embeddings)))

    for iteration in range(min(top_k, len(chunks_with_embeddings))):
        best_index = None
        best_score = float("-inf")

        for idx in remaining_indices:
            chunk_vec = chunks_with_embeddings[idx]["_parsed_embedding"]

            relevance = cosine_similarity(parsed_query, chunk_vec)

            if selected_indices:
                max_sim_to_selected = max(
                    cosine_similarity(
                        chunk_vec,
                        chunks_with_embeddings[s]["_parsed_embedding"]
                    )
                    for s in selected_indices
                )
            else:
                max_sim_to_selected = 0.0

            mmr_score = (
                lambda_mult * relevance
                - (1 - lambda_mult) * max_sim_to_selected
            )

            if mmr_score > best_score:
                best_score = mmr_score
                best_index = idx

        if best_index is not None:
            selected_indices.append(best_index)
            remaining_indices.remove(best_index)

            page = chunks_with_embeddings[best_index]["metadata"].get(
                "page_number", "?"
            )
            print(f"[MMR] Iteration {iteration + 1}: "
                  f"selected chunk index {best_index} "
                  f"(score={best_score:.4f}, page={page})")

    selected = [chunks_with_embeddings[i] for i in selected_indices]

    for chunk in selected:
        chunk.pop("_parsed_embedding", None)

    print(f"[MMR] Complete: selected {len(selected)} chunks from pages "
          f"{[c['metadata'].get('page_number', '?') for c in selected]}")

    return selected


def cosine_similarity(vec_a, vec_b) -> float:
    a = np.array(_parse_vector(vec_a), dtype=np.float32)
    b = np.array(_parse_vector(vec_b), dtype=np.float32)

    if a.size == 0 or b.size == 0 or len(a) != len(b):
        return 0.0

    return float(np.dot(a, b))


def _parse_vector(vec) -> list[float]:
    if vec is None:
        return []

    if isinstance(vec, list):
        if not vec:
            return []
        try:
            return [float(x) for x in vec]
        except (ValueError, TypeError):
            return []

    if isinstance(vec, str):
        vec = vec.strip()
        if not vec:
            return []

        if vec.startswith("["):
            vec = vec[1:]
        if vec.endswith("]"):
            vec = vec[:-1]

        if not vec.strip():
            return []

        try:
            return [float(x.strip()) for x in vec.split(",") if x.strip()]
        except (ValueError, TypeError):
            return []

    print(f"[MMR] Warning: unexpected vector type {type(vec)} — returning []")
    return []
