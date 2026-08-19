import pandas as pd
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

def load_file(filename):
    path = DATA_DIR / filename
    ext = path.suffix.lower()

    if ext == ".csv":
        return pd.read_csv(path)
    elif ext == ".json":
        with open(path, "r") as f:
            return json.load(f)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

if __name__ == "__main__":
    articles = load_file("tech_news.csv")
    print("Articles shape:", articles.shape)
    print(articles.head())

    metadata = load_file("company_metadata.json")
    print("\nMetadata type:", type(metadata))
    if isinstance(metadata, list):
        print("Metadata count:", len(metadata))
        print(metadata[0])
    elif isinstance(metadata, dict):
        print("Metadata keys:", list(metadata.keys()))