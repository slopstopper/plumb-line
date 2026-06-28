"""
data/schema.py
Static field type mappings.
Layer: data (bottom).
"""

from src.ui.report import build_report

# Maps field names to their expected Python types for validation.
FIELD_TYPES = {
    "id": str,
    "value": float,
    "category": str,
    "timestamp": str,
}

# Fields that contribute to numeric aggregation.
NUMERIC_FIELDS = ["value"]

# Fields used as record identifiers.
IDENTIFIER_FIELDS = ["id"]


def validate_and_display(records, config):
    """Run a quick validation pass and return a formatted report."""
    return build_report(records, config)
