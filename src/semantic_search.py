"""Cosine similarity search over article embeddings."""
import numpy as np
from embeddings import get_model, load_embeddings


def cosine_similarity(query_vec, matrix):
    """query_vec: (d,), matrix: (n, d). Both assumed normalized -> dot product = cosine sim."""
    return matrix @ query_vec


def find_similar_articles(query_text, top_k=5):
    """
    Returns list of (article_id, similarity_score), sorted descending.
    """
    article_ids, embeddings = load_embeddings()
    if embeddings is None:
        raise RuntimeError("No embeddings found. Run generate_embeddings() first.")

    model = get_model()
    query_vec = model.encode([query_text], normalize_embeddings=True)[0]

    scores = cosine_similarity(query_vec, embeddings)
    top_idx = np.argsort(-scores)[:top_k]

    return [(article_ids[i], float(scores[i])) for i in top_idx]


def compute_top_similar_per_article(top_n=3):
    """
    For every article, find the top_n most similar OTHER articles.
    Returns dict: {article_id: [similar_id_1, similar_id_2, similar_id_3]}
    """
    article_ids, embeddings = load_embeddings()
    if embeddings is None:
        raise RuntimeError("No embeddings found. Run generate_embeddings() first.")

    sim_matrix = embeddings @ embeddings.T  # (n, n) cosine sim since normalized
    np.fill_diagonal(sim_matrix, -np.inf)   # exclude self

    result = {}
    for i, aid in enumerate(article_ids):
        top_idx = np.argsort(-sim_matrix[i])[:top_n]
        result[aid] = [article_ids[j] for j in top_idx]

    return result