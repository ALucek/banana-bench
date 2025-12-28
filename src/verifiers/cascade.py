"""Cascading error filtering for validation errors."""

from typing import List

from .models import ValidationError


# Cascade level constants
FATAL = 0  # Parsing errors - stop all downstream validation
CRITICAL = 1  # Structural errors - stop grid/accidental word checks
HIGH = 2  # Grid conflicts
MEDIUM = 3  # Word validation errors
LOW = 4  # Tile matching errors


def filter_cascading_errors(
    errors: List[ValidationError],
    max_errors: int = 5
) -> List[ValidationError]:
    """
    Filter out cascading errors based on hierarchy.

    Filtering rules:
    - Level 0 (FATAL) present → Show ONLY Level 0 errors
    - Level 1 (CRITICAL) present → Show Level 1 + INVALID_WORD + Level 4
    - Level 2 (HIGH) present → Show Level 2 + Level 3 + Level 4
    - Otherwise → Show all errors

    Args:
        errors: List of validation errors to filter
        max_errors: Maximum number of errors to return (default 5)

    Returns:
        Filtered list of errors, limited to max_errors
    """
    if not errors:
        return errors

    # Group errors by cascade level
    by_level: dict[int, List[ValidationError]] = {}
    for err in errors:
        level = err.cascade_level
        by_level.setdefault(level, []).append(err)

    # Determine which errors to show based on cascade rules
    result: List[ValidationError] = []

    # Level 0 (FATAL): Show only parsing errors
    if FATAL in by_level:
        result = by_level[FATAL]

    # Level 1 (CRITICAL): Show structural errors + intentional word errors + tile errors
    elif CRITICAL in by_level:
        result = by_level[CRITICAL].copy()
        # Add INVALID_WORD errors (but not ACCIDENTAL_INVALID)
        if MEDIUM in by_level:
            result.extend([e for e in by_level[MEDIUM] if e.code == "INVALID_WORD"])
        # Add tile errors (always relevant)
        if LOW in by_level:
            result.extend(by_level[LOW])

    # Level 2 (HIGH): Show grid conflicts + word validation + tiles
    elif HIGH in by_level:
        result = by_level[HIGH].copy()
        if MEDIUM in by_level:
            result.extend(by_level[MEDIUM])
        if LOW in by_level:
            result.extend(by_level[LOW])

    # No high-priority errors: show everything
    else:
        result = errors.copy()

    # Limit to max_errors to avoid overwhelming the LLM
    if len(result) > max_errors:
        # Keep first max_errors-1, add summary for rest
        kept = result[:max_errors - 1]
        num_hidden = len(result) - len(kept)

        # Add a summary error
        kept.append(ValidationError(
            code="ADDITIONAL_ERRORS",
            message=f"... and {num_hidden} more similar error{'s' if num_hidden > 1 else ''}. Fix the above first.",
            cascade_level=result[0].cascade_level
        ))
        return kept

    return result
