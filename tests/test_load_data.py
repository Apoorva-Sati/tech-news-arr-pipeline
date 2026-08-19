import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from load_data import load_file

def test_load_csv():
    df = load_file("tech_news.csv")
    assert df.shape[0] == 750

def test_load_json():
    data = load_file("company_metadata.json")
    assert data is not None