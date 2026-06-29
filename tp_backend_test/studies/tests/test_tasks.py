import pytest

from tp_backend_test.studies.models import NctSearchTask
from tp_backend_test.studies.models import Study
from tp_backend_test.studies.models import UploadTask
from tp_backend_test.studies.tasks import CeleryProcessFileUploadService
from tp_backend_test.studies.tasks import CeleryProcessNctIdService
from tp_backend_test.studies.tasks import CeleryUpdateFileUploadStatusService
from tp_backend_test.studies.tests.helpers import make_uploaded_file


@pytest.mark.django_db
def test_update_file_upload_still_processing_celery(settings):
    """Test if it works through celery."""
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
    settings.CELERY_TASK_ALWAYS_EAGER = True

    CeleryUpdateFileUploadStatusService().schedule(upload_task.id).wait()  # pyright: ignore[reportAttributeAccessIssue]

    assert (
        UploadTask.objects.get(id=upload_task.id).status == UploadTask.Status.PROCESSING
    )


@pytest.mark.django_db
def test_process_nct_ids_celery(settings):
    """Make sure ProcessFileUploadJobService successfully processes the csv."""
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
    settings.CELERY_TASK_ALWAYS_EAGER = True
    CeleryProcessNctIdService().schedule(nct_id=nct_id).wait()  # pyright: ignore[reportOptionalMemberAccess]
    assert (
        NctSearchTask.objects.get(id=search_task.id).status == NctSearchTask.Status.DONE
    )
    assert Study.objects.filter(nct_id=nct_id).count() == 1


@pytest.mark.django_db
def test_process_file_upload_task_celery(settings):
    """A basic test to make sure process file upload works with celery."""
    ids = [b"NCT06596772", b"NCT05660161", b"NCT07641023"]

    task = UploadTask.objects.create(
        source_file=make_uploaded_file(
            b"\n".join([b"NCT Number", *ids]),
        ),
        file_hash="whatever",  # Hash doesn't matter for this test
    )
    settings.CELERY_TASK_ALWAYS_EAGER = True
    CeleryProcessFileUploadService().schedule(upload_id=task.id).wait()  # pyright: ignore[reportOptionalMemberAccess]
    assert NctSearchTask.objects.count() == len(ids)
    assert UploadTask.objects.get(pk=task.id).status == UploadTask.Status.PROCESSING
