"""
Central configuration for the StatsWales 2 → StatsWales 3 redirect system.

Contains the hardcoded category-to-topic mapping from the service owner,
SW3 URL templates, code prefix mappings, and matching thresholds.
"""

# SW3 base URLs — English and Welsh
SW3_EN_BASE = "https://stats.gov.wales"
SW3_CY_BASE = "https://stats.llyw.cymru"
SW3_EN_HOME = f"{SW3_EN_BASE}/en-GB"
SW3_CY_HOME = f"{SW3_CY_BASE}/cy-GB"
SW3_API_BASE = "https://api.stats.gov.wales/v1"

# Legacy: used by build_mapping.py (English mapping)
SW3_BASE_URL = SW3_EN_BASE
SW3_HOME = SW3_EN_HOME

# SW2 domain → SW3 locale mapping
DOMAIN_LOCALE = {
    "statswales.gov.wales": {"base": SW3_EN_BASE, "home": SW3_EN_HOME, "locale": "en-GB"},
    "statscymru.llyw.cymru": {"base": SW3_CY_BASE, "home": SW3_CY_HOME, "locale": "cy-GB"},
}

# Confidence thresholds for fuzzy matching
EXACT_MATCH_CONFIDENCE = 1.0
SEQUENCE_MATCHER_THRESHOLD = 0.85
TOKEN_OVERLAP_MIN = 0.6

# SW2 category → SW3 topic mapping
# Keys are the SW2 URL category segments (e.g., "Agriculture")
# Values are dicts with "id" (SW3 topic ID) and "slug" (SW3 URL slug),
# or None for categories that should redirect to the homepage.
CATEGORY_TO_TOPIC = {
    "Agriculture": {
        "id": 23,
        "slug": "environment-energy-agriculture",
    },
    "Business-Economy-and-Labour-Market": {
        "id": 1,
        "slug": "business-economy-labour-market",
    },
    "Census": {
        "id": 71,
        "slug": "people-identity-equality",
    },
    "Community-Safety-and-Social-Inclusion": {
        "id": 8,
        "slug": "crime-fire-rescue",
    },
    "Education-and-Skills": {
        "id": 13,
        "slug": "education-training",
    },
    "Environment-and-Countryside": {
        "id": 23,
        "slug": "environment-energy-agriculture",
    },
    "Equality-and-Diversity": {
        "id": 71,
        "slug": "people-identity-equality",
    },
    "Health-and-Social-Care": {
        "id": 40,
        "slug": "health-social-care",
    },
    "Housing": {
        "id": 56,
        "slug": "housing",
    },
    "Local-Government": {
        "id": 32,
        "slug": "finance-tax",
    },
    "National-Survey-for-Wales": None,  # no direct SW3 equivalent
    "Population-and-Migration": {
        "id": 71,
        "slug": "people-identity-equality",
    },
    "Sustainable-Development": {
        "id": 23,
        "slug": "environment-energy-agriculture",
    },
    "Taxes-devolved-to-Wales": {
        "id": 32,
        "slug": "finance-tax",
    },
    "Tourism": {
        "id": 1,
        "slug": "business-economy-labour-market",
    },
    "Transport": {
        "id": 92,
        "slug": "transport",
    },
    "Welsh-Government": None,  # no direct SW3 equivalent
    "Welsh-Language": {
        "id": 102,
        "slug": "welsh-language",
    },
    "Well-being": None,  # no direct SW3 equivalent
}

# Download file code prefixes → SW2 category names
# Used to map /Download/File?fileName=CODE0123.ext → topic URL
CODE_PREFIX_TO_CATEGORY = {
    "AGRI": "Agriculture",
    "CARE": "Health-and-Social-Care",
    "CSAF": "Community-Safety-and-Social-Inclusion",
    "CSIW": "Health-and-Social-Care",
    "ECON": "Business-Economy-and-Labour-Market",
    "EDUC": "Education-and-Skills",
    "ENVI": "Environment-and-Countryside",
    "HLTH": "Health-and-Social-Care",
    "HOUS": "Housing",
    "LGFS": "Local-Government",
    "POPU": "Population-and-Migration",
    "SCHS": "Education-and-Skills",
    "SCHW": "Education-and-Skills",
    "SIEQ": "Equality-and-Diversity",
    "TRAN": "Transport",
    "WRAX": "Taxes-devolved-to-Wales",
    "YTHS": "Education-and-Skills",
}

# Data file paths
DATA_DIR = "data"
SW3_TOPICS_CACHE = f"{DATA_DIR}/sw3_topics.json"
SW3_DATASETS_CACHE = f"{DATA_DIR}/sw3_datasets.json"
MAPPING_CSV = f"{DATA_DIR}/mapping.csv"
OVERRIDES_CSV = f"{DATA_DIR}/overrides.csv"
PATHS_CSV = "paths.csv"


def sw3_dataset_url(uuid: str) -> str:
    """Build the SW3 URL for a specific dataset."""
    return f"{SW3_HOME}/{uuid}"


def sw3_topic_url(topic_id: int, slug: str) -> str:
    """Build the SW3 URL for a topic page."""
    return f"{SW3_HOME}/topic/{topic_id}/{slug}"


def sw3_topic_url_for_category(category: str) -> str:
    """Get the SW3 topic URL for an SW2 category, or homepage if unmapped."""
    topic = CATEGORY_TO_TOPIC.get(category)
    if topic is None:
        return SW3_HOME
    return sw3_topic_url(topic["id"], topic["slug"])
