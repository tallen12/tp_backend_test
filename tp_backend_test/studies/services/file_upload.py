from typing import TYPE_CHECKING
from typing import Any
from typing import Protocol

from django.db import transaction

from tp_backend_test.studies.models import UploadTask
from tp_backend_test.studies.services.csv_validator import NctIdCsvValidatorService
from tp_backend_test.studies.services.file_hasher import FileHasherService
from tp_backend_test.studies.services.process_file_upload import (
    CeleryProcessFileUploadJobService,
)

if TYPE_CHECKING:
    import uuid
    from collections.abc import Callable
    from typing import Self

    from celery.result import AsyncResult
    from django.core.files.uploadedfile import InMemoryUploadedFile
    from django.core.files.uploadedfile import TemporaryUploadedFile


# Custom errors used by this service
class InvalidCsvError(ValueError):
    """Raised when an uploaded file's is not a valid csv."""


# Protocols to make an interface for dependency injection
# Optional since type enforcement is limited because of django
# but I still find useful for documentation
class FileUploadTaskProtocol(Protocol):
    """Protocol for creating file upload tasks."""

    def create_file_upload(self, file_data: bytes) -> UploadTask: ...


class IsValidCsvProtocol(Protocol):
    """Protocol that validates file content match one of a set of allowed MIME types."""

    def validate(self, data: bytes) -> bool: ...


class ProcessFileUploadJobProtocol(Protocol):
    """Schedules the async job that processes an upload task.

    Implementations should enqueue work (e.g. via Celery) rather than
    executing it inline. You can run sync or mocked implementations for testing.
    """

    def schedule(self, upload_id: uuid.UUID) -> AsyncResult | None: ...


class FileHashProtocol(Protocol):
    """Produces a deterministic hash of raw file bytes.

    The hash is used to detect duplicate uploads before persisting anything
    to the database.
    """

    def make_hash(self, data: bytes) -> str: ...


class ModelManagerProtocol(Protocol):
    """Minimal subset of a Django model manager used by FileUploadTaskService.

    Allows for easy mocking during unit tests (without the DB).
    """

    def create(self, **kwargs) -> UploadTask: ...
    def filter(self, **kwargs) -> Self: ...
    def first(self) -> UploadTask | None: ...


class OnCommitProtocol(Protocol):
    """Protocol to handle the django transaction.on_commit dependency injection."""

    def __call__(self, func: Callable[[], Any]) -> None: ...


class FileUploadTaskService:
    """Service that orchestrates the ingestion of a CSV file into an UploadTask.

    Steps performed by `get_or_create`:
        1. Read and validate the file's MIME type against `valid_mimetypes`.
        2. Hash the file contents.
        3. Check whether a task with that hash already exists.
        4. If it does, return the existing task without scheduling duplicate work.
        5. If it doesn't, persist a new UploadTask and schedule the processing job.

    All dependencies are injected, so each concern (validation, hashing,
    persistence, job scheduling) can be swapped or mocked independently.
    """

    @staticmethod
    def factory():
        """Factory method to help setup concrete version with the standard depdencies.

        For this simple use case keep it inside the class.

        More complicated services may need to have this as a seperate class if for
        instance need to configure services with configs.
        """
        return FileUploadTaskService(
            csv_validator=NctIdCsvValidatorService(),
            process_file_upload_job=CeleryProcessFileUploadJobService(),
            file_hasher=FileHasherService(),
            model_manager=UploadTask.objects,
            on_commit=transaction.on_commit,
        )

    def __init__(
        self,
        csv_validator: IsValidCsvProtocol,
        process_file_upload_job: ProcessFileUploadJobProtocol,
        file_hasher: FileHashProtocol,
        model_manager: ModelManagerProtocol,
        on_commit: OnCommitProtocol,
    ):
        self.mimetype_validator = csv_validator
        self.file_upload_job = process_file_upload_job
        self.hash_method = file_hasher
        self.model_manager = model_manager
        self.on_commit = on_commit

    def get_or_create(
        self,
        file: InMemoryUploadedFile | TemporaryUploadedFile,
    ) -> tuple[UploadTask, bool]:
        """Return an UploadTask for the given file, creating one if needed.

        Args:
            file: The uploaded file object from Django's request handling.

        Returns:
            A ``(task, created)`` tuple. ``created`` is ``True`` when a new
            task was inserted and its processing job was scheduled, ``False``
            when a task for this file already existed.

        Raises:
            InvalidMimeTypeError: If the file's detected MIME type is not in
                ``valid_mimetypes``.
        """
        file.seek(0)
        file_data = file.read()
        if not self.mimetype_validator.validate(
            data=file_data,
        ):
            error_msg = "This file is not a valid csv."
            raise InvalidCsvError(error_msg)
        file_hash = self.hash_method.make_hash(file_data)
        existing_task = self.model_manager.filter(file_hash=file_hash).first()
        if existing_task:
            return existing_task, False
        new_task = self.model_manager.create(
            source_file=file,
            file_hash=file_hash,
        )
        # Need to make sure to wait until commit
        # to trigger the job to avoid race conditions
        self.on_commit(lambda: self.file_upload_job.schedule(new_task.id))

        return new_task, True
