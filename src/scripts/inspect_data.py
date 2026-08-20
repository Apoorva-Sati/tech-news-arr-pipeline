from ingestion.load_data import load_file

def inspect_articles():
    df = load_file("tech_news.csv")
    print("=== ARTICLE COLUMNS & TYPES ===")
    print(df.dtypes)
    print("\n=== SAMPLE ROW ===")
    print(df.iloc[0])

def inspect_metadata():
    data = load_file("company_metadata.json")
    print("\n=== METADATA STRUCTURE ===")
    if isinstance(data, list):
        print(f"Type: list, count: {len(data)}")
        print("Sample record keys:", list(data[0].keys()))
        print("Sample record:", data[0])
    elif isinstance(data, dict):
        print(f"Type: dict, keys: {list(data.keys())}")
        first_key = list(data.keys())[0]
        print(f"Sample value for '{first_key}':", data[first_key])

if __name__ == "__main__":
    inspect_articles()
    inspect_metadata()