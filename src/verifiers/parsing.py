"""Board parsing utilities."""

import re
from typing import List, Tuple

from .models import WordEntry, ValidationError


def extract_board_content(spec: str) -> str:
    """Extract content from between <board> and </board> tags."""
    match = re.search(r'<board>(.*?)</board>', spec, re.DOTALL)
    if match:
        return match.group(1).strip()
    return spec.strip()


def parse_board(spec: str) -> Tuple[List[WordEntry], List[ValidationError]]:
    """
    Parse the board specification into word entries with error collection.
    
    Returns a tuple of (entries, errors).
    """
    spec = extract_board_content(spec)
    lines = [line.strip() for line in spec.strip().split('\n') if line.strip()]
    
    errors: List[ValidationError] = []
    entries: List[WordEntry] = []
    
    if not lines:
        errors.append(ValidationError(
            code="EMPTY_BOARD",
            message="Board specification is empty"
        ))
        return entries, errors
    
    # First line: ROOT DIRECTION
    root_match = re.match(r'^([A-Z]+)\s+([HV])$', lines[0], re.IGNORECASE)
    if not root_match:
        errors.append(ValidationError(
            code="INVALID_ROOT",
            message=f"Invalid root line format: '{lines[0]}'",
            line=1
        ))
        return entries, errors
    
    entries.append(WordEntry(
        word=root_match.group(1).upper(),
        direction=root_match.group(2).upper()
    ))
    
    # Subsequent lines: WORD[j] @ TARGET[i] DIRECTION
    pattern = r'^([A-Z]+)\[(\d+)\]\s*@\s*([A-Z]+)\[(\d+)\]\s+([HV])$'
    for i, line in enumerate(lines[1:], start=2):
        match = re.match(pattern, line, re.IGNORECASE)
        if not match:
            errors.append(ValidationError(
                code="INVALID_LINE",
                message=f"Invalid line format: '{line}'",
                line=i
            ))
            continue
        
        entries.append(WordEntry(
            word=match.group(1).upper(),
            direction=match.group(5).upper(),
            target=match.group(3).upper(),
            target_idx=int(match.group(4)),
            word_idx=int(match.group(2))
        ))
    
    return entries, errors

