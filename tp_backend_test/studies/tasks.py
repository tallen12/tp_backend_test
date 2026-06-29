from typing import TYPE_CHECKING

from celery import shared_task
from django.conf import settings

from tp_backend_test.studies.models import NctSearchTask
from tp_backend_test.studies.models import UploadTask
from tp_backend_test.studies.services.process_file_upload import (
    ProcessFileUploadService,
)
from tp_backend_test.studies.services.process_nct_ids import ProcessNctIdService
from tp_backend_test.studies.services.process_nct_ids import StudyFetcherError
from tp_backend_test.studies.services.update_file_upload_status import (
    UpdateFileUploadOrchestratorService,
)
from tp_backend_test.studies.services.update_file_upload_status import (
    UpdateFileUploadStatusService,
)

if TYPE_CHECKING:
    import uuid

    from celery.result import AsyncResult


@shared_task
def orchestrator_celery_task():
    UpdateFileUploadOrchestratorService(
        upload_task_model_manager=UploadTask.objects,
        update_file_upload_status_job=CeleryUpdateFileUploadStatusService(),
    ).update_in_process_file_upload_status()


class CeleryUpdateFileUploadOrchestratorService:
    def schedule(self):
        return orchestrator_celery_task.delay()  # pyright: ignore[reportFunctionMemberAccess]


@shared_task
def update_celery_task(file_upload_id: uuid.UUID):
    UpdateFileUploadStatusService(UploadTask.objects).update_status(file_upload_id)


class CeleryUpdateFileUploadStatusService:
    def schedule(self, file_upload_id: uuid.UUID):
        return update_celery_task.delay(file_upload_id)  # pyright: ignore[reportFunctionMemberAccess]


# Defining this as a static method on the class had issues
@shared_task(
    autoretry_for=(StudyFetcherError,),
    max_retries=5,  # Stop after 5 attempts like in config
    default_retry_delay=5,
    retry_backoff=True,
    retry_jitter=True,
    bind=True,
)
def process_nct_id_celery_task(self, nct_id: str):
    ProcessNctIdService.factory(
        settings.CTGOV_API_BASE_URL,
        max_retries=5,
    ).process_nct_id(
        nct_id=nct_id,
        retries=self.request.retries,
    )


class CeleryProcessNctIdService:
    def schedule(self, nct_id: str) -> AsyncResult | None:
        return process_nct_id_celery_task.delay(nct_id)  # pyright: ignore[reportCallIssue]


class CeleryProcessFileUploadService:
    @staticmethod
    @shared_task
    def process_file_upload(file_upload_id: uuid.UUID):
        ProcessFileUploadService(
            upload_task_model_manager=UploadTask.objects,
            nct_search_task_model_manager=NctSearchTask.objects,
            nct_search_job=CeleryProcessNctIdService(),
        ).process_file_upload(
            file_upload_id=file_upload_id,
        )

    def schedule(self, upload_id: uuid.UUID) -> AsyncResult | None:
        return self.process_file_upload.apply_async(args=[upload_id])  # pyright: ignore[reportFunctionMemberAccess]
