# YipitData Data Engineering Pipeline

Turns messy tech-news articles into queryable company ARR observations + AI article dataset.

## Install
```bash
pip install -r requirements.txt
```

## Run
```bash
python main.py
```
Runs: Load → Match companies → Clean/Enrich → Model tables → Export AI dataset.
All outputs land in `/output`.

## Outputs
- `dim_company.csv` — one row per company (grain: company_id)
- `dim_article.csv` — one row per article (grain: article_id)
- `fact_arr_observations.csv` — one row per article with valid ARR (grain: article_id; natural-key dedup, so re-running never duplicates)
- `rejected_arr_observations.csv` — articles with missing/undisclosed revenue, kept for audit
- `articles_matched.csv` / `articles_unmatched.csv` — company-name matching results
- `articles_enriched.csv` — full cleaned+enriched intermediate table
- `ai_articles_enriched.csv` — required deliverable: AI-related articles, 2022–2024, ARR > $50M

## Query patterns
- **ARR over time for a company**: filter `fact_arr_observations` by `company_id`, sort by `published_date`
- **Source article for an observation**: join `fact_arr_observations.article_id` → `dim_article`
- **Filter by date/category/industry/ARR**: join `dim_article` + `dim_company` + `fact_arr_observations`
- **Re-run without duplicates**: `fact_arr_observations` dedupes on `article_id` (natural key)

## Assumptions
- Ambiguous numeric dates (e.g. 01/02/2023) parsed as MM/DD/YYYY (US-style)
- Currency: EUR ×1.1, GBP ×1.27, JPY ÷150 → USD
- "Not disclosed"/N/A/blank revenue → excluded from `fact_arr_observations`, kept in `rejected_arr_observations`
- Company matching: exact → alias (e.g. AWS→Amazon Web Services) → compound ("X / Y") → fuzzy match
- Unmatched companies (Mistral AI, Cohere, xAI, Perplexity, Hugging Face — not in metadata) logged to `articles_unmatched.csv`, excluded from modeled tables

## Bonus (not implemented)
Semantic search / embeddings / DuckDB hybrid search — out of scope for this submission.