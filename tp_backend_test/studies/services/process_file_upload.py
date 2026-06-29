import csv
import io
import itertools
from typing import TYPE_CHECKING
from typing import Protocol

from tp_backend_test.studies.models import NctSearchTask
from tp_backend_test.studies.models import UploadTask

if TYPE_CHECKING:
    import uuid
    from collections.abc import Iterable
    from collections.abc import Sequence

    from celery.result import AsyncResult


class UploadTaskModelManagerProtocol(Protocol):
    """Minimal subset of a Django model manager.

    Allows for easy mocking during unit tests (without the DB).
    """

    def get(self, pk: uuid.UUID) -> UploadTask: ...


class NctSearchTaskModelManagerProtocol(Protocol):
    """Minimal subset of a Django model manager.

    Allows for easy mocking during unit tests (without the DB).
    """

    def bulk_create(  # noqa: PLR0913
        self,
        objs: Iterable[NctSearchTask],
        batch_size: int | None = ...,
        ignore_conflicts: bool = ...,  # noqa: FBT001
        update_conflicts: bool | None = ...,  # noqa: FBT001
        update_fields: Sequence[str] | None = ...,
        unique_fields: Sequence[str] | None = ...,
    ) -> list[NctSearchTask]: ...


class ProcessNctSearchJobProtocol(Protocol):
    """Schedules the async job that processes an upload task.

    Implementations should enqueue work (e.g. via Celery) rather than
    executing it inline. You can run sync or mocked implementations for testing.
    """

    def schedule(self, nct_id: str) -> AsyncResult | None: ...


class ProcessFileUploadService:
    def __init__(
        self,
        upload_task_model_manager: UploadTaskModelManagerProtocol,
        nct_search_task_model_manager: NctSearchTaskModelManagerProtocol,
        nct_search_job: ProcessNctSearchJobProtocol,
    ):
        self.upload_task_model_manager = upload_task_model_manager
        self.nct_search_task_model_manager = nct_search_task_model_manager
        self.nct_search_job = nct_search_job

    def process_file_upload(self, file_upload_id: uuid.UUID):
        """Parse csv and generate NctSearchTasks for each NCT ID."""
        upload_task = self.upload_task_model_manager.get(pk=file_upload_id)
        with upload_task.source_file.open(mode="rb") as f:
            # It apparently needs TextIOWrapper to work
            reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"))
            insert_ids, job_ids = itertools.tee(
                reader,
            )
            # This is already validated so we can assume that it is a single row csv
            self.nct_search_task_model_manager.bulk_create(
                [
                    NctSearchTask(nct_id=row["NCT Number"], upload_task=upload_task)
                    for row in insert_ids
                    if row
                ],
                ignore_conflicts=True,
            )
            # Maybe a more elegant way to do this without teeing the iterator
            # but not thinking too hard right now
            for row in job_ids:
                self.nct_search_job.schedule(row["NCT Number"])
        upload_task.status = UploadTask.Status.PROCESSING
        upload_task.save(update_fields=["status"])
