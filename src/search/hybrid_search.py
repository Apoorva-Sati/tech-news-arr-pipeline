"""SQL filters (DuckDB) + vector similarity search combined."""
from pathlib import Path
import duckdb
import numpy as np
from search.embeddings import get_model, load_embeddings

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "output" / "warehouse.duckdb"


def hybrid_search(query_text=None, query_article_id=None, min_arr=None,
                   year_from=None, year_to=None, ai_only=False, top_k=5):
    """
    Combine SQL filters (DuckDB) with semantic similarity ranking.
    Provide either query_text OR query_article_id to rank by similarity.
    Filters are optional; any combination can be applied.
    """
    article_ids, embeddings = load_embeddings()
    if embeddings is None:
        raise RuntimeError("No embeddings found. Run generate_embeddings() first.")

    # --- Step 1: SQL filter candidates ---
    con = duckdb.connect(str(DB_PATH), read_only=True)

    where_clauses = []
    if min_arr is not None:
        where_clauses.append(f"f.arr_usd >= {min_arr}")
    if year_from is not None:
        where_clauses.append(f"a.year >= {year_from}")
    if year_to is not None:
        where_clauses.append(f"a.year <= {year_to}")
    if ai_only:
        where_clauses.append("a.is_ai_related = TRUE")

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    candidates = con.sql(f"""
        SELECT f.article_id, a.title, a.published_date, f.arr_usd
        FROM fact_arr_observations f
        JOIN dim_article a USING (article_id)
        {where_sql}
    """).df()
    con.close()

    if candidates.empty:
        return candidates.assign(similarity=[])

    # --- Step 2: rank candidates by similarity ---
    id_to_idx = {aid: i for i, aid in enumerate(article_ids)}
    candidate_ids = [aid for aid in candidates["article_id"] if aid in id_to_idx]
    candidates = candidates[candidates["article_id"].isin(candidate_ids)].copy()

    idxs = [id_to_idx[aid] for aid in candidates["article_id"]]
    candidate_embeddings = embeddings[idxs]

    if query_text:
        model = get_model()
        query_vec = model.encode([query_text], normalize_embeddings=True)[0]
    elif query_article_id:
        query_vec = embeddings[id_to_idx[query_article_id]]
    else:
        # no semantic query -> just return filtered results, unranked
        candidates["similarity"] = None
        return candidates.head(top_k)

    scores = candidate_embeddings @ query_vec
    candidates["similarity"] = scores
    candidates = candidates.sort_values("similarity", ascending=False)

    return candidates.head(top_k)