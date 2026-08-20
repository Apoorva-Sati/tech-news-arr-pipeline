# Data Architecture Document — tech-news-arr-pipeline

## 1. Overview

**Goal:** Turn messy synthetic tech-news articles into (a) an auditable, queryable model of company ARR observations over time, and (b) a semantic search index over the same articles, without losing lineage back to source records.

**Assumptions:**
- Dataset is small (750 articles, 20 metadata companies) and static for this exercise, but the design should tolerate new article batches arriving repeatedly (not a one-time load).
- "Revenue" in the source is always interpreted as a **reported ARR observation** as of `published_date`, not verified financial fact — outputs must carry that caveat.
- Single-machine, single-user execution is acceptable now; the architecture should still map cleanly onto a hosted warehouse if scaled.

## 2. Architecture — Logical Flow

```
tech_news.csv ─┐
                ├─▶ Load ─▶ Match (company_id) ─▶ Split matched/unmatched
company_metadata.json ─┘                              │
                                                        ▼
                                          Clean + Enrich (ARR, dates, category, metadata)
                                                        │
                              ┌─────────────────────────┼─────────────────────────┐
                              ▼                         ▼                         ▼
                     dim_company.csv          fact_arr_observations.csv    dim_article.csv
                     (+ rejected_arr_observations.csv)
                                                        │
                              ┌─────────────────────────┼─────────────────────────┐
                              ▼                         ▼                         ▼
                  ai_articles_enriched.csv     warehouse.duckdb          embeddings.npy
                  (filtered export)            (per-table load)          + hybrid_search / semantic_search
```

## 3. Components

| Component | Purpose | Technology |
|---|---|---|
| Ingestion | Load raw CSV/JSON by extension | `src/ingestion/load_data.py` (pandas, json) |
| Matching | Resolve article `company_name` → canonical `company_id` | `src/matching/matching_company.py` — exact → alias → compound-split → difflib fuzzy (0.85 cutoff) |
| Cleaning | Parse revenue, dates, category into structured values | `src/cleaning/cleaning.py` |
| Enrichment | Attach metadata, derive `company_age`, `company_size_category`, `is_ai_related` | `src/matching/enrichment.py` |
| Modeling | Materialize warehouse-style tables | `src/modeling/modeling.py` |
| Export | Filtered `ai_articles_enriched.csv` deliverable | `src/export/export.py` |
| Warehouse load | Load modeled CSVs into a queryable local store | `src/export/build_duckdb.py` (DuckDB) |
| Embeddings | Title+summary → 384-dim vectors | `src/search/embeddings.py` (sentence-transformers, all-MiniLM-L6-v2) |
| Semantic/Hybrid search | Cosine similarity; SQL filter + similarity ranking | `src/search/semantic_search.py`, `src/search/hybrid_search.py` |
| Orchestration | Runs all stages in order | `main.py` |
| Tests | Unit coverage on load/clean/match/model | `tests/` (pytest) |

## 4. Data Model

**Grain-first design**, bronze→silver→gold implicit in stage naming:

| Table | Grain | Key columns |
|---|---|---|
| `dim_company` | one row per `company_id` | company_id (PK), industry, founded_year, headquarters, employee_count, is_public, stock_ticker, company_size_category |
| `dim_article` | one row per `article_id` | article_id (PK), company_id (FK), title, published_date, year/quarter/month, category, category_standardized, is_ai_related, summary, url, match_type |
| `fact_arr_observations` | one row per `article_id` **with a valid parsed ARR** | article_id (PK + FK to dim_article), company_id (FK), arr_usd, raw_revenue_string, published_date/year/quarter/month |
| `rejected_arr_observations` | one row per article with missing/undisclosed revenue | article_id, company_id, raw_revenue_string, published_date — audit trail, excluded from fact table |
| `articles_unmatched.csv` | articles whose company couldn't be resolved to metadata | excluded upstream of modeling |

**Relationships:** `fact_arr_observations.article_id` → `dim_article.article_id` (source lineage); `dim_article.company_id` / `fact_arr_observations.company_id` → `dim_company.company_id`.

**Idempotency:** `article_id` is a natural key (not a surrogate autoincrement), so `drop_duplicates(subset="article_id")` on every table means re-running the pipeline on the same input never creates duplicate rows — this satisfies the "re-run without duplicating" requirement without needing a hash-based surrogate key, since one article always yields at most one ARR observation.

## 5. Data Flow

1. **Load** raw CSV/JSON as-is (no transformation).
2. **Match** each article's `company_name` to a `company_id` in metadata; split into matched/unmatched, both persisted for audit.
3. **Clean** matched articles: `clean_revenue` (currency/magnitude/range parsing → USD int), `clean_date` (multi-format → year/quarter/month), `standardize_category` (taxonomy mapping).
4. **Enrich** with metadata fields, `company_age`, `company_size_category`, `is_ai_related`.
5. **Model**: split into `dim_company`, `dim_article`, `fact_arr_observations` (valid ARR only), `rejected_arr_observations` (invalid/missing ARR, kept for audit — never silently dropped).
6. **Export** `ai_articles_enriched.csv` (AI category/industry AND 2022–2024 AND ARR > $50M) plus embeddings and `top_similar_articles`.
7. **Load into DuckDB** for SQL-based hybrid querying.

## 6. Storage Strategy

- **At rest:** flat CSV files in `/output`, one per modeled table — simplest audit format, diffable, git-ignored to avoid bloating the repo.
- **Query layer:** DuckDB file (`warehouse.duckdb`) built by reading the same CSVs — gives SQL access without a server, and keeps CSVs as the source of truth for the tables.
- **Vector storage:** `embeddings.npy` + `embedding_article_ids.npy` (parallel arrays) for reuse across runs; avoids re-encoding 750 articles every invocation.
- **Partitioning/retention:** not needed at this scale; if scaled, `fact_arr_observations` would partition by `year`/`quarter` and retain all history (ARR is a time series, never overwritten in place — see §10).

## 7. Data Processing

- **Mode:** batch, single local run via `python main.py`; no streaming component.
- **Transformations:** regex-based revenue parsing (currency detection, magnitude suffix, range midpoint), multi-format date parsing with explicit ambiguous-date assumption (documented in code + README), category taxonomy dictionary, company-name normalization + fuzzy matching.
- **Idempotency mechanism:** natural-key dedup (`article_id`) at every table-build step, so reprocessing the same batch is a no-op on row count.
- **Backfill mechanism (design intent for growth):** new article batches would be loaded, matched, cleaned, and **appended** rather than replacing existing `fact_arr_observations` rows for different `article_id`s — each article is an independent observation, so backfills are naturally additive; only re-ingesting the *same* `article_id` with corrected data would need an explicit upsert (currently: rerun regenerates the full table from the full matched set, which is correct for local batch scale but would need incremental upsert logic at production scale — see Open Questions).

## 8. Security & Governance

- Data is synthetic and non-sensitive; no PII, no compliance requirements for this exercise.
- **Lineage:** every fact row carries `raw_revenue_string` (original text) and links back via `article_id`/`url` to the source article — satisfies "never treat ARR as company master data without source lineage."
- **Data quality gates:** invalid/undisclosed ARR routed to `rejected_arr_observations` rather than coerced into `fact_arr_observations`; unmatched companies routed to `articles_unmatched.csv` rather than silently joined.
- **Governance gap (local exercise):** no schema versioning, no access control — acceptable locally, called out below for a production posture.

## 9. Reliability & Scalability

- **Reliability:** deterministic parsing functions (pure functions, no external I/O in cleaning/matching) make outputs reproducible and unit-testable in isolation.
- **Failure isolation:** a single bad revenue string or unparseable date doesn't fail the run — it degrades to `None` and is captured for audit rather than raising.
- **Scalability path:** the pandas/local-file design is a stand-in for what would be a warehouse job (e.g., dbt models on Snowflake/BigQuery) at real scale; DuckDB is the natural bridge since the SQL used in `hybrid_search.py` would port with minimal changes.
- **Monitoring (not implemented, noted for scale):** row-count deltas per stage (matched vs. unmatched, valid vs. rejected ARR) are already printed to stdout each run — this is the seed of a data-quality dashboard.

## 10. Key Decisions & Trade-offs

| Decision | Rationale | Trade-off |
|---|---|---|
| Natural-key (`article_id`) dedup instead of surrogate/hash `observation_id` | Simpler, and one article = at most one ARR observation, so it's sufficient | Won't support multiple ARR mentions within a single article without a schema change |
| CSV as source of truth, DuckDB as derived query layer | Keeps outputs human-diffable and matches the assignment's "CSV required, DuckDB optional" framing | Two representations of the same data must stay in sync (handled by DuckDB being rebuilt from CSV every run) |
| Regex + difflib fuzzy matching (0.85 cutoff) over an LLM/embedding-based entity resolver | Fast, deterministic, no external dependency for a small (20-company) lookup | Won't generalize as gracefully to a much larger, noisier company universe |
| Rejecting invalid ARR into a separate table instead of imputing | Assignment explicitly forbids treating missing ARR as valid | Reduces `fact_arr_observations` row count vs. total article count — expected and documented |
| Local sentence-transformers embeddings, normalized for dot-product similarity | Matches assignment's suggested model; avoids external API dependency | First run requires network access to download the model (~90MB), noted in README |