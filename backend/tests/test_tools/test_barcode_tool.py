"""Tests for barcode_tool.py — EAN-13 validation and generation."""

import pytest
from tools.barcode_tool import validate_ean13, generate_ean13


def test_validate_ean13_valid():
    """Should validate a correct EAN-13."""
    result = validate_ean13("5901234123457")
    assert result["status"] == "valid"


def test_validate_ean13_invalid():
    """Should reject an incorrect EAN-13 (wrong checksum)."""
    result = validate_ean13("5901234123450")
    assert result["valid_checksum"] is False


def test_validate_ean13_invalid_length():
    """Should reject too-short or too-long codes."""
    short = validate_ean13("123")
    assert short["status"] == "invalid"
    long = validate_ean13("12345678901234")
    assert long["status"] == "invalid"


def test_validate_ean13_empty():
    """Should reject empty string."""
    result = validate_ean13("")
    assert result["status"] == "invalid"


def test_validate_ean13_non_numeric():
    """Should reject non-numeric input."""
    result = validate_ean13("ABCDEFGHIJKLM")
    assert result["status"] == "invalid"


def test_generate_ean13():
    """Should generate a valid EAN-13."""
    result = generate_ean13()
    assert result["status"] == "ok"
    assert len(result["barcode"]) == 13
    assert result["barcode"].isdigit()


def test_generate_ean13_with_base():
    """Should generate EAN-13 from first 12 digits."""
    result = generate_ean13(base="400638133393")
    assert result["status"] == "ok"
    assert result["barcode"].startswith("400638133393")


def test_generate_ean13_checksum():
    """The generated barcode should have the correct checksum."""
    result = generate_ean13(base="400638133393")
    barcode = result["barcode"]
    weights = [1, 3, 1, 3, 1, 3, 1, 3, 1, 3, 1, 3]
    total = sum(int(barcode[i]) * weights[i] for i in range(12))
    expected_checksum = (10 - (total % 10)) % 10
    assert int(barcode[12]) == expected_checksum


def test_generate_ean13_strips_non_digits():
    """Should strip non-digit characters from base."""
    result = generate_ean13(base="4006-3813-3393")
    assert result["status"] == "ok"
    assert len(result["barcode"]) == 13