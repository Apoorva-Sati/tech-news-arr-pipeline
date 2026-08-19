"""Build warehouse-style tables: dim_company, fact_arr_observation, bridge to source articles."""
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"


def build_dim_company(enriched):
    """One row per company_id (grain: company)."""
    cols = ["company_id", "industry", "founded_year", "headquarters",
            "employee_count", "is_public", "stock_ticker", "company_size_category"]
    dim = enriched[cols].drop_duplicates(subset="company_id").reset_index(drop=True)
    return dim


def build_fact_arr_observations(enriched):
    """
    Grain: one row per article_id that has a valid arr_usd.
    Natural key = article_id -> re-running the pipeline never duplicates rows
    (dedup by article_id, not surrogate autoincrement).
    """
    valid = enriched[enriched["arr_usd"].notna()].copy()
    fact = valid[[
        "article_id", "company_id", "published_date", "year", "quarter", "month",
        "arr_usd", "revenue"  # revenue = original raw string, kept for audit/lineage
    ]].rename(columns={"revenue": "raw_revenue_string"})
    fact = fact.drop_duplicates(subset="article_id").reset_index(drop=True)
    return fact


def build_dim_article(enriched):
    """Grain: one row per article_id. Links fact table back to source (title/url/summary)."""
    cols = ["article_id", "title", "company_id", "published_date", "year", "quarter",
            "month", "category", "category_standardized", "is_ai_related",
            "summary", "url", "author", "match_type"]
    cols = [c for c in cols if c in enriched.columns]
    return enriched[cols].drop_duplicates(subset="article_id").reset_index(drop=True)


def build_rejected_arr(enriched):
    """Articles with no valid ARR (missing/undisclosed) — kept for audit, excluded from fact table."""
    invalid = enriched[enriched["arr_usd"].isna()].copy()
    return invalid[["article_id", "company_id", "revenue", "published_date"]].rename(
        columns={"revenue": "raw_revenue_string"}
    )


def write_tables(enriched):
    OUTPUT_DIR.mkdir(exist_ok=True)
    dim_company = build_dim_company(enriched)
    fact_arr = build_fact_arr_observations(enriched)
    dim_article = build_dim_article(enriched)
    rejected = build_rejected_arr(enriched)

    dim_company.to_csv(OUTPUT_DIR / "dim_company.csv", index=False)
    fact_arr.to_csv(OUTPUT_DIR / "fact_arr_observations.csv", index=False)
    dim_article.to_csv(OUTPUT_DIR / "dim_article.csv", index=False)
    rejected.to_csv(OUTPUT_DIR / "rejected_arr_observations.csv", index=False)

    print(f"dim_company: {len(dim_company)} rows")
    print(f"fact_arr_observations: {len(fact_arr)} rows (grain = article_id, dedup on rerun)")
    print(f"dim_article: {len(dim_article)} rows")
    print(f"rejected_arr_observations: {len(rejected)} rows")

    return dim_company, fact_arr, dim_article, rejected