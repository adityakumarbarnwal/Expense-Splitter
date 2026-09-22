"""
Tests for the AI expense parser.

Uses mocking to avoid actual Gemini API calls during testing.
Tests cover: valid input, missing amount, unknown member, LLM failure, malformed response.
"""

import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock

from app.services.ai.expense_parser import parse_expense_from_text, _parse_gemini_response
from app.services.ai.ai_validator import validate_ai_parse_result
from app.schemas.ai_response import AIParseResult


GROUP_MEMBERS = ["Aditya", "Rahul", "Aman"]


class TestParseGeminiResponse:
    """Unit tests for the response parser."""

    def test_valid_json_response(self):
        """Valid JSON is parsed correctly."""
        json_str = '''{
            "description": "Dinner",
            "amount": 1200,
            "payer": "Rahul",
            "participants": ["Aditya", "Rahul", "Aman"],
            "confidence": "high",
            "notes": null
        }'''
        result = _parse_gemini_response(json_str)
        assert result.description == "Dinner"
        assert result.amount == Decimal("1200")
        assert result.payer_name == "Rahul"
        assert len(result.participant_names) == 3

    def test_json_with_code_fence(self):
        """JSON wrapped in markdown code fences is stripped."""
        json_str = '```json\n{"description": "Lunch", "amount": 300, "payer": "Aditya", "participants": ["Aditya"], "confidence": "high", "notes": null}\n```'
        result = _parse_gemini_response(json_str)
        assert result.description == "Lunch"

    def test_invalid_json_raises(self):
        """Invalid JSON raises ValueError."""
        with pytest.raises(ValueError, match="invalid JSON"):
            _parse_gemini_response("This is not JSON")

    def test_null_amount(self):
        """Null amount is preserved as None."""
        json_str = '{"description": "Unknown", "amount": null, "payer": null, "participants": [], "confidence": "low", "notes": "Could not extract amount"}'
        result = _parse_gemini_response(json_str)
        assert result.amount is None


class TestAIValidator:
    """Unit tests for the AI output validator."""

    def test_valid_members_pass(self):
        """All members present in group → no warnings."""
        result = AIParseResult(
            description="Dinner",
            amount=Decimal("900"),
            payer_name="Aditya",
            participant_names=["Aditya", "Rahul", "Aman"],
            confidence="high",
        )
        validated, warnings = validate_ai_parse_result(result, GROUP_MEMBERS)
        assert warnings == []
        assert validated.payer_name == "Aditya"
        assert len(validated.participant_names) == 3

    def test_unknown_payer_flagged(self):
        """Unknown payer name generates a warning."""
        result = AIParseResult(
            description="Dinner",
            amount=Decimal("900"),
            payer_name="UnknownPerson",  # Not in group
            participant_names=["Aditya"],
            confidence="high",
        )
        validated, warnings = validate_ai_parse_result(result, GROUP_MEMBERS)
        assert any("UnknownPerson" in w for w in warnings)
        assert validated.payer_name is None  # Cleared because unknown

    def test_unknown_participant_removed(self):
        """Unknown participant is removed with a warning."""
        result = AIParseResult(
            description="Dinner",
            amount=Decimal("900"),
            payer_name="Aditya",
            participant_names=["Aditya", "Ghost"],  # Ghost not in group
            confidence="high",
        )
        validated, warnings = validate_ai_parse_result(result, GROUP_MEMBERS)
        assert "Ghost" not in validated.participant_names
        assert any("Ghost" in w for w in warnings)
        assert "Aditya" in validated.participant_names

    def test_case_insensitive_member_matching(self):
        """Member names are matched case-insensitively."""
        result = AIParseResult(
            description="Taxi",
            amount=Decimal("200"),
            payer_name="aditya",  # lowercase
            participant_names=["RAHUL"],  # uppercase
            confidence="high",
        )
        validated, warnings = validate_ai_parse_result(result, GROUP_MEMBERS)
        assert warnings == []
        assert validated.payer_name == "Aditya"  # Corrected to proper case
        assert validated.participant_names == ["Rahul"]

    def test_negative_amount_flagged(self):
        """Negative amount generates a warning and is cleared."""
        result = AIParseResult(
            description="Something",
            amount=Decimal("-100"),
            payer_name="Aditya",
            participant_names=["Aditya"],
            confidence="high",
        )
        validated, warnings = validate_ai_parse_result(result, GROUP_MEMBERS)
        assert any("non-positive" in w for w in warnings)
        assert validated.amount is None


class TestParseExpenseFromText:
    """Integration tests for parse_expense_from_text with mocked Gemini."""

    def _make_mock_response(self, json_text: str):
        """Create a mock Gemini response object."""
        mock_response = MagicMock()
        mock_response.text = json_text
        return mock_response

    def test_successful_parse(self):
        """Valid natural language is parsed correctly."""
        mock_json = '{"description": "Dinner", "amount": 1200, "payer": "Aditya", "participants": ["Aditya", "Rahul", "Aman"], "confidence": "high", "notes": null}'

        with patch("app.services.ai.expense_parser.genai") as mock_genai:
            mock_model = MagicMock()
            mock_genai.GenerativeModel.return_value = mock_model
            mock_model.generate_content.return_value = self._make_mock_response(mock_json)

            with patch("app.services.ai.expense_parser.settings") as mock_settings:
                mock_settings.gemini_api_key = "test-key-12345"
                mock_settings.gemini_model = "gemini-2.0-flash"

                result = parse_expense_from_text(
                    text="I paid 1200 for dinner for me, Rahul and Aman",
                    group_member_names=GROUP_MEMBERS,
                    current_member_name="Aditya",
                )

        assert result.success is True
        assert result.result is not None
        assert result.result.description == "Dinner"
        assert result.result.amount == Decimal("1200")

    def test_missing_api_key_returns_error(self):
        """Missing API key returns a user-friendly error."""
        with patch("app.services.ai.expense_parser.settings") as mock_settings:
            mock_settings.gemini_api_key = ""

            result = parse_expense_from_text(
                text="Lunch for 3 people",
                group_member_names=GROUP_MEMBERS,
            )

        assert result.success is False
        assert result.error is not None
        assert "not configured" in result.error.lower() or "manual" in result.error.lower()

    def test_api_failure_returns_error(self):
        """API exception is caught and returns a user-friendly error."""
        with patch("app.services.ai.expense_parser.genai") as mock_genai:
            mock_model = MagicMock()
            mock_genai.GenerativeModel.return_value = mock_model
            mock_model.generate_content.side_effect = Exception("API Error")

            with patch("app.services.ai.expense_parser.settings") as mock_settings:
                mock_settings.gemini_api_key = "test-key-12345"
                mock_settings.gemini_model = "gemini-2.0-flash"

                result = parse_expense_from_text(
                    text="Dinner for everyone",
                    group_member_names=GROUP_MEMBERS,
                )

        assert result.success is False
        assert "unavailable" in result.error.lower() or "manual" in result.error.lower()

    def test_malformed_response_returns_error(self):
        """Malformed AI response returns error gracefully."""
        with patch("app.services.ai.expense_parser.genai") as mock_genai:
            mock_model = MagicMock()
            mock_genai.GenerativeModel.return_value = mock_model
            mock_model.generate_content.return_value = self._make_mock_response(
                "This is not valid JSON at all!"
            )

            with patch("app.services.ai.expense_parser.settings") as mock_settings:
                mock_settings.gemini_api_key = "test-key-12345"
                mock_settings.gemini_model = "gemini-2.0-flash"

                result = parse_expense_from_text(
                    text="Dinner",
                    group_member_names=GROUP_MEMBERS,
                )

        assert result.success is False

    def test_unknown_member_generates_warning(self):
        """AI output with unknown member generates a warning but still succeeds."""
        mock_json = '{"description": "Dinner", "amount": 500, "payer": "Aditya", "participants": ["Aditya", "Ghost"], "confidence": "medium", "notes": null}'

        with patch("app.services.ai.expense_parser.genai") as mock_genai:
            mock_model = MagicMock()
            mock_genai.GenerativeModel.return_value = mock_model
            mock_model.generate_content.return_value = self._make_mock_response(mock_json)

            with patch("app.services.ai.expense_parser.settings") as mock_settings:
                mock_settings.gemini_api_key = "test-key-12345"
                mock_settings.gemini_model = "gemini-2.0-flash"

                result = parse_expense_from_text(
                    text="Dinner for Aditya and Ghost",
                    group_member_names=GROUP_MEMBERS,
                )

        assert result.success is True
        assert len(result.warnings) > 0
        # Ghost should be removed from participants
        assert "Ghost" not in result.result.participant_names
