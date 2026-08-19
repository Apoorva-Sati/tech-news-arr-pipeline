"""Export ai_articles_enriched.csv per assignment spec."""
import pandas as pd
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"

REQUIRED_COLS = [
    "article_id", "title", "company_name", "published_date", "category",
    "arr_usd", "summary", "url", "industry", "founded_year", "headquarters",
    "employee_count", "is_public", "stock_ticker", "company_age",
    "company_size_category",
]


def export_ai_articles(enriched):
    """
    Filter: category or industry indicates AI/ML, published 2022-2024,
    arr_usd > $50M.
    """
    df = enriched.copy()

    ai_mask = df["is_ai_related"] == True  # noqa: E712
    date_mask = df["year"].between(2022, 2024, inclusive="both")
    arr_mask = df["arr_usd"].notna() & (df["arr_usd"] > 50_000_000)

    result = df[ai_mask & date_mask & arr_mask].copy()

    # 'embedding' placeholder column (filled by bonus semantic-search step if implemented)
    if "embedding" not in result.columns:
        result["embedding"] = None

    out_cols = [c for c in REQUIRED_COLS if c in result.columns] + \
               (["embedding"] if "embedding" not in REQUIRED_COLS else [])

    result = result[REQUIRED_COLS + ["embedding"]]
    OUTPUT_DIR.mkdir(exist_ok=True)
    result.to_csv(OUTPUT_DIR / "ai_articles_enriched.csv", index=False)
    print(f"ai_articles_enriched.csv: {len(result)} rows")
    return result