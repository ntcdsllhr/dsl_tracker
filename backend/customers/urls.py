from rest_framework.routers import DefaultRouter
from django.urls import path

from . import views

router = DefaultRouter()
router.register("customers", views.CustomerViewSet, basename="customer")
router.register("dsl-services", views.DSLServiceViewSet, basename="dslservice")
router.register("copper-pairs", views.CopperPairViewSet, basename="copperpair")
router.register("regions", views.RegionViewSet, basename="region")
router.register("cities", views.CityViewSet, basename="city")
router.register("exchanges", views.ExchangeViewSet, basename="exchange")
router.register("msags", views.MSAGViewSet, basename="msag")
router.register("activity", views.ActivityLogViewSet, basename="activitylog")
router.register("complaints", views.ComplaintViewSet, basename="complaint")

# Custom paths must come BEFORE router.urls: DRF's router registers
# activity/<pk>/ as a catch-all detail route, which would otherwise swallow
# a request to activity/stats/ (matching pk="stats") before it ever reaches
# the explicit view below.
urlpatterns = [
    path("dashboard/stats/", views.dashboard_stats, name="dashboard-stats"),
    path("activity/stats/", views.activity_stats, name="activity-stats"),
] + router.urls
