"""core/validation.py için birim testler"""
import pytest
from core.validation import (
    ValidationError, bounded_integer, limited_string,
    require_json_object, identifier, IDENTIFIER_PATTERN,
)


class TestBoundedInteger:
    def test_valid_value(self):
        assert bounded_integer(5, "port", 1, 100) == 5

    def test_default_value_when_none(self):
        assert bounded_integer(None, "count", 0, 99, default=10) == 10

    def test_string_number(self):
        assert bounded_integer("42", "limit", 1, 100) == 42

    def test_min_boundary(self):
        assert bounded_integer(1, "x", 1, 10) == 1

    def test_max_boundary(self):
        assert bounded_integer(10, "x", 1, 10) == 10

    def test_below_minimum(self):
        with pytest.raises(ValidationError, match="must be between"):
            bounded_integer(0, "x", 1, 10)

    def test_above_maximum(self):
        with pytest.raises(ValidationError, match="must be between"):
            bounded_integer(11, "x", 1, 10)

    def test_invalid_string(self):
        with pytest.raises(ValidationError, match="must be an integer"):
            bounded_integer("abc", "x", 1, 10)

    def test_negative_value(self):
        with pytest.raises(ValidationError, match="must be between"):
            bounded_integer(-1, "x", 0, 10)

    def test_large_port_range(self):
        assert bounded_integer(65535, "port", 1, 65535) == 65535


class TestLimitedString:
    def test_valid_string(self):
        assert limited_string("hello", "name") == "hello"

    def test_strips_whitespace(self):
        assert limited_string("  hello  ", "name") == "hello"

    def test_minimum_length(self):
        assert limited_string("a", "x", minimum_length=1) == "a"

    def test_too_short(self):
        with pytest.raises(ValidationError, match="length must be between"):
            limited_string("", "x", minimum_length=1)

    def test_too_long(self):
        with pytest.raises(ValidationError, match="length must be between"):
            limited_string("a" * 5000, "x")

    def test_not_a_string(self):
        with pytest.raises(ValidationError, match="must be a string"):
            limited_string(123, "x")

    def test_control_characters(self):
        with pytest.raises(ValidationError, match="invalid control"):
            limited_string("hello\x00world", "x")

    def test_allows_newline_tab(self):
        assert limited_string("a\nb\tc", "x") == "a\nb\tc"


class TestIdentifierPattern:
    def test_valid_identifier(self):
        assert IDENTIFIER_PATTERN.fullmatch("abc123") is not None
        assert IDENTIFIER_PATTERN.fullmatch("test-id") is not None
        assert IDENTIFIER_PATTERN.fullmatch("a.b_c:z") is not None

    def test_invalid_identifier_empty(self):
        assert IDENTIFIER_PATTERN.fullmatch("") is None

    def test_invalid_identifier_special(self):
        assert IDENTIFIER_PATTERN.fullmatch("hello world") is None
        assert IDENTIFIER_PATTERN.fullmatch("test@id") is None


class TestRequireJsonObject:
    def test_valid_dict(self, monkeypatch):
        class FakeRequest:
            def get_json(self, silent=True):
                return {"key": "value"}
        req = FakeRequest()
        assert require_json_object(req) == {"key": "value"}

    def test_none_body(self, monkeypatch):
        class FakeRequest:
            def get_json(self, silent=True):
                return None
        req = FakeRequest()
        with pytest.raises(ValidationError, match="JSON object"):
            require_json_object(req)

    def test_list_body(self, monkeypatch):
        class FakeRequest:
            def get_json(self, silent=True):
                return [1, 2, 3]
        req = FakeRequest()
        with pytest.raises(ValidationError, match="JSON object"):
            require_json_object(req)