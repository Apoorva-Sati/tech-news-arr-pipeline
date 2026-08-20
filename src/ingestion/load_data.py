import pandas as pd
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"        

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