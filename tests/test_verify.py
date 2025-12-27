"""
Comprehensive test suite for board verification.

Tests all validation cases:
- Parse errors (EMPTY_BOARD, INVALID_ROOT, INVALID_LINE)
- Structure errors (TARGET_NOT_FOUND, TARGET_INDEX_OOB, WORD_INDEX_OOB, LETTER_MISMATCH, SAME_DIRECTION)
- Grid errors (GRID_CONFLICT)
- Word validation (INVALID_WORD, ACCIDENTAL_INVALID, ACCIDENTAL_VALID)
"""

import pytest
from src.verifiers import verify, ValidationResult


class TestValidBoards:
    """Test cases for valid board configurations."""
    
    def test_single_word_horizontal(self):
        """Single horizontal word should be valid."""
        result = verify("<board>CAT H</board>")
        assert result.valid is True
        assert result.words == ["CAT"]
        assert "CAT" in result.grid
    
    def test_single_word_vertical(self):
        """Single vertical word should be valid."""
        result = verify("<board>DOG V</board>")
        assert result.valid is True
        assert result.words == ["DOG"]
    
    def test_two_words_perpendicular(self):
        """Two perpendicular words with correct intersection."""
        result = verify("""
        <board>
        CAT H
        TAR[0] @ CAT[2] V
        </board>
        """)
        assert result.valid is True
        assert result.words == ["CAT", "TAR"]
    
    def test_complex_valid_board(self):
        """Complex board with multiple intersections."""
        result = verify("""
        <board>
        SCURRIES H
        NINES[4] @ SCURRIES[0] V
        RUNES[2] @ NINES[0] H
        YEN[2] @ NINES[2] H
        BRAWN[1] @ SCURRIES[3] V
        DEN[2] @ BRAWN[4] H
        DEED[0] @ DEN[0] V
        STIR[2] @ SCURRIES[5] V
        SPARK[0] @ STIR[0] H
        TRAPS[2] @ SPARK[2] V
        TIGER[0] @ TRAPS[0] H
        TAROT[2] @ TIGER[4] V
        </board>
        """)
        assert result.valid is True
        assert len(result.words) == 12
        assert result.grid is not None
    
    def test_board_without_tags(self):
        """Board specification without XML tags should work."""
        result = verify("CAT H")
        assert result.valid is True
        assert result.words == ["CAT"]
    
    def test_case_insensitive_words(self):
        """Words should be case-insensitive."""
        result = verify("<board>cat H</board>")
        assert result.valid is True
        assert result.words == ["CAT"]
    
    def test_case_insensitive_direction(self):
        """Direction should be case-insensitive."""
        result = verify("<board>CAT h</board>")
        assert result.valid is True


class TestParseErrors:
    """Test cases for parsing errors."""
    
    def test_empty_board(self):
        """Empty board specification should fail."""
        result = verify("<board></board>")
        assert result.valid is False
        assert any(e.code == "EMPTY_BOARD" for e in result.errors)
    
    def test_empty_string(self):
        """Empty string should fail."""
        result = verify("")
        assert result.valid is False
        assert any(e.code == "EMPTY_BOARD" for e in result.errors)
    
    def test_whitespace_only(self):
        """Whitespace-only board should fail."""
        result = verify("<board>   \n   </board>")
        assert result.valid is False
        assert any(e.code == "EMPTY_BOARD" for e in result.errors)
    
    def test_invalid_root_missing_direction(self):
        """Root line missing direction should fail."""
        result = verify("<board>CAT</board>")
        assert result.valid is False
        assert any(e.code == "INVALID_ROOT" for e in result.errors)
    
    def test_invalid_root_bad_direction(self):
        """Root line with invalid direction should fail."""
        result = verify("<board>CAT X</board>")
        assert result.valid is False
        assert any(e.code == "INVALID_ROOT" for e in result.errors)
    
    def test_invalid_root_numbers_in_word(self):
        """Root line with numbers in word should fail."""
        result = verify("<board>CAT123 H</board>")
        assert result.valid is False
        assert any(e.code == "INVALID_ROOT" for e in result.errors)
    
    def test_invalid_line_format(self):
        """Non-root line with bad format should fail."""
        result = verify("""
        <board>
        CAT H
        DOG @ CAT V
        </board>
        """)
        assert result.valid is False
        assert any(e.code == "INVALID_LINE" for e in result.errors)
    
    def test_invalid_line_missing_indices(self):
        """Non-root line missing indices should fail."""
        result = verify("""
        <board>
        CAT H
        DOG @ CAT[0] V
        </board>
        """)
        assert result.valid is False
        assert any(e.code == "INVALID_LINE" for e in result.errors)
    
    def test_invalid_line_missing_at_symbol(self):
        """Non-root line missing @ symbol should fail."""
        result = verify("""
        <board>
        CAT H
        DOG[0] CAT[0] V
        </board>
        """)
        assert result.valid is False
        assert any(e.code == "INVALID_LINE" for e in result.errors)


class TestStructureErrors:
    """Test cases for structural validation errors."""
    
    def test_target_not_found(self):
        """Referencing non-existent target word should fail."""
        result = verify("""
        <board>
        CAT H
        DOG[0] @ BIRD[0] V
        </board>
        """)
        assert result.valid is False
        assert any(e.code == "TARGET_NOT_FOUND" for e in result.errors)
    
    def test_target_not_yet_placed(self):
        """Referencing word that comes later should fail."""
        result = verify("""
        <board>
        CAT H
        DOG[0] @ BIRD[0] V
        BIRD[0] @ CAT[0] V
        </board>
        """)
        assert result.valid is False
        assert any(e.code == "TARGET_NOT_FOUND" for e in result.errors)
    
    def test_target_index_out_of_bounds(self):
        """Target index exceeding word length should fail."""
        result = verify("""
        <board>
        CAT H
        DOG[0] @ CAT[5] V
        </board>
        """)
        assert result.valid is False
        assert any(e.code == "TARGET_INDEX_OOB" for e in result.errors)
    
    def test_target_index_exact_length(self):
        """Target index equal to word length should fail (0-indexed)."""
        result = verify("""
        <board>
        CAT H
        DOG[0] @ CAT[3] V
        </board>
        """)
        assert result.valid is False
        assert any(e.code == "TARGET_INDEX_OOB" for e in result.errors)
    
    def test_word_index_out_of_bounds(self):
        """Word index exceeding word length should fail."""
        result = verify("""
        <board>
        CAT H
        DOG[5] @ CAT[0] V
        </board>
        """)
        assert result.valid is False
        assert any(e.code == "WORD_INDEX_OOB" for e in result.errors)
    
    def test_letter_mismatch(self):
        """Mismatched letters at intersection should fail."""
        result = verify("""
        <board>
        CAT H
        DOG[0] @ CAT[0] V
        </board>
        """)
        assert result.valid is False
        assert any(e.code == "LETTER_MISMATCH" for e in result.errors)
        # Check error message contains useful info
        error = next(e for e in result.errors if e.code == "LETTER_MISMATCH")
        assert "D" in error.message and "C" in error.message
    
    def test_same_direction_horizontal(self):
        """Horizontal word attaching to horizontal word should fail."""
        result = verify("""
        <board>
        CAT H
        ACE[0] @ CAT[1] H
        </board>
        """)
        assert result.valid is False
        assert any(e.code == "SAME_DIRECTION" for e in result.errors)
    
    def test_same_direction_vertical(self):
        """Vertical word attaching to vertical word should fail."""
        result = verify("""
        <board>
        CAT V
        ACE[0] @ CAT[1] V
        </board>
        """)
        assert result.valid is False
        assert any(e.code == "SAME_DIRECTION" for e in result.errors)


class TestGridErrors:
    """Test cases for grid conflict errors."""
    
    def test_grid_conflict_different_letters(self):
        """Overlapping cells with different letters should fail."""
        # This creates a situation where letters conflict
        result = verify("""
        <board>
        HELLO H
        WORLD[0] @ HELLO[0] V
        </board>
        """)
        assert result.valid is False
        # Should have letter mismatch AND grid conflict
        assert any(e.code == "LETTER_MISMATCH" for e in result.errors)
        assert any(e.code == "GRID_CONFLICT" for e in result.errors)
    
    def test_no_conflict_same_letter(self):
        """Overlapping cells with same letter should succeed."""
        result = verify("""
        <board>
        CAT H
        TAR[0] @ CAT[2] V
        </board>
        """)
        assert result.valid is True
        assert not any(e.code == "GRID_CONFLICT" for e in result.errors)


class TestWordValidation:
    """Test cases for dictionary word validation."""
    
    def test_invalid_word_root(self):
        """Invalid dictionary word as root should fail."""
        result = verify("<board>XYZZY H</board>")
        assert result.valid is False
        assert any(e.code == "INVALID_WORD" for e in result.errors)
        error = next(e for e in result.errors if e.code == "INVALID_WORD")
        assert "XYZZY" in error.message
    
    def test_invalid_word_non_root(self):
        """Invalid dictionary word in non-root position should fail."""
        result = verify("""
        <board>
        CAT H
        XYZAT[3] @ CAT[1] V
        </board>
        """)
        assert result.valid is False
        assert any(e.code == "INVALID_WORD" for e in result.errors)
    
    def test_valid_dictionary_words(self):
        """All valid dictionary words should pass."""
        result = verify("""
        <board>
        CAT H
        TAR[0] @ CAT[2] V
        </board>
        """)
        assert result.valid is True
        assert not any(e.code == "INVALID_WORD" for e in result.errors)
    
    def test_accidental_invalid_word(self):
        """Accidental invalid word formed on grid should fail."""
        # Board forms: A T .
        #              C A T
        # Declared: AT, TA, CAT (all valid)
        # Accidental: AC (column 0, invalid word)
        result = verify("""
        <board>
        AT H
        TA[0] @ AT[1] V
        CAT[1] @ TA[1] H
        </board>
        """)
        assert result.valid is False
        assert any(e.code == "ACCIDENTAL_INVALID" for e in result.errors)
        error = next(e for e in result.errors if e.code == "ACCIDENTAL_INVALID")
        assert error.word == "AC"


class TestWarnings:
    """Test cases for validation warnings."""
    
    def test_accidental_valid_word_warning(self):
        """Valid accidental word should generate warning, not error."""
        result = verify("""
        <board>
        AT H
        TA[0] @ AT[1] V
        AN[0] @ AT[0] V
        </board>
        """)
        # Should be valid (NA is valid, just not declared)
        assert result.valid is True
        # Should have warning for accidental valid word
        assert len(result.warnings) == 1
        assert result.warnings[0].code == "ACCIDENTAL_VALID"
        assert result.warnings[0].word == "NA"


class TestValidationResult:
    """Test the ValidationResult model structure."""
    
    def test_result_has_all_fields(self):
        """ValidationResult should have all expected fields."""
        result = verify("<board>CAT H</board>")
        assert hasattr(result, 'valid')
        assert hasattr(result, 'errors')
        assert hasattr(result, 'warnings')
        assert hasattr(result, 'words')
        assert hasattr(result, 'grid')
    
    def test_result_types(self):
        """ValidationResult fields should have correct types."""
        result = verify("<board>CAT H</board>")
        assert isinstance(result.valid, bool)
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)
        assert isinstance(result.words, list)
        assert result.grid is None or isinstance(result.grid, str)
    
    def test_error_structure(self):
        """Validation errors should have correct structure."""
        result = verify("<board>XYZZY H</board>")
        assert len(result.errors) > 0
        error = result.errors[0]
        assert hasattr(error, 'code')
        assert hasattr(error, 'message')
        assert hasattr(error, 'word')
        assert hasattr(error, 'line')
    
    def test_words_list_populated(self):
        """Words list should contain declared words."""
        result = verify("""
        <board>
        CAT H
        TAR[0] @ CAT[2] V
        </board>
        """)
        assert "CAT" in result.words
        assert "TAR" in result.words
        assert len(result.words) == 2


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_single_letter_word(self):
        """Single letter words should be handled (but are invalid in TWL)."""
        result = verify("<board>A H</board>")
        # Single letter "A" is NOT a valid word in TWL dictionary
        assert result.valid is False
        assert any(e.code == "INVALID_WORD" for e in result.errors)
    
    def test_long_word(self):
        """Long words should be handled correctly."""
        result = verify("<board>INTERNATIONALLY H</board>")
        assert result.valid is True
        assert result.words == ["INTERNATIONALLY"]
    
    def test_index_zero(self):
        """Index 0 should work correctly."""
        result = verify("""
        <board>
        CAT H
        COT[0] @ CAT[0] V
        </board>
        """)
        assert result.valid is True
    
    def test_last_index(self):
        """Last valid index should work correctly."""
        result = verify("""
        <board>
        CAT H
        TAR[0] @ CAT[2] V
        </board>
        """)
        assert result.valid is True
    
    def test_multiple_errors(self):
        """Multiple errors should all be reported."""
        result = verify("""
        <board>
        XYZZY H
        ABCDE[0] @ XYZZY[0] H
        </board>
        """)
        assert result.valid is False
        # Should have multiple types of errors
        error_codes = [e.code for e in result.errors]
        assert len(error_codes) >= 2
    
    def test_multiline_whitespace(self):
        """Extra whitespace should be handled."""
        result = verify("""
        
        <board>
        
        CAT H
        
        TAR[0] @ CAT[2] V
        
        </board>
        
        """)
        assert result.valid is True


class TestGridRendering:
    """Test grid rendering output."""
    
    def test_grid_contains_words(self):
        """Rendered grid should contain placed words."""
        result = verify("<board>CAT H</board>")
        assert result.grid is not None
        assert "CAT" in result.grid
    
    def test_grid_uses_dots_for_empty(self):
        """Empty cells should be rendered as dots."""
        result = verify("""
        <board>
        CAT H
        TAR[0] @ CAT[2] V
        </board>
        """)
        assert result.grid is not None
        assert "." in result.grid
    
    def test_grid_multiline(self):
        """Multi-row grids should have newlines."""
        result = verify("""
        <board>
        CAT H
        TAR[0] @ CAT[2] V
        </board>
        """)
        assert result.grid is not None
        assert "\n" in result.grid

