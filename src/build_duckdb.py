"""Build a DuckDB warehouse file from the modeled CSV tables in /output."""
from pathlib import Path
import duckdb

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"

TABLES = [
    "dim_company",
    "dim_article",
    "fact_arr_observations",
    "rejected_arr_observations",
]


def build_duckdb():
    db_path = OUTPUT_DIR / "warehouse.duckdb"
    con = duckdb.connect(str(db_path))

    for name in TABLES:
        csv_path = OUTPUT_DIR / f"{name}.csv"
        con.execute(
            f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM read_csv_auto('{csv_path}')"
        )
        print(f"Loaded {name} into DuckDB")

    con.close()
    print(f"DuckDB warehouse written to {db_path}")


if __name__ == "__main__":
    build_duckdb()