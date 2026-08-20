"""Generate sentence embeddings for article title + summary."""
from pathlib import Path
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "output"

MODEL_NAME = "all-MiniLM-L6-v2"
_model = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def generate_embeddings(df):
    """
    df must have 'article_id', 'title', 'summary'.
    Returns (article_ids: list, embeddings: np.ndarray of shape (n, 384))
    Also saves embeddings.npy + article_ids.npy to /output for reuse.
    """
    model = get_model()
    text = (df["title"].fillna("") + " " + df["summary"].fillna("")).tolist()
    embeddings = model.encode(text, show_progress_bar=True, normalize_embeddings=True)

    article_ids = df["article_id"].tolist()

    OUTPUT_DIR.mkdir(exist_ok=True)
    np.save(OUTPUT_DIR / "embeddings.npy", embeddings)
    np.save(OUTPUT_DIR / "embedding_article_ids.npy", np.array(article_ids))

    return article_ids, embeddings


def load_embeddings():
    """Load previously saved embeddings. Returns (article_ids, embeddings) or (None, None)."""
    ids_path = OUTPUT_DIR / "embedding_article_ids.npy"
    emb_path = OUTPUT_DIR / "embeddings.npy"
    if not ids_path.exists() or not emb_path.exists():
        return None, None
    article_ids = np.load(ids_path, allow_pickle=True).tolist()
    embeddings = np.load(emb_path)
    return article_ids, embeddings