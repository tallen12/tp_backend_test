from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone


class TimestampedModel(models.Model):
    # Use uuid instead of auto incrementing integer
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Study(TimestampedModel):
    nct_id = models.CharField(max_length=11, unique=True, db_index=True)
    brief_title = models.TextField(blank=True)
    official_title = models.TextField(blank=True)
    overall_status = models.CharField(max_length=64, blank=True)
    conditions = models.JSONField(default=list, blank=True)
    study_type = models.CharField(max_length=64, blank=True)
    brief_summary = models.TextField(blank=True)
    sponsor_primary_key = models.CharField(max_length=255, blank=True)

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        ordering = ["nct_id"]

    def __str__(self) -> str:
        return self.nct_id

    def save(self, *args, **kwargs):
        self.nct_id = self.nct_id.upper()
        super().save(*args, **kwargs)


class UploadTask(TimestampedModel):
    class Status(models.TextChoices):
        NEW = "new"
        PROCESSING = "processing"
        DONE = "done"

    source_file = models.FileField(upload_to="study_uploads/")
    file_hash = models.CharField(
        unique=True,
        editable=False,
        max_length=64,
        db_index=True,  # Put a btree index since we are querying it on insert to dedupe
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.source_file.name or f"Upload task {self.pk}"


class NctSearchTask(TimestampedModel):
    class Status(models.TextChoices):
        NEW = "new"
        PROCESSING = "processing"
        NOT_FOUND = "not found"
        FAILURE = "failure"
        DONE = "done"

    nct_id = models.CharField(
        max_length=11,
        db_index=True,
    )  # Does not need to be unique since this is per upload
    upload_task = models.ForeignKey(UploadTask, on_delete=models.CASCADE)
    study = models.ForeignKey(
        Study,
        on_delete=models.SET_NULL,
        null=True,
        default=None,
    )  # These should not be deleted

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Upload task {self.pk} for {self.nct_id}"
