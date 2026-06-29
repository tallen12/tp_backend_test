from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
import requests

from tp_backend_test.studies.services.process_nct_ids import StudyFetcher
from tp_backend_test.studies.services.process_nct_ids import StudyNotFoundError
from tp_backend_test.studies.services.process_nct_ids import StudyServerError
from tp_backend_test.studies.services.process_nct_ids import StudyTimeoutError

BASE_URL = "http://fake-api.example.com"
NCT_ID = "NCT06596772"


@pytest.fixture
def fetcher():
    return StudyFetcher(ct_gov_url=BASE_URL)


def make_response(status_code: int, json_data: dict | None = None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.raise_for_status.side_effect = (
        requests.exceptions.HTTPError(response=resp) if status_code >= 400 else None  # noqa: PLR2004
    )
    return resp


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@patch("tp_backend_test.studies.services.process_nct_ids.requests.get")
def test_fetch_data_returns_json_on_200(mock_get, fetcher):
    payload = {"protocolSection": {"identificationModule": {"nctId": NCT_ID}}}
    mock_get.return_value = make_response(200, payload)

    result = fetcher.fetch_data(NCT_ID)

    mock_get.assert_called_once_with(f"{BASE_URL}/api/v2/studies/{NCT_ID}", timeout=5)
    assert result == payload


# ---------------------------------------------------------------------------
# HTTP errors
# ---------------------------------------------------------------------------


@patch("tp_backend_test.studies.services.process_nct_ids.requests.get")
def test_fetch_data_raises_study_not_found_on_404(mock_get, fetcher):
    mock_get.return_value = make_response(404)

    with pytest.raises(StudyNotFoundError) as exc_info:
        fetcher.fetch_data(NCT_ID)

    assert exc_info.value.nct_id == NCT_ID


@patch("tp_backend_test.studies.services.process_nct_ids.requests.get")
def test_fetch_data_raises_study_server_error_on_500(mock_get, fetcher):
    mock_get.return_value = make_response(500)

    with pytest.raises(StudyServerError) as exc_info:
        fetcher.fetch_data(NCT_ID)

    assert exc_info.value.nct_id == NCT_ID
    assert exc_info.value.status_code == 500  # noqa: PLR2004


@patch("tp_backend_test.studies.services.process_nct_ids.requests.get")
def test_fetch_data_raises_study_server_error_on_503(mock_get, fetcher):
    mock_get.return_value = make_response(503)

    with pytest.raises(StudyServerError) as exc_info:
        fetcher.fetch_data(NCT_ID)

    assert exc_info.value.status_code == 503  # noqa: PLR2004


@patch("tp_backend_test.studies.services.process_nct_ids.requests.get")
def test_fetch_data_reraises_unhandled_http_error(mock_get, fetcher):
    """A 4xx that isn't 404 (e.g. 403) should propagate as a raw HTTPError."""
    mock_get.return_value = make_response(403)

    with pytest.raises(requests.exceptions.HTTPError):
        fetcher.fetch_data(NCT_ID)


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------


@patch("tp_backend_test.studies.services.process_nct_ids.requests.get")
def test_fetch_data_raises_study_timeout_on_read_timeout(mock_get, fetcher):
    mock_get.side_effect = requests.exceptions.ReadTimeout()

    with pytest.raises(StudyTimeoutError) as exc_info:
        fetcher.fetch_data(NCT_ID)

    assert exc_info.value.nct_id == NCT_ID


# ---------------------------------------------------------------------------
# Exception chaining
# ---------------------------------------------------------------------------


@patch("tp_backend_test.studies.services.process_nct_ids.requests.get")
def test_study_not_found_chains_original_exception(mock_get, fetcher):
    mock_get.return_value = make_response(404)

    with pytest.raises(StudyNotFoundError) as exc_info:
        fetcher.fetch_data(NCT_ID)

    assert isinstance(exc_info.value.__cause__, requests.exceptions.HTTPError)


@patch("tp_backend_test.studies.services.process_nct_ids.requests.get")
def test_study_timeout_chains_original_exception(mock_get, fetcher):
    mock_get.side_effect = requests.exceptions.ReadTimeout()

    with pytest.raises(StudyTimeoutError) as exc_info:
        fetcher.fetch_data(NCT_ID)

    assert isinstance(exc_info.value.__cause__, requests.exceptions.ReadTimeout)
