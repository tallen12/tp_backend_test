import django_filters

from tp_backend_test.studies.models import NctSearchTask
from tp_backend_test.studies.models import Study
from tp_backend_test.studies.models import UploadTask


class StudyFilter(django_filters.FilterSet):
    nct_id = django_filters.CharFilter(lookup_expr="icontains")
    brief_title = django_filters.CharFilter(lookup_expr="icontains")
    official_title = django_filters.CharFilter(lookup_expr="icontains")
    overall_status = django_filters.CharFilter(lookup_expr="iexact")
    study_type = django_filters.CharFilter(lookup_expr="iexact")
    upload_task_id = django_filters.UUIDFilter(
        field_name="nctsearchtask__upload_task_id",
        distinct=True,
    )
    ordering = django_filters.OrderingFilter(
        fields=(
            ("nct_id", "nct_id"),
            ("created_at", "created_at"),
            ("updated_at", "updated_at"),
        ),
    )

    class Meta:
        model = Study
        fields = [
            "nct_id",
            "brief_title",
            "official_title",
            "overall_status",
            "study_type",
        ]


class UploadTaskFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(lookup_expr="iexact")
    created_at_after = django_filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="gte",
    )
    created_at_before = django_filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="lte",
    )
    ordering = django_filters.OrderingFilter(
        fields=(
            ("created_at", "created_at"),
            ("updated_at", "updated_at"),
            ("status", "status"),
        ),
    )

    class Meta:
        model = UploadTask
        fields = ["status"]


class NctSearchTaskFilter(django_filters.FilterSet):
    nct_id = django_filters.CharFilter(lookup_expr="icontains")
    status = django_filters.ChoiceFilter(lookup_expr="iexact")
    upload_task_id = django_filters.UUIDFilter(field_name="upload_task_id")
    ordering = django_filters.OrderingFilter(
        fields=(
            ("nct_id", "nct_id"),
            ("status", "status"),
            ("created_at", "created_at"),
        ),
    )

    class Meta:
        model = NctSearchTask
        fields = ["nct_id", "status", "upload_task_id"]
