import pytest
from django.db import models

from tp_backend_test.studies.models import Study
from tp_backend_test.studies.models import UploadTask

pytestmark = pytest.mark.django_db

EXPECTED_STUDY_FIELDS = {
    "id",
    "created_at",
    "updated_at",
    "nct_id",
    "brief_title",
    "official_title",
    "overall_status",
    "conditions",
    "study_type",
    "brief_summary",
    "sponsor_primary_key",
}

EXPECTED_UPLOAD_TASK_FIELDS = {
    "id",
    "created_at",
    "updated_at",
    "source_file",
    "file_hash",
    "status",
}


def test_study_nct_id_is_normalized_to_uppercase():
    study = Study.objects.create(nct_id="nct00000001", brief_title="Example")

    assert study.nct_id == "NCT00000001"


def test_study_only_scaffolds_product_fields():
    field_names = {field.name for field in Study._meta.fields}  # noqa: SLF001

    assert field_names == EXPECTED_STUDY_FIELDS


def test_upload_task_only_scaffolds_source_file_and_timestamps():
    field_names = {field.name for field in UploadTask._meta.fields}  # noqa: SLF001
    relationship_fields = {
        field.name
        for field in UploadTask._meta.get_fields()  # noqa: SLF001
        if isinstance(field, models.ManyToManyRel | models.ManyToManyField)
    }

    assert field_names == EXPECTED_UPLOAD_TASK_FIELDS
    assert relationship_fields == set()
