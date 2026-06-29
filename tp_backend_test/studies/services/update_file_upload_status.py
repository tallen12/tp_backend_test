from typing import TYPE_CHECKING
from typing import Protocol

from tp_backend_test.studies.models import NctSearchTask
from tp_backend_test.studies.models import UploadTask

if TYPE_CHECKING:
    import uuid

    from celery.result import AsyncResult
    from django.db.models import QuerySet


# Interfaces used in this service
class UploadTaskModelManagerProtocol(Protocol):
    """Minimal subset of a Django model manager.

    Allows for easy mocking during unit tests (without the DB).
    """

    def get(self, pk: uuid.UUID) -> UploadTask: ...
    def filter(self, status: UploadTask.Status) -> QuerySet[UploadTask]: ...


class UpdateFileUploadStatusJobProtocol(Protocol):
    """Schedules the async job that runs the UpdateFileUploadStatus task.

    Implementations should enqueue work (e.g. via Celery) rather than
    executing it inline. You can run sync or mocked implementations for testing.
    """

    def schedule(self, file_upload_id: uuid.UUID) -> AsyncResult | None: ...


class UpdateFileUploadStatusService:
    @staticmethod
    def factory():
        return UpdateFileUploadStatusService(
            upload_task_model_manager=UploadTask.objects,
        )

    def __init__(self, upload_task_model_manager: UploadTaskModelManagerProtocol):
        self.upload_task_model_manager = upload_task_model_manager

    def update_status(self, file_upload_id: uuid.UUID):
        upload_task = self.upload_task_model_manager.get(pk=file_upload_id)
        search_tasks = upload_task.nctsearchtask_set.all()  # pyright: ignore[reportAttributeAccessIssue]
        all_status = {search_task.status for search_task in search_tasks}
        if all_status and NctSearchTask.Status.PROCESSING not in all_status:
            upload_task.status = UploadTask.Status.DONE
            upload_task.save()

    def schedule(self, file_upload_id: uuid.UUID):
        self.update_status(file_upload_id)


class UpdateFileUploadOrchestratorService:
    def __init__(
        self,
        upload_task_model_manager: UploadTaskModelManagerProtocol,
        update_file_upload_status_job: UpdateFileUploadStatusJobProtocol,
    ):
        self.upload_task_model_manager = upload_task_model_manager
        self.update_file_upload_status_job = update_file_upload_status_job

    def update_in_process_file_upload_status(self):
        results = self.upload_task_model_manager.filter(
            status=UploadTask.Status.PROCESSING,
        )
        for result in results:
            self.update_file_upload_status_job.schedule(file_upload_id=result.id)

    def schedule(self):
        self.update_in_process_file_upload_status()
