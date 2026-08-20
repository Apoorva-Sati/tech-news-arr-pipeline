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