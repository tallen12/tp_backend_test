import csv
import io
import itertools
from typing import TYPE_CHECKING
from typing import Protocol

from celery import shared_task

from tp_backend_test.studies.models import NctSearchTask
from tp_backend_test.studies.models import UploadTask

if TYPE_CHECKING:
    import uuid
    from collections.abc import Iterable

    from celery.result import AsyncResult


class UploadTaskModelManagerProtocol(Protocol):
    """Minimal subset of a Django model manager used by FileUploadTaskService.

    Allows for easy mocking during unit tests (without the DB).
    """

    def get(self, pk: uuid.UUID) -> UploadTask: ...


class NctSearchTaskModelManagerProtocol(Protocol):
    """Minimal subset of a Django model manager used by FileUploadTaskService.

    Allows for easy mocking during unit tests (without the DB).
    """

    def bulk_create(self, objs: Iterable[NctSearchTask]) -> list[NctSearchTask]: ...


class ProcessFileUploadJobService:
    @staticmethod
    def factory():
        return ProcessFileUploadJobService(
            upload_task_model_manager=UploadTask.objects,
            nct_search_task_model_manager=NctSearchTask.objects,
        )

    def __init__(
        self,
        upload_task_model_manager: UploadTaskModelManagerProtocol,
        nct_search_task_model_manager: NctSearchTaskModelManagerProtocol,
    ):
        self.upload_task_model_manager = upload_task_model_manager
        self.nct_search_task_model_manager = nct_search_task_model_manager

    def process_file_upload(self, file_upload_id: uuid.UUID):
        """Parse csv and generate NctSearchTasks for each NCT ID."""
        upload_task = self.upload_task_model_manager.get(pk=file_upload_id)
        with upload_task.source_file.open(mode="rb") as f:
            reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"))
            insert_ids, _job_ids = itertools.tee(
                reader,
            )  # Will add once get that service done.
            # This is already validated so we can assume that it is a single row csv
            self.nct_search_task_model_manager.bulk_create(
                [
                    NctSearchTask(nct_id=row["NCT Number"], upload_task=upload_task)
                    for row in insert_ids
                    if row
                ],
            )


class CeleryProcessFileUploadJobService:
    @staticmethod
    @shared_task
    def celery_task(file_upload_id: uuid.UUID):
        ProcessFileUploadJobService.factory().process_file_upload(
            file_upload_id=file_upload_id,
        )

    def schedule(self, upload_id: uuid.UUID) -> AsyncResult | None:
        return self.celery_task.apply_async(args=[upload_id])  # pyright: ignore[reportFunctionMemberAccess]
