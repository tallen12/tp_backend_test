from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser
from rest_framework.parsers import MultiPartParser

from tp_backend_test.studies.api.filters import NctSearchTaskFilter
from tp_backend_test.studies.api.filters import StudyFilter
from tp_backend_test.studies.api.filters import UploadTaskFilter
from tp_backend_test.studies.api.serializers import NctSearchTaskSerializer
from tp_backend_test.studies.api.serializers import StudySerializer
from tp_backend_test.studies.api.serializers import UploadTaskSerializer
from tp_backend_test.studies.models import NctSearchTask
from tp_backend_test.studies.models import Study
from tp_backend_test.studies.models import UploadTask
from tp_backend_test.studies.services.file_upload import FileUploadTaskService
from tp_backend_test.studies.services.file_upload import InvalidCsvError


class StudyViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = StudySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = StudyFilter
    pagination_class = PageNumberPagination

    def get_queryset(self):
        queryset = Study.objects.all()
        upload_task_id = self.request.query_params.get("upload_task_id")
        if upload_task_id:
            queryset = queryset.filter(
                nctsearchtask__upload_task_id=upload_task_id,
            ).distinct()
        return queryset


class UploadTaskViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = UploadTaskSerializer
    queryset = UploadTask.objects.all()
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend]
    filterset_class = UploadTaskFilter

    def perform_create(self, serializer):
        try:
            upload_task, created = FileUploadTaskService.factory().get_or_create(
                self.request.data["source_file"],
            )
        except InvalidCsvError as e:
            raise ValidationError({"source_file": str(e)}) from e

        if not created:
            msg = f"A task for this file already exists: {upload_task.pk}"
            raise ValidationError(
                {
                    "source_file": msg,
                },
            )

        serializer.instance = upload_task


class NctSearchTaskViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = NctSearchTaskSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = NctSearchTaskFilter
    pagination_class = PageNumberPagination

    def get_queryset(self):
        queryset = NctSearchTask.objects.select_related("upload_task", "study")
        upload_task_id = self.request.query_params.get("upload_task_id")
        if upload_task_id:
            queryset = queryset.filter(upload_task_id=upload_task_id)
        return queryset
