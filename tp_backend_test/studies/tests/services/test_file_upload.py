"""
Tests for FileUploadService

Makes use of dependency injection to easily mock services to test
everything being called correctly. Additional tests will cover implementation
(for example to make sure models are created correctly).
"""

from io import BytesIO
from unittest.mock import MagicMock

import pytest
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.test import SimpleTestCase

from tp_backend_test.studies.services.file_upload import FileUploadTaskService
from tp_backend_test.studies.services.file_upload import InvalidCsvError


def make_uploaded_file(
    content: bytes = b"col1,col2\nval1,val2",
) -> InMemoryUploadedFile:
    """Generate a mock django uploaded file."""
    return InMemoryUploadedFile(
        file=BytesIO(content),
        field_name="source_file",
        name="test.csv",
        content_type="text/csv",
        size=len(content),
        charset=None,
    )


def make_service(
    valid_csv: bool = True,  # noqa: FBT001, FBT002 It is ok for testing
    hash_return: str = "deadbeef",
    existing_task=None,
):
    """Setup test service with injected mock components."""
    mimetype_validator = MagicMock()
    mimetype_validator.validate.return_value = valid_csv

    file_upload_job = MagicMock()
    hash_method = MagicMock()
    hash_method.make_hash.return_value = hash_return

    model_manager = MagicMock()
    model_manager.filter.return_value.first.return_value = existing_task

    service = FileUploadTaskService(
        csv_validator=mimetype_validator,
        process_file_upload_job=file_upload_job,
        file_hasher=hash_method,
        model_manager=model_manager,
        on_commit=lambda func: func(),
    )
    return service, mimetype_validator, file_upload_job, hash_method, model_manager


class TestFileUploadTaskServiceCsv(SimpleTestCase):
    def test_raises_on_invalid_csv(self):
        service, _, _, _, _ = make_service(valid_csv=False)
        with pytest.raises(InvalidCsvError):
            service.get_or_create(make_uploaded_file())

    def test_mime_validator_called_with_file_bytes(self):
        content = b"col1,col2\nval1,val2"
        service, validator, _, _, _ = make_service(existing_task=MagicMock())
        service.get_or_create(make_uploaded_file(content))

        validator.validate.assert_called_once_with(
            data=content,
        )


class TestFileUploadTaskServiceHashing(SimpleTestCase):
    def test_hash_method_called_with_file_bytes(self):
        content = b"col1,col2\nval1,val2"
        service, _, _, hash_method, _ = make_service(existing_task=MagicMock())
        service.get_or_create(make_uploaded_file(content))

        hash_method.make_hash.assert_called_once_with(content)

    def test_file_seeked_before_read(self):
        service, _, _, hash_method, _ = make_service(existing_task=MagicMock())
        file = make_uploaded_file(b"data")
        file.read()  # advance pointer

        service.get_or_create(file)

        hash_method.make_hash.assert_called_once_with(b"data")


class TestFileUploadTaskServiceExistingTask(SimpleTestCase):
    def test_returns_existing_task(self):
        existing = MagicMock()
        service, _, _, _, _ = make_service(existing_task=existing)

        task, created = service.get_or_create(make_uploaded_file())

        assert task is existing
        assert not created

    def test_does_not_create_new_record(self):
        existing = MagicMock()
        service, _, _, _, manager = make_service(existing_task=existing)

        service.get_or_create(make_uploaded_file())

        manager.create.assert_not_called()

    def test_does_not_schedule_job(self):
        existing = MagicMock()
        service, _, job, _, _ = make_service(existing_task=existing)

        service.get_or_create(make_uploaded_file())

        job.schedule.assert_not_called()


class TestFileUploadTaskServiceNewTask(SimpleTestCase):
    def test_creates_new_task(self):
        new_task = MagicMock()
        service, _, _, _, manager = make_service(existing_task=None)
        manager.create.return_value = new_task

        task, created = service.get_or_create(make_uploaded_file())

        assert task is new_task
        assert created

    def test_create_called_with_file_and_hash(self):
        service, _, _, _, manager = make_service(
            existing_task=None,
            hash_return="deadbeef",
        )
        file = make_uploaded_file()

        service.get_or_create(file)

        manager.create.assert_called_once_with(source_file=file, file_hash="deadbeef")

    def test_schedules_job_with_new_task_id(self):
        new_task = MagicMock()
        service, _, job, _, manager = make_service(existing_task=None)
        manager.create.return_value = new_task

        service.get_or_create(make_uploaded_file())

        job.schedule.assert_called_once_with(new_task.id)
