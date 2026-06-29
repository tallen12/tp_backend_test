from unittest.mock import Mock

import pytest

from tp_backend_test.studies.models import NctSearchTask
from tp_backend_test.studies.models import UploadTask
from tp_backend_test.studies.services.update_file_upload_status import (
    UpdateFileUploadOrchestratorService,
)
from tp_backend_test.studies.services.update_file_upload_status import (
    UpdateFileUploadStatusService,
)
from tp_backend_test.studies.tests.helpers import make_uploaded_file


# This service is simple enough it isn't worth setting up mocks
@pytest.mark.django_db
def test_update_file_upload_status():
    """Make sure UpdateFileUploadStatusService works.

    If nothing is in process set the upload file status to done.
    """
    ids = [b"NCT06596772"]
    nct_id = ids[0].decode("utf-8")

    upload_task = UploadTask.objects.create(
        source_file=make_uploaded_file(
            b"\n".join([b"NCT Number", *ids]),
        ),
        file_hash="whatever",  # Hash doesn't matter for this test
        status=UploadTask.Status.PROCESSING,
    )
    NctSearchTask.objects.create(
        upload_task_id=upload_task.id,
        nct_id=nct_id,
        status=NctSearchTask.Status.DONE,
    )
    NctSearchTask.objects.create(
        upload_task_id=upload_task.id,
        nct_id=nct_id,
        status=NctSearchTask.Status.DONE,
    )

    UpdateFileUploadStatusService(
        upload_task_model_manager=UploadTask.objects,
    ).update_status(upload_task.id)

    assert UploadTask.objects.get(id=upload_task.id).status == UploadTask.Status.DONE


@pytest.mark.django_db
def test_update_file_upload_still_processing():
    """Make sure UpdateFileUploadStatusService works.

    If something is in process don't set the status.
    """
    ids = [b"NCT06596772"]
    nct_id = ids[0].decode("utf-8")

    upload_task = UploadTask.objects.create(
        source_file=make_uploaded_file(
            b"\n".join([b"NCT Number", *ids]),
        ),
        file_hash="whatever",  # Hash doesn't matter for this test
        status=UploadTask.Status.PROCESSING,
    )
    NctSearchTask.objects.create(
        upload_task_id=upload_task.id,
        nct_id=nct_id,
        status=NctSearchTask.Status.DONE,
    )
    NctSearchTask.objects.create(
        upload_task_id=upload_task.id,
        nct_id=nct_id,
        status=NctSearchTask.Status.PROCESSING,
    )

    UpdateFileUploadStatusService(
        upload_task_model_manager=UploadTask.objects,
    ).update_status(upload_task.id)

    assert (
        UploadTask.objects.get(id=upload_task.id).status == UploadTask.Status.PROCESSING
    )


@pytest.mark.django_db
def test_update_in_process_file_upload_status_schedules_processing_uploads():
    """Make sure processing uploads have status update jobs scheduled."""

    upload_task = UploadTask.objects.create(
        source_file=make_uploaded_file(
            b"\n".join([b"NCT Number", b"NCT06596772"]),
        ),
        file_hash="whatever",
        status=UploadTask.Status.PROCESSING,
    )
    UploadTask.objects.create(
        source_file=make_uploaded_file(
            b"\n".join([b"NCT Number", b"NCT06596772"]),
        ),
        file_hash="whatever2",
        status=UploadTask.Status.DONE,
    )

    UploadTask.objects.create(
        source_file=make_uploaded_file(
            b"\n".join([b"NCT Number", b"NCT06596772"]),
        ),
        file_hash="whatever3",
        status=UploadTask.Status.NEW,
    )

    update_file_upload_status_job = Mock()

    service = UpdateFileUploadOrchestratorService(
        upload_task_model_manager=UploadTask.objects,
        update_file_upload_status_job=update_file_upload_status_job,
    )

    service.schedule()

    update_file_upload_status_job.schedule.assert_called_once_with(
        file_upload_id=upload_task.id,
    )
