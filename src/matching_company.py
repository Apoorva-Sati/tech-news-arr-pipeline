import re
import difflib
from pathlib import Path

import pandas as pd


# -----------------------------
# Paths
# -----------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# -----------------------------
# Normalization helpers
# -----------------------------

SUFFIXES = [
    "inc.", "inc", "corporation", "corp.", "corp", "technologies",
    "technology", "tech", "research", "llc", "ltd", "ltd.", "co.",
    "company", "group", "labs", "lab"
]

# alias keys are POST-suffix-stripping normalized forms
ALIASES = {
    "azure": "microsoft",
    "microsoftazure": "microsoft",
    "deepmind": "googledeepmind",
    "facebookai": "metaai",
    "aws": "amazonwebservices",
}


def strip_parenthetical(text):
    return re.sub(r"\(.*?\)", "", text)


def strip_suffixes(text):
    words = text.split()
    while words and words[-1].lower().strip(".") in SUFFIXES:
        words.pop()
    return " ".join(words)


def normalize_company_name(name):
    """Normalize company name ONLY for comparison. Does not modify original."""
    if pd.isna(name) or name is None:
        return None
    text = strip_parenthetical(str(name))
    text = strip_suffixes(text)
    normalized = "".join(text.lower().split())
    return normalized if normalized else None


# -----------------------------
# Build lookup structures from metadata
# -----------------------------

def build_metadata_lookup(metadata):
    """
    metadata is a dict: {company_name: {attributes...}}
    Returns:
    - normalized_to_id: dict {normalized_name: company_name}
    - normalized_names: list of normalized names (for fuzzy matching)
    """
    normalized_to_id = {}

    for company_name in metadata.keys():
        norm = normalize_company_name(company_name)
        if norm:
            normalized_to_id[norm] = company_name

    normalized_names = list(normalized_to_id.keys())
    return normalized_to_id, normalized_names


# -----------------------------
# Company matching
# -----------------------------

def match_company(article_company_name, normalized_to_id, normalized_names, cutoff=0.80):
    """
    Returns (company_id, match_type) where match_type is
    'exact', 'alias', 'compound-*', 'fuzzy', or None if unmatched.
    """
    norm = normalize_company_name(article_company_name)
    if not norm:
        return None, None

    # 1. Exact match
    if norm in normalized_to_id:
        return normalized_to_id[norm], "exact"

    # 2. Alias match
    alias_target = ALIASES.get(norm)
    if alias_target and alias_target in normalized_to_id:
        return normalized_to_id[alias_target], "alias"

    # 3. Compound names, e.g. "The Boring Company / SpaceX"
    if "/" in str(article_company_name):
        for part in str(article_company_name).split("/"):
            result, mtype = match_company(part.strip(), normalized_to_id, normalized_names, cutoff)
            if result:
                return result, "compound-" + mtype

    # 4. Fuzzy match
    close = difflib.get_close_matches(norm, normalized_names, n=1, cutoff=cutoff)
    if close:
        return normalized_to_id[close[0]], "fuzzy"

    return None, None


# -----------------------------
# Process matching
# -----------------------------

def process_matching(articles, metadata):
    normalized_to_id, normalized_names = build_metadata_lookup(metadata)

    result = articles.copy()

    matches = result["company_name"].apply(
        lambda name: match_company(name, normalized_to_id, normalized_names)
    )
    result["company_id"] = matches.apply(lambda x: x[0])
    result["match_type"] = matches.apply(lambda x: x[1])

    matched = result[result["company_id"].notna()].copy()
    unmatched = result[result["company_id"].isna()].copy()

    matched.to_csv(OUTPUT_DIR / "articles_matched.csv", index=False)
    unmatched.to_csv(OUTPUT_DIR / "articles_unmatched.csv", index=False)

    return matched, unmatched
