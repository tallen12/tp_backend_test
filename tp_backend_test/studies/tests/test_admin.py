from http import HTTPStatus

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from tp_backend_test.studies.models import UploadTask

pytestmark = pytest.mark.django_db


def test_study_admin_changelist_loads(admin_client):
    response = admin_client.get(reverse("admin:studies_study_changelist"))

    assert response.status_code == HTTPStatus.OK


def test_upload_task_admin_accepts_csv_upload(admin_client):
    url = reverse("admin:studies_uploadtask_add")
    response = admin_client.get(url)

    assert response.status_code == HTTPStatus.OK

    csv_file = SimpleUploadedFile(
        "nct_ids.csv",
        b"NCT Number\nNCT00000001\n",
        content_type="text/csv",
    )
    response = admin_client.post(
        url,
        data={
            "source_file": csv_file,
        },
    )

    context_data = getattr(response, "context_data", None)
    form_errors = context_data["adminform"].form.errors if context_data else {}
    assert response.status_code == HTTPStatus.FOUND, form_errors
    upload_task = UploadTask.objects.get()
    assert upload_task.source_file.name.startswith("study_uploads/")


def test_upload_task_admin_returns_existing_task_on_duplicate(admin_client):
    url = reverse("admin:studies_uploadtask_add")
    csv_content = b"NCT Number\nNCT00000001\n"

    first_file = SimpleUploadedFile("nct_ids.csv", csv_content, content_type="text/csv")
    admin_client.post(url, data={"source_file": first_file})
    assert UploadTask.objects.count() == 1
    original_task = UploadTask.objects.get()

    second_file = SimpleUploadedFile(
        "nct_ids.csv",
        csv_content,
        content_type="text/csv",
    )
    response = admin_client.post(url, data={"source_file": second_file})

    # Still redirects — not an error, just returns the existing task
    assert response.status_code == HTTPStatus.FOUND
    assert UploadTask.objects.count() == 1
    assert UploadTask.objects.get().pk == original_task.pk
