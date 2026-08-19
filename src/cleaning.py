import re
import json
import pandas as pd
from datetime import datetime

def clean_revenue(raw_value):

    if raw_value is None:
        return None

    text = str(raw_value).strip()

    if text == "" or text.lower() in ("n/a", "not disclosed"):
        return None

    range_match = re.findall(r'[\$€£¥]?\s?([\d,\.]+)\s?(B|M|billion|million)?', text, re.IGNORECASE)
    if "-" in text and len(range_match) >= 2:
        low = _parse_amount(range_match[0][0], range_match[0][1], text)
        high = _parse_amount(range_match[1][0], range_match[1][1], text)
        if low is None or high is None:
            return None
        return int((low + high) / 2)

    single_match = re.search(
        r'([\$€£¥]?)\s?([\d,\.]+)\s?(B|M|billion|million)?\s?(USD|EUR|GBP|JPY)?',
        text, re.IGNORECASE
    )
    if not single_match:
        return None

    symbol, number, magnitude, currency_word = single_match.groups()
    amount = _parse_amount(number, magnitude, text)
    if amount is None:
        return None

    # Determine currency
    currency = _detect_currency(symbol, currency_word)
    return int(_convert_to_usd(amount, currency))


def _parse_amount(number_str, magnitude, full_text):
    """Convert number string + magnitude (B/M/billion/million) into a float."""
    try:
        number = float(number_str.replace(",", ""))
    except (ValueError, AttributeError):
        return None

    if magnitude:
        magnitude = magnitude.lower()
        if magnitude in ("b", "billion"):
            number *= 1_000_000_000
        elif magnitude in ("m", "million"):
            number *= 1_000_000

    return number


def _detect_currency(symbol, currency_word):
    """Determine currency code from symbol or word."""
    if symbol == "€" or (currency_word and currency_word.upper() == "EUR"):
        return "EUR"
    if symbol == "£" or (currency_word and currency_word.upper() == "GBP"):
        return "GBP"
    if symbol == "¥" or (currency_word and currency_word.upper() == "JPY"):
        return "JPY"
    return "USD"  # default


def _convert_to_usd(amount, currency):
    """Apply fixed conversion rates to USD."""
    rates = {
        "EUR": 1.1,
        "GBP": 1.27,
        "JPY": 1 / 150,
        "USD": 1.0,
    }
    return amount * rates.get(currency, 1.0)

def clean_date(raw_date):
    """
    Normalize published_date to datetime.
    Returns dict: {date, year, quarter, month} or None if invalid/missing.

    Assumption for ambiguous numeric dates (e.g. 01/02/2023):
    Treated as MM/DD/YYYY (US format) by default, since source data
    is assumed US-centric unless day > 12 clearly indicates DD/MM/YYYY.
    """
    if raw_date is None:
        return None

    text = str(raw_date).strip()
    if text == "" or text.lower() in ("n/a", "na", "null", "none", "not disclosed"):
        return None

    # Try formats in order: ISO, US, EU
    formats_to_try = [
        "%Y-%m-%d",      # ISO: 2023-05-12
        "%Y/%m/%d",      # ISO variant
        "%m/%d/%Y",      # US: 05/12/2023
        "%d/%m/%Y",      # EU: 12/05/2023
        "%m-%d-%Y",      # US variant
        "%d-%m-%Y",      # EU variant
        "%B %d, %Y",     # e.g. May 12, 2023
        "%d %B %Y",      # e.g. 12 May 2023
    ]

    parsed = None
    for fmt in formats_to_try:
        try:
            parsed = datetime.strptime(text, fmt)
            break
        except ValueError:
            continue

    if parsed is None:
        return None

    year = parsed.year
    month = parsed.month
    quarter = (month - 1) // 3 + 1

    return {
        "date": parsed,
        "year": year,
        "quarter": quarter,
        "month": month,
    }

def standardize_category(raw_category):
    """
    Normalize article categories into a consistent taxonomy.
    """

    if raw_category is None:
        return None

    category = str(raw_category).strip().lower()

    if category == "":
        return None

    category_mapping = {

        # AI / Machine Learning
        "ai & ml": "Artificial Intelligence",
        "ai/ml": "Artificial Intelligence",
        "artificial intelligence": "Artificial Intelligence",
        "machine learning": "Artificial Intelligence",

        #Big Data
        "big data": "Big Data",

        # Cloud
        "cloud": "Cloud Computing",
        "cloud computing": "Cloud Computing",
        "cloud services": "Cloud Services",

        # Cybersecurity
        "cybersecurity": "Cyber Security",
        "security": "Cyber Security",
        "infosec": "Cyber Security",

        #Data / Analytics
        "analytics": "Data Analytics",
        "data analytics": "Data Analytics",

        # Software
        "enterprise software": "Software",
        "software": "Software",
        "saas": "Software",

        # Fintech
        "fintech": "Financial Technology",
        "financial technology": "Financial Technology",
        "finance": "Financial Technology",
    }

    return category_mapping.get(category, "Other")