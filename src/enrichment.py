import json
from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"


# -----------------------------
# Enrichment functions
# -----------------------------

def enrich_with_metadata(company_id, metadata):
    """
    Attach company metadata fields for a given company_id (company name).
    metadata: dict {company_name: {attributes...}}
    Returns dict of enrichment fields, or dict of Nones if not found.
    """
    fields = ["industry", "founded_year", "headquarters", "employee_count",
              "is_public", "stock_ticker"]

    if company_id is None or company_id not in metadata:
        return {f: None for f in fields}

    record = metadata[company_id]
    return {f: record.get(f) for f in fields}


def calculate_company_age(founded_year, published_year):
    """
    Age = published_year - founded_year.
    Returns None if either value is missing/invalid.
    """
    if founded_year is None or published_year is None:
        return None
    try:
        age = int(published_year) - int(founded_year)
        return age if age >= 0 else None  # negative age = data issue, flag as None
    except (ValueError, TypeError):
        return None


def get_size_category(employee_count):
    """
    Small: <10,000 | Medium: 10,000-30,000 | Large: >30,000
    Returns None if employee_count missing.
    """
    if employee_count is None:
        return None
    try:
        count = int(employee_count)
    except (ValueError, TypeError):
        return None

    if count < 10_000:
        return "Small"
    elif count <= 30_000:
        return "Medium"
    else:
        return "Large"


def is_ai_related(standardized_category, industry):
    """
    True if EITHER the article category OR the company industry
    signals AI/ML.
    """
    ai_signals = {"ai_ml", "ai/ml", "artificial intelligence", "machine learning"}

    category_flag = (
        str(standardized_category).strip().lower() in ai_signals
        if standardized_category else False
    )
    industry_flag = (
        str(industry).strip().lower() in ai_signals
        if industry else False
    )

    return category_flag or industry_flag


# -----------------------------
# Apply enrichment to matched articles
# -----------------------------

def enrich_articles(matched_articles, metadata):
    df = matched_articles.copy()

    # Pull metadata fields
    enriched = df["company_id"].apply(lambda cid: enrich_with_metadata(cid, metadata))
    enriched_df = pd.DataFrame(list(enriched))
    df = pd.concat([df.reset_index(drop=True), enriched_df.reset_index(drop=True)], axis=1)

    # Company age (requires clean_date already applied -> 'year' column, else use published_date year)
    if "year" in df.columns:
        published_year_col = df["year"]
    else:
        published_year_col = pd.to_datetime(df["published_date"], errors="coerce").dt.year

    df["company_age"] = [
        calculate_company_age(fy, py)
        for fy, py in zip(df["founded_year"], published_year_col)
    ]

    # Size category
    df["company_size_category"] = df["employee_count"].apply(get_size_category)

    # AI flag (requires standardized category column, e.g. 'category_standardized')
    category_col = df["category_standardized"] if "category_standardized" in df.columns else df.get("category")
    df["is_ai_related"] = [
        is_ai_related(cat, ind)
        for cat, ind in zip(category_col, df["industry"])
    ]

    return df


if __name__ == "__main__":
    matched = pd.read_csv(OUTPUT_DIR / "articles_matched.csv")

    with open(DATA_DIR / "company_metadata.json", "r", encoding="utf-8") as f:
        metadata = json.load(f)

    enriched = enrich_articles(matched, metadata)
    enriched.to_csv(OUTPUT_DIR / "articles_enriched.csv", index=False)

    print(f"Enriched {len(enriched)} articles.")
    print("\nSample rows:")
    print(enriched[["company_id", "industry", "founded_year", "employee_count",
                     "company_age", "company_size_category", "is_ai_related"]].head(5))
    print("\nSaved: output/articles_enriched.csv")