"""
Entry point: runs the full pipeline end to end.
    Load -> Match -> Clean/Enrich -> Model -> Export
Run: python main.py
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent / "src"))

from load_data import load_file
from matching_company import process_matching
from enrichment import enrich_articles
from modeling import write_tables
from export import export_ai_articles
from build_duckdb import build_duckdb
from embeddings import generate_embeddings
from semantic_search import compute_top_similar_per_article


def run_pipeline():
    print("== 1. Load ==")
    articles = load_file("tech_news.csv")
    metadata = load_file("company_metadata.json")
    print(f"Loaded {len(articles)} articles, {len(metadata)} companies")

    print("\n== 2. Match companies ==")
    matched, unmatched = process_matching(articles, metadata)
    print(f"Matched: {len(matched)}  Unmatched: {len(unmatched)}")

    print("\n== 3. Clean + Enrich ==")
    enriched = enrich_articles(matched, metadata)
    enriched.to_csv("output/articles_enriched.csv", index=False)

    print("\n== 4. Model warehouse tables ==")
    write_tables(enriched)

    print("\n== 5. Export AI article dataset ==")
    export_ai_articles(enriched)

    print("\n== 6. Build DuckDB warehouse ==")
    build_duckdb()

    print("\n== 7. Generate embeddings + semantic search index ==")
    generate_embeddings(enriched)
    top_similar = compute_top_similar_per_article(top_n=3)

    # attach top_similar_articles to enriched output for inspection
    enriched["top_similar_articles"] = enriched["article_id"].map(top_similar)
    enriched.to_csv("output/articles_enriched.csv", index=False)

    print("\nPipeline complete. See /output for all CSVs.")


if __name__ == "__main__":
    run_pipeline()