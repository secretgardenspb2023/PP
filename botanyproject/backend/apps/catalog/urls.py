from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import PlantViewSet, SearchView, SuggestView

app_name = "catalog"

router = DefaultRouter()
router.register("plants", PlantViewSet, basename="plant")

urlpatterns = [
    path("search/suggest/", SuggestView.as_view(), name="search-suggest"),
    path("search/", SearchView.as_view(), name="search"),
    *router.urls,
]
