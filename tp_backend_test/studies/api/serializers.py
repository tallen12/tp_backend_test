from rest_framework import serializers

from tp_backend_test.studies.models import NctSearchTask
from tp_backend_test.studies.models import Study
from tp_backend_test.studies.models import UploadTask


class StudySerializer(serializers.ModelSerializer):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = Study
        fields = "__all__"


class UploadTaskSerializer(serializers.ModelSerializer):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = UploadTask
        fields = [
            "id",
            "source_file",
            "file_hash",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "file_hash", "status", "created_at", "updated_at"]


class NctSearchTaskSerializer(serializers.ModelSerializer):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = NctSearchTask
        fields = "__all__"
        read_only_fields = ["id", "status", "created_at", "updated_at"]
