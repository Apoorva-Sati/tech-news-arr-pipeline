"""Export ai_articles_enriched.csv per assignment spec."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"

REQUIRED_COLS = [
    "article_id", "title", "company_name", "published_date", "category",
    "arr_usd", "summary", "url", "industry", "founded_year", "headquarters",
    "employee_count", "is_public", "stock_ticker", "company_age",
    "company_size_category",
]


def export_ai_articles(enriched):
    from embeddings import load_embeddings
    df = enriched.copy()

    ai_mask = df["is_ai_related"] == True  # noqa: E712
    date_mask = df["year"].between(2022, 2024, inclusive="both")
    arr_mask = df["arr_usd"].notna() & (df["arr_usd"] > 50_000_000)

    result = df[ai_mask & date_mask & arr_mask].copy()

    # real embeddings, keyed by article_id
    article_ids, embeddings = load_embeddings()
    if embeddings is not None:
        id_to_vec = dict(zip(article_ids, embeddings.tolist()))
        result["embedding"] = result["article_id"].map(id_to_vec)
    else:
        result["embedding"] = None

    cols = REQUIRED_COLS + ["embedding"]
    if "top_similar_articles" in df.columns:
        cols.append("top_similar_articles")

    result = result[cols]
    OUTPUT_DIR.mkdir(exist_ok=True)
    result.to_csv(OUTPUT_DIR / "ai_articles_enriched.csv", index=False)
    print(f"ai_articles_enriched.csv: {len(result)} rows")
    return result