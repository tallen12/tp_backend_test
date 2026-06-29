from unittest.mock import patch

import pytest

from tp_backend_test.studies.services.csv_validator import NctIdCsvValidatorService


@pytest.fixture
def validator():
    return NctIdCsvValidatorService()


def test_valid_csv(validator):
    data = b"NCT Number,Title,Status\nNCT001,Study A,Active"
    assert validator.validate(data) is True


def test_missing_header(validator):
    data = b"Title,Status\nStudy A,Active"
    assert validator.validate(data) is False


def test_empty_bytes(validator):
    assert validator.validate(b"") is False


def test_single_column(validator):
    data = b"NCT Number\nNCT001\nNCT002"
    assert validator.validate(data) is True


def test_header_in_second_line_not_first(validator):
    data = b"junk\nNCT Number,Title"
    assert validator.validate(data) is False


def test_binary_data(validator):
    data = bytes(range(256))
    assert validator.validate(data) is False


def test_chardet_returns_none_falls_back_to_utf8(validator):
    data = b"NCT Number,Title"
    with patch("chardet.detect", return_value={"encoding": None}):
        assert validator.validate(data) is True
