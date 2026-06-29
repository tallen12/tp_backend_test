from unittest.mock import MagicMock
from unittest.mock import call

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
    nct_search_job = MagicMock()
    ProcessFileUploadService(
        upload_task_model_manager=UploadTask.objects,
        nct_search_task_model_manager=NctSearchTask.objects,
        nct_search_job=nct_search_job,  # Mock to not trigger additional jobs
    ).process_file_upload(file_upload_id=task.id)
    assert NctSearchTask.objects.count() == len(ids)
    assert UploadTask.objects.get(pk=task.id).status == UploadTask.Status.PROCESSING
    nct_search_job.schedule.assert_has_calls(
        [call(_id.decode("utf-8")) for _id in ids],
        any_order=True,  # drop this if order matters
    )
