import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))
from semantic_search import find_similar_articles

if __name__ == "__main__":
    results = find_similar_articles("AI startup raises massive funding round", top_k=5)
    for article_id, score in results:
        print(f"{article_id}: {score:.4f}")