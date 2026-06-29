import uuid
from unittest.mock import MagicMock

import pytest

from tp_backend_test.studies.models import NctSearchTask
from tp_backend_test.studies.models import Study
from tp_backend_test.studies.models import UploadTask
from tp_backend_test.studies.services.process_nct_ids import ProcessNctIdService
from tp_backend_test.studies.services.process_nct_ids import StudyFetcher
from tp_backend_test.studies.services.process_nct_ids import StudyNotFoundError
from tp_backend_test.studies.services.process_nct_ids import StudyServerError
from tp_backend_test.studies.services.process_nct_ids import StudyTimeoutError
from tp_backend_test.studies.tests.helpers import make_uploaded_file

API_RESPONSE = {
    "protocolSection": {
        "identificationModule": {
            "nctId": "NCT06596772",
            "briefTitle": "A Brief Title",
            "officialTitle": "An Official Title",
        },
        "statusModule": {"overallStatus": "RECRUITING"},
        "conditionsModule": {"conditions": ["Diabetes", "Obesity"]},
        "designModule": {"studyType": "INTERVENTIONAL"},
        "descriptionModule": {"briefSummary": "A brief summary."},
        "sponsorCollaboratorsModule": {"leadSponsor": {"name": "ACME Corp"}},
    },
}


def make_service(
    fetcher=None,
    study_manager=None,
    nct_search_manager=None,
    max_retries=3,
):
    """Helper to build a ProcessNctIdService with sensible mock defaults."""
    if fetcher is None:
        fetcher = MagicMock(spec=StudyFetcher)
        fetcher.fetch_data.return_value = API_RESPONSE

    if study_manager is None:
        study_manager = MagicMock()
        study_manager.filter.return_value.first.return_value = None  # no existing study

    if nct_search_manager is None:
        nct_search_manager = MagicMock()
        nct_search_manager.filter.return_value.update.return_value = None

    return ProcessNctIdService(
        study_fetcher=fetcher,
        study_manager=study_manager,
        nct_search_manager=nct_search_manager,
        max_retries=max_retries,
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_process_nct_id_creates_study_when_not_existing():
    """Fetches and saves a study that doesn't exist yet."""
    nct_id = "NCT06596772"
    mock_study = MagicMock(id=uuid.uuid4())

    study_manager = MagicMock()
    study_manager.filter.return_value.first.return_value = None
    study_manager.update_or_create.return_value = mock_study, True

    nct_search_manager = MagicMock()
    nct_search_manager.filter.return_value.update.return_value = None

    make_service(
        study_manager=study_manager,
        nct_search_manager=nct_search_manager,
    ).process_nct_id(nct_id)

    study_manager.update_or_create.assert_called_once()
    nct_search_manager.filter.return_value.update.assert_called_once_with(
        status=NctSearchTask.Status.DONE,
        study_id=mock_study.id,
    )


def test_process_nct_id_skips_fetch_when_study_exists():
    """Does not call the fetcher when the study already exists in the DB."""
    nct_id = "NCT06596772"
    mock_study = MagicMock(id=uuid.uuid4())

    fetcher = MagicMock(spec=StudyFetcher)
    study_manager = MagicMock()
    study_manager.filter.return_value.first.return_value = mock_study

    nct_search_manager = MagicMock()

    make_service(
        fetcher=fetcher,
        study_manager=study_manager,
        nct_search_manager=nct_search_manager,
    ).process_nct_id(nct_id)

    fetcher.fetch_data.assert_not_called()
    nct_search_manager.filter.return_value.update.assert_called_once_with(
        status=NctSearchTask.Status.DONE,
        study_id=mock_study.id,
    )


def test_parse_data_extracts_all_fields():
    """parse_data correctly maps every field from the API response."""
    service = make_service()
    result = service.parse_data(API_RESPONSE)

    assert result["nct_id"] == "NCT06596772"
    assert result["brief_title"] == "A Brief Title"
    assert result["official_title"] == "An Official Title"
    assert result["overall_status"] == "RECRUITING"
    assert result["conditions"] == ["Diabetes", "Obesity"]
    assert result["study_type"] == "INTERVENTIONAL"
    assert result["brief_summary"] == "A brief summary."
    assert result["sponsor_primary_key"] == "ACME Corp"


def test_parse_data_tolerates_missing_sections():
    """parse_data returns empty defaults when sections are absent."""
    service = make_service()
    result = service.parse_data({})

    assert result["nct_id"] == ""
    assert result["conditions"] == []
    assert result["sponsor_primary_key"] == ""


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_process_nct_id_sets_failure_on_not_found():
    """Sets FAILURE status and re-raises when the study doesn't exist in the API."""
    nct_id = "NCT00000000"

    fetcher = MagicMock(spec=StudyFetcher)
    fetcher.fetch_data.side_effect = StudyNotFoundError(nct_id)

    study_manager = MagicMock()
    study_manager.filter.return_value.first.return_value = None

    nct_search_manager = MagicMock()

    service = make_service(
        fetcher=fetcher,
        study_manager=study_manager,
        nct_search_manager=nct_search_manager,
    )

    service.process_nct_id(nct_id)

    nct_search_manager.filter.return_value.update.assert_called_once_with(
        status=NctSearchTask.Status.NOT_FOUND,
        study_id=None,
    )


def test_process_nct_id_sets_failure_after_max_retries_exceeded():
    """Sets FAILURE status when a transient error outlasts the retry budget."""
    nct_id = "NCT06596772"

    fetcher = MagicMock(spec=StudyFetcher)
    fetcher.fetch_data.side_effect = StudyServerError(nct_id, 503)

    study_manager = MagicMock()
    study_manager.filter.return_value.first.return_value = None

    nct_search_manager = MagicMock()

    service = make_service(
        fetcher=fetcher,
        study_manager=study_manager,
        nct_search_manager=nct_search_manager,
        max_retries=2,
    )

    service.process_nct_id(nct_id, retries=3)  # retries > max_retries

    nct_search_manager.filter.return_value.update.assert_called_once_with(
        status=NctSearchTask.Status.FAILURE,
        study_id=None,
    )


def test_process_nct_id_stays_processing_before_max_retries():
    """Does not set FAILURE when there are still retries remaining."""
    nct_id = "NCT06596772"

    fetcher = MagicMock(spec=StudyFetcher)
    fetcher.fetch_data.side_effect = StudyTimeoutError(nct_id)

    study_manager = MagicMock()
    study_manager.filter.return_value.first.return_value = None

    nct_search_manager = MagicMock()

    service = make_service(
        fetcher=fetcher,
        study_manager=study_manager,
        nct_search_manager=nct_search_manager,
        max_retries=5,
    )

    with pytest.raises(StudyTimeoutError):
        service.process_nct_id(nct_id, retries=1)  # retries <= max_retries

    nct_search_manager.filter.return_value.update.assert_called_once_with(
        status=NctSearchTask.Status.PROCESSING,
        study_id=None,
    )


# Integration test to make sure it works correctly on db
@pytest.mark.django_db
def test_process_nct_ids(settings):
    """Make sure ProcessNctIdService searches for the nct-id."""
    ids = [b"NCT06596772"]
    nct_id = ids[0].decode("utf-8")

    upload_task = UploadTask.objects.create(
        source_file=make_uploaded_file(
            b"\n".join([b"NCT Number", *ids]),
        ),
        file_hash="whatever",  # Hash doesn't matter for this test
    )
    search_task = NctSearchTask.objects.create(
        upload_task_id=upload_task.id,
        nct_id=nct_id,
    )
    # This techincally hits the configured service.
    # For this case I don't think it matters in actual real code I will be more careful
    # to mock it (using mountebank or something)
    ProcessNctIdService.factory(settings.CTGOV_API_BASE_URL).process_nct_id(nct_id)
    assert (
        NctSearchTask.objects.get(id=search_task.id).status == NctSearchTask.Status.DONE
    )
    assert Study.objects.filter(nct_id=nct_id).count() == 1
