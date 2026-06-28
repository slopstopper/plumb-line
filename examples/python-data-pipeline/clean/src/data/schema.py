"""
data/schema.py
Static field type mappings. Pure data — imports nothing upward.
Layer: data (bottom). Allowed imports: none.
"""

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
