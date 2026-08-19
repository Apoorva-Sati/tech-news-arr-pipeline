# YipitData Data Engineering Pipeline

Turns messy tech-news articles into queryable company ARR observations + AI article dataset, with a DuckDB warehouse and semantic search on top.

## Install
```bash
pip install -r requirements.txt
```

## Run
```bash
python main.py
```
Runs: Load → Match companies → Clean/Enrich → Model tables → Export AI dataset → Build DuckDB warehouse → Generate embeddings + semantic search index.

All outputs land in `/output`.

## Outputs
- `dim_company.csv` — one row per company (grain: company_id)
- `dim_article.csv` — one row per article (grain: article_id)
- `fact_arr_observations.csv` — one row per article with valid ARR (grain: article_id; natural-key dedup, so re-running never duplicates)
- `rejected_arr_observations.csv` — articles with missing/undisclosed revenue, kept for audit
- `articles_matched.csv` / `articles_unmatched.csv` — company-name matching results
- `articles_enriched.csv` — full cleaned+enriched intermediate table, includes `top_similar_articles`
- `ai_articles_enriched.csv` — required deliverable: AI-related articles, 2022–2024, ARR > $50M, includes `embedding` and `top_similar_articles`
- `warehouse.duckdb` — DuckDB database loaded with all four modeled tables above, for direct SQL querying
- `embeddings.npy` / `embedding_article_ids.npy` — cached sentence embeddings for reuse without re-running the model

## Query patterns
- **ARR over time for a company**: filter `fact_arr_observations` by `company_id`, sort by `published_date`
- **Source article for an observation**: join `fact_arr_observations.article_id` → `dim_article`
- **Filter by date/category/industry/ARR**: join `dim_article` + `dim_company` + `fact_arr_observations`
- **Re-run without duplicates**: `fact_arr_observations` dedupes on `article_id` (natural key)

These can be run directly as SQL against `output/warehouse.duckdb` (e.g. via the DuckDB CLI, Python `duckdb` package, or a GUI client like DBeaver), or as pandas joins against the CSVs.

Example (Python):
```python
import duckdb
con = duckdb.connect("output/warehouse.duckdb", read_only=True)
con.sql("""
    SELECT published_date, arr_usd, article_id
    FROM fact_arr_observations
    WHERE company_id = 'Snowflake'
    ORDER BY published_date
""").show()
```

## Assumptions
- Ambiguous numeric dates (e.g. 01/02/2023) parsed as MM/DD/YYYY (US-style)
- Currency: EUR ×1.1, GBP ×1.27, JPY ÷150 → USD
- "Not disclosed"/N/A/blank revenue → excluded from `fact_arr_observations`, kept in `rejected_arr_observations`
- Company matching: exact → alias (e.g. AWS→Amazon Web Services) → compound ("X / Y") → fuzzy match
- Unmatched companies (Mistral AI, Cohere, xAI, Perplexity, Hugging Face — not in metadata) logged to `articles_unmatched.csv`, excluded from modeled tables

## Bonus: Semantic Search & Hybrid Querying

Implemented in `src/embeddings.py`, `src/semantic_search.py`, and `src/hybrid_search.py`.

**Embeddings**: generated from `title + summary` using `sentence-transformers` (`all-MiniLM-L6-v2`, 384-dim), normalized so cosine similarity reduces to a dot product. Cached to `output/embeddings.npy` + `output/embedding_article_ids.npy` so they don't need regenerating on every run.

**Similarity search**:
```python
from semantic_search import find_similar_articles
find_similar_articles("AI startup raises massive funding round", top_k=5)
# -> [(article_id, similarity_score), ...]
```

**Top similar articles**: for every article, the top 3 most semantically similar *other* articles are precomputed and attached as `top_similar_articles` in `articles_enriched.csv` and `ai_articles_enriched.csv`.

**Hybrid search** (SQL filters + vector similarity, backed by DuckDB):
```python
from hybrid_search import hybrid_search
hybrid_search(
    query_text="breakthrough language model",
    min_arr=500_000_000,
    ai_only=True,
    top_k=5,
)
```
This runs the SQL filter (ARR threshold, AI flag, date range, etc.) against `warehouse.duckdb` first to narrow candidates, then ranks the survivors by cosine similarity to the query — matching the assignment's example ("find AI-related articles from 2022–2024 with ARR greater than $50M, similar to a query or article").

**Note on network access**: the first run downloads the `all-MiniLM-L6-v2` model (~90MB) from Hugging Face; it's cached locally afterward, so subsequent runs work offline.