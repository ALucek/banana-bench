"""Test cascading error filtering logic."""

import pytest

from src.verifiers import verify
from src.verifiers.cascade import filter_cascading_errors, FATAL, CRITICAL, HIGH, MEDIUM, LOW
from src.verifiers.models import ValidationError


class TestCascadeLevelConstants:
    """Test that cascade level constants are correctly defined."""

    def test_cascade_levels_defined(self):
        """Cascade levels should have correct values."""
        assert FATAL == 0
        assert CRITICAL == 1
        assert HIGH == 2
        assert MEDIUM == 3
        assert LOW == 4


class TestCascadeFiltering:
    """Test error cascade hierarchy."""

    def test_parsing_error_hides_all_downstream(self):
        """When parsing fails, only show parsing errors."""
        # Invalid root format
        result = verify("CAT")  # Missing direction
        assert len(result.errors) >= 1
        assert result.errors[0].code == "INVALID_ROOT"

        filtered = filter_cascading_errors(result.errors)

        # Should only have INVALID_ROOT
        assert len(filtered) == 1
        assert filtered[0].code == "INVALID_ROOT"
        assert filtered[0].cascade_level == FATAL

    def test_empty_board_parsing_error(self):
        """Empty board should show only EMPTY_BOARD error."""
        result = verify("")
        filtered = filter_cascading_errors(result.errors)

        assert len(filtered) == 1
        assert filtered[0].code == "EMPTY_BOARD"
        assert filtered[0].cascade_level == FATAL

    def test_structural_error_hides_grid_conflicts(self):
        """Letter mismatch should hide resulting grid conflicts."""
        # Create a board with letter mismatch that would cause grid conflict
        spec = """
        CAT H
        DOG[0] @ CAT[0] V
        """
        result = verify(spec)

        # Should have both LETTER_MISMATCH and GRID_CONFLICT
        codes = [e.code for e in result.errors]
        assert "LETTER_MISMATCH" in codes
        assert "GRID_CONFLICT" in codes

        filtered = filter_cascading_errors(result.errors)

        # Filtered should only have LETTER_MISMATCH
        filtered_codes = [e.code for e in filtered]
        assert "LETTER_MISMATCH" in filtered_codes
        assert "GRID_CONFLICT" not in filtered_codes

    def test_structural_error_shows_invalid_word(self):
        """Structural errors should still show intentional invalid word errors."""
        # Create a board with structural error and invalid word
        spec = """
        XYZZY H
        DOG[0] @ XYZZY[0] V
        """
        result = verify(spec)

        # Should have LETTER_MISMATCH and INVALID_WORD
        codes = [e.code for e in result.errors]
        assert "LETTER_MISMATCH" in codes or "INVALID_WORD" in codes

        filtered = filter_cascading_errors(result.errors)

        # Should have both errors (INVALID_WORD is intentional, not accidental)
        filtered_codes = [e.code for e in filtered]
        if "LETTER_MISMATCH" in codes:
            assert "LETTER_MISMATCH" in filtered_codes
        if "INVALID_WORD" in codes:
            assert "INVALID_WORD" in filtered_codes

    def test_structural_error_hides_accidental_invalid(self):
        """Structural errors should hide accidental invalid word errors."""
        # Create errors with both structural and accidental invalid
        errors = [
            ValidationError(
                code="LETTER_MISMATCH",
                message="Letter mismatch",
                cascade_level=CRITICAL
            ),
            ValidationError(
                code="ACCIDENTAL_INVALID",
                message="Accidental invalid word",
                cascade_level=MEDIUM
            ),
        ]

        filtered = filter_cascading_errors(errors)

        # Should only have LETTER_MISMATCH
        assert len(filtered) == 1
        assert filtered[0].code == "LETTER_MISMATCH"

    def test_grid_conflict_shows_word_validation(self):
        """Grid conflicts should still show word validation errors."""
        errors = [
            ValidationError(
                code="GRID_CONFLICT",
                message="Grid conflict",
                cascade_level=HIGH
            ),
            ValidationError(
                code="INVALID_WORD",
                message="Invalid word",
                cascade_level=MEDIUM
            ),
            ValidationError(
                code="ACCIDENTAL_INVALID",
                message="Accidental invalid",
                cascade_level=MEDIUM
            ),
        ]

        filtered = filter_cascading_errors(errors)

        # Should have all three
        assert len(filtered) == 3
        codes = [e.code for e in filtered]
        assert "GRID_CONFLICT" in codes
        assert "INVALID_WORD" in codes
        assert "ACCIDENTAL_INVALID" in codes

    def test_tile_errors_shown_with_structural(self):
        """Tile errors (TILES_NOT_IN_HAND) should be shown even with structural errors.

        Note: TILES_UNUSED is now a warning, not an error, so it's handled separately.
        """
        errors = [
            ValidationError(
                code="LETTER_MISMATCH",
                message="Letter mismatch",
                cascade_level=CRITICAL
            ),
            ValidationError(
                code="TILES_NOT_IN_HAND",
                message="Tiles not in hand",
                cascade_level=LOW
            ),
        ]

        filtered = filter_cascading_errors(errors)

        # Should have both
        assert len(filtered) == 2
        codes = [e.code for e in filtered]
        assert "LETTER_MISMATCH" in codes
        assert "TILES_NOT_IN_HAND" in codes

    def test_tile_errors_not_shown_with_parsing(self):
        """Tile errors should be hidden when parsing fails."""
        errors = [
            ValidationError(
                code="INVALID_ROOT",
                message="Invalid root",
                cascade_level=FATAL
            ),
            ValidationError(
                code="TILES_NOT_IN_HAND",
                message="Tiles not in hand",
                cascade_level=LOW
            ),
        ]

        filtered = filter_cascading_errors(errors)

        # Should only have parsing error
        assert len(filtered) == 1
        assert filtered[0].code == "INVALID_ROOT"

    def test_max_errors_limit(self):
        """More than max_errors should be limited with summary."""
        # Create 10 errors of same level
        errors = [
            ValidationError(
                code=f"ERROR_{i}",
                message=f"Error {i}",
                cascade_level=CRITICAL
            )
            for i in range(10)
        ]

        filtered = filter_cascading_errors(errors, max_errors=5)

        # Should have exactly 5 errors
        assert len(filtered) == 5

        # Last error should be summary
        assert filtered[-1].code == "ADDITIONAL_ERRORS"
        assert "6 more" in filtered[-1].message  # 10 total - 4 kept = 6 hidden

    def test_no_errors_returns_empty(self):
        """Empty error list should return empty."""
        filtered = filter_cascading_errors([])
        assert filtered == []

    def test_no_high_priority_errors_shows_all(self):
        """When only low-priority errors, show all."""
        errors = [
            ValidationError(
                code="INVALID_WORD",
                message="Invalid word 1",
                cascade_level=MEDIUM
            ),
            ValidationError(
                code="ACCIDENTAL_INVALID",
                message="Accidental invalid",
                cascade_level=MEDIUM
            ),
            ValidationError(
                code="TILES_UNUSED",
                message="Tiles unused",
                cascade_level=LOW
            ),
        ]

        filtered = filter_cascading_errors(errors)

        # Should have all three
        assert len(filtered) == 3


class TestRealWorldScenarios:
    """Test with real board validation scenarios."""

    def test_valid_board_no_errors(self):
        """Valid board should have no errors."""
        spec = """
        CAT H
        """
        result = verify(spec)
        filtered = filter_cascading_errors(result.errors)

        assert len(filtered) == 0

    def test_complex_board_with_multiple_structural_errors(self):
        """Complex board with multiple structural errors."""
        # Multiple letter mismatches
        spec = """
        HELLO H
        WORLD[0] @ HELLO[4] V
        JOULE[2] @ WORLD[0] H
        """
        result = verify(spec)

        # May have structural errors and grid conflicts
        assert len(result.errors) > 0

        filtered = filter_cascading_errors(result.errors)

        # Should primarily show structural errors, not grid conflicts
        filtered_codes = [e.code for e in filtered]
        if "LETTER_MISMATCH" in [e.code for e in result.errors]:
            assert "LETTER_MISMATCH" in filtered_codes

    def test_improved_error_messages(self):
        """Verify that improved error messages are present."""
        # Letter mismatch
        spec = """
        CAT H
        DOG[0] @ CAT[0] V
        """
        result = verify(spec)

        # Find LETTER_MISMATCH error
        mismatch_errors = [e for e in result.errors if e.code == "LETTER_MISMATCH"]
        if mismatch_errors:
            # Should have TIP in message
            assert "TIP:" in mismatch_errors[0].message

        # Invalid root
        result2 = verify("CAT")
        root_errors = [e for e in result2.errors if e.code == "INVALID_ROOT"]
        if root_errors:
            # Should have Example in message
            assert "Example:" in root_errors[0].message


class TestFilteringLogicEdgeCases:
    """Test edge cases in filtering logic."""

    def test_mixed_cascade_levels(self):
        """Test with errors at multiple cascade levels."""
        errors = [
            ValidationError(code="FATAL_ERR", message="Fatal", cascade_level=FATAL),
            ValidationError(code="CRITICAL_ERR", message="Critical", cascade_level=CRITICAL),
            ValidationError(code="HIGH_ERR", message="High", cascade_level=HIGH),
            ValidationError(code="MEDIUM_ERR", message="Medium", cascade_level=MEDIUM),
            ValidationError(code="LOW_ERR", message="Low", cascade_level=LOW),
        ]

        filtered = filter_cascading_errors(errors)

        # Should only show FATAL
        assert len(filtered) == 1
        assert filtered[0].cascade_level == FATAL

    def test_only_word_and_tile_errors(self):
        """Only word validation and tile errors.

        Note: TILES_UNUSED is now a warning, so use TILES_NOT_IN_HAND for this test.
        """
        errors = [
            ValidationError(code="INVALID_WORD", message="Invalid", cascade_level=MEDIUM),
            ValidationError(code="TILES_NOT_IN_HAND", message="Not in hand", cascade_level=LOW),
        ]

        filtered = filter_cascading_errors(errors)

        # Should show both
        assert len(filtered) == 2

    def test_max_errors_edge_case_exactly_max(self):
        """Exactly max_errors should not add summary."""
        errors = [
            ValidationError(code=f"ERR_{i}", message=f"Error {i}", cascade_level=CRITICAL)
            for i in range(5)
        ]

        filtered = filter_cascading_errors(errors, max_errors=5)

        # Should have exactly 5, no summary
        assert len(filtered) == 5
        assert all(e.code != "ADDITIONAL_ERRORS" for e in filtered)

    def test_max_errors_edge_case_one_more(self):
        """One more than max_errors should add summary."""
        errors = [
            ValidationError(code=f"ERR_{i}", message=f"Error {i}", cascade_level=CRITICAL)
            for i in range(6)
        ]

        filtered = filter_cascading_errors(errors, max_errors=5)

        # Should have exactly 5, with summary
        assert len(filtered) == 5
        assert filtered[-1].code == "ADDITIONAL_ERRORS"
        assert "2 more" in filtered[-1].message  # 6 total - 4 kept = 2 hidden
