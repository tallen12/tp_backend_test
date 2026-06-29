from django.contrib import admin
from django.contrib import messages

from tp_backend_test.studies.models import Study
from tp_backend_test.studies.models import UploadTask
from tp_backend_test.studies.services.file_upload import FileUploadTaskService
from tp_backend_test.studies.services.file_upload import InvalidCsvError


@admin.register(Study)
class StudyAdmin(admin.ModelAdmin):
    list_display = [
        "nct_id",
        "brief_title",
        "overall_status",
        "study_type",
        "updated_at",
    ]
    search_fields = ["nct_id", "brief_title", "official_title", "overall_status"]
    list_filter = ["overall_status", "study_type"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["nct_id"]


@admin.register(UploadTask)
class UploadTaskAdmin(admin.ModelAdmin):
    list_display = [
        "source_file",
        "created_at",
        "updated_at",
        "file_hash",
        "status",
    ]
    readonly_fields = ["created_at", "updated_at", "file_hash", "status"]
    exclude = ["status", "file_hash"]

    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)
        self.file_upload_service = FileUploadTaskService.factory()

    def save_model(self, request, obj, form, change):
        try:
            upload_task, created = self.file_upload_service.get_or_create(
                form.cleaned_data["source_file"],
            )
        except InvalidCsvError as e:
            self.message_user(request, str(e), level=messages.ERROR)
            return

        if not created:
            self.message_user(
                request,
                f"A task for this file already exists: {upload_task.pk}",
                level=messages.WARNING,
            )
            request.duplicate_upload = True  # type: ignore This is a django workaround
        else:
            # Copy pk so Django's response_add can build the redirect URL
            obj.pk = upload_task.pk

    def message_user(
        self,
        request,
        message,
        level=messages.INFO,
        extra_tags="",
        fail_silently=False,  # noqa: FBT002 This is django function override
    ):
        if getattr(request, "duplicate_upload", False) and level == messages.SUCCESS:
            return
        super().message_user(
            request,
            message,
            level=level,
            extra_tags=extra_tags,
            fail_silently=fail_silently,
        )
