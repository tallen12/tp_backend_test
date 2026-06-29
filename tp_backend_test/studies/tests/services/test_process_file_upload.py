import pytest

from tp_backend_test.studies.models import NctSearchTask
from tp_backend_test.studies.models import UploadTask
from tp_backend_test.studies.services.process_file_upload import (
    ProcessFileUploadService,
)
from tp_backend_test.studies.tests.helpers import make_uploaded_file

pytestmark = pytest.mark.django_db


def test_process_file_upload(settings):
    """Make sure ProcessFileUploadJobService successfully processes the csv."""
    ids = [b"NCT06596772", b"NCT05660161", b"NCT07641023"]

    task = UploadTask.objects.create(
        source_file=make_uploaded_file(
            b"\n".join([b"NCT Number", *ids]),
        ),
        file_hash="whatever",  # Hash doesn't matter for this test
    )
    ProcessFileUploadService(
        upload_task_model_manager=UploadTask.objects,
        nct_search_task_model_manager=NctSearchTask.objects,
    ).process_file_upload(file_upload_id=task.id)  # pyright: ignore[reportAttributeAccessIssue] Need to type correctly
    assert NctSearchTask.objects.count() == len(ids)


def test_process_file_upload_task(settings):
    """A basic test to make sure process file upload works with celery."""
    ids = [b"NCT06596772", b"NCT05660161", b"NCT07641023"]

    task = UploadTask.objects.create(
        source_file=make_uploaded_file(
            b"\n".join([b"NCT Number", *ids]),
        ),
        file_hash="whatever",  # Hash doesn't matter for this test
    )
    settings.CELERY_TASK_ALWAYS_EAGER = True
    ProcessFileUploadService(
        upload_task_model_manager=UploadTask.objects,
        nct_search_task_model_manager=NctSearchTask.objects,
    ).process_file_upload(file_upload_id=task.id)  # pyright: ignore[reportAttributeAccessIssue] Need to type correctly
    assert NctSearchTask.objects.count() == len(ids)
