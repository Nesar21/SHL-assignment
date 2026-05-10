"""
Catalog module: loads SHL product catalog, builds lookup dicts, generates compact string.

On startup (eager, in lifespan):
  1. Load shl_product_catalog.json (377 items)
  2. Build by_entity_id dict for O(1) lookup
  3. Derive test_type codes from keys array
  4. Generate compact catalog string for prompt injection (~19K tokens estimated)

lookup(entity_id) is the ONLY way recommendations are constructed.
It returns an exact catalog match or None. Never fuzzy matches.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from app import config
from app.models import Recommendation

logger = logging.getLogger(__name__)

# --- Key code mapping (PDF: A, B, C, D, E, K, P, S) ---
KEY_MAP: dict[str, str] = {
    "Ability & Aptitude": "A",
    "Assessment Exercises": "E",
    "Biodata & Situational Judgment": "B",
    "Competencies": "C",
    "Development & 360": "D",
    "Knowledge & Skills": "K",
    "Personality & Behavior": "P",
    "Simulations": "S",
}

# --- Job level abbreviations for compact format ---
LEVEL_MAP: dict[str, str] = {
    "Director": "Dir",
    "Entry-Level": "Ent",
    "Executive": "Exec",
    "Front Line Manager": "FLM",
    "General Population": "GP",
    "Graduate": "Grad",
    "Manager": "Mgr",
    "Mid-Professional": "Mid",
    "Professional Individual Contributor": "PIC",
    "Supervisor": "Sup",
}

# --- Module-level state (populated by load()) ---
_catalog_items: list[dict] = []
_by_entity_id: dict[str, dict] = {}
_compact_catalog: str = ""
_all_names: set[str] = set()
_all_job_levels: set[str] = set()
_all_languages: set[str] = set()


def _get_test_type(item: dict) -> str:
    """Derive test_type code string from item's keys array.
    
    Default: comma-separated (e.g. "A,S", "P,C") — matches trace format.
    With TEST_TYPE_PRIMARY_ONLY=true: single primary code (e.g. "A", "P").
    """
    codes = [KEY_MAP[k] for k in item.get("keys", []) if k in KEY_MAP]
    if not codes:
        return ""
    if config.TEST_TYPE_PRIMARY_ONLY:
        return codes[0]
    return ",".join(codes)


def _truncate_description(description: str) -> str:
    """Truncate description to DESCRIPTION_MAX_WORDS words."""
    words = description.split()
    if len(words) <= config.DESCRIPTION_MAX_WORDS:
        return description
    return " ".join(words[:config.DESCRIPTION_MAX_WORDS]) + "..."


def _build_compact_line(item: dict) -> str:
    """Build a compact single-line catalog entry for prompt injection.
    
    Format: [entity_id] Name | KeyCodes | Levels | Languages | Duration | Description
    """
    eid = item["entity_id"]
    name = item["name"]
    keys = item["_test_type_code"]
    levels = ",".join(LEVEL_MAP.get(lvl, lvl) for lvl in item.get("job_levels", []))

    langs = item.get("languages", [])
    if not langs:
        lang_str = "-"
    elif len(langs) <= 3:
        lang_str = ",".join(langs)
    else:
        lang_str = ",".join(langs[:3]) + f" +{len(langs) - 3}"

    dur = item.get("duration", "") or "-"
    remote = item.get("remote", "")
    adaptive = item.get("adaptive", "")
    desc = _truncate_description(item.get("description", ""))

    return (
        f"[{eid}] {name} | {keys} | {levels} | "
        f"{lang_str} | {dur} | Remote:{remote} Adaptive:{adaptive} | {desc}"
    )


def load() -> None:
    """Load catalog from JSON file. Call once at startup."""
    global _catalog_items, _by_entity_id, _compact_catalog, _all_names
    global _all_job_levels, _all_languages

    catalog_path = Path(config.CATALOG_PATH)
    if not catalog_path.is_absolute():
        # Resolve relative to project root (parent of app/)
        project_root = Path(__file__).parent.parent
        catalog_path = project_root / catalog_path

    logger.info(f"Loading catalog from: {catalog_path}")
    with open(catalog_path, "r", encoding="utf-8") as f:
        _catalog_items = json.load(f)

    _by_entity_id = {}
    _all_names = set()
    _all_job_levels = set()
    _all_languages = set()
    lines: list[str] = []

    for item in _catalog_items:
        eid = str(item["entity_id"])
        # Pre-compute test_type code and store on item
        item["_test_type_code"] = _get_test_type(item)
        _by_entity_id[eid] = item
        _all_names.add(item["name"])

        # Collect all job levels and languages for test utilities
        for lvl in item.get("job_levels", []):
            _all_job_levels.add(lvl)
        for lang in item.get("languages", []):
            _all_languages.add(lang)

        lines.append(_build_compact_line(item))

    _compact_catalog = "\n".join(lines)

    logger.info(
        f"Catalog loaded: {len(_catalog_items)} items, "
        f"compact string: {len(_compact_catalog):,} chars (~{len(_compact_catalog) // 4:,} estimated tokens), "
        f"{len(_all_job_levels)} unique job levels, "
        f"{len(_all_languages)} unique languages"
    )


def lookup(entity_id: str) -> Optional[Recommendation]:
    """Strict lookup by entity_id. Returns Recommendation or None.
    
    This is the ONLY path for constructing recommendations.
    name, url, test_type are ALL from the catalog — never from LLM output.
    """
    item = _by_entity_id.get(str(entity_id))
    if item is None:
        return None
    return Recommendation(
        name=item["name"],
        url=item["link"],
        test_type=item["_test_type_code"],
    )


def get_compact_catalog() -> str:
    """Return the full compact catalog string for system prompt injection."""
    return _compact_catalog


def all_names() -> set[str]:
    """Return all catalog item names (for hallucination detection in tests)."""
    return _all_names.copy()


def all_job_levels() -> set[str]:
    """Return all unique job level names from catalog."""
    return _all_job_levels.copy()


def all_languages() -> set[str]:
    """Return all unique language names from catalog."""
    return _all_languages.copy()


def get_item_count() -> int:
    """Return number of items loaded."""
    return len(_catalog_items)
