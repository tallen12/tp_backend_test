from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from tp_backend_test.studies.api.views import NctSearchTaskViewSet
from tp_backend_test.studies.api.views import StudyViewSet
from tp_backend_test.studies.api.views import UploadTaskViewSet
from tp_backend_test.users.api.views import UserViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("users", UserViewSet)
router.register("studies", StudyViewSet, basename="study")
router.register("upload-tasks", UploadTaskViewSet, basename="upload-task")
router.register("nct-search-tasks", NctSearchTaskViewSet, basename="nct-search-task")

app_name = "api"
urlpatterns = router.urls
