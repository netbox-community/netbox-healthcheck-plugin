from django.conf.urls import include
from django.urls import path

from netbox.views.generic import ObjectChangeLogView


urlpatterns = (
    path('healthcheck/', include('health_check.urls')),
)
