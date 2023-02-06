from django.urls import path

from netbox.views.generic import ObjectChangeLogView
from . import models, views


urlpatterns = (
    path('healthcheck/', include('health_check.urls')),
)
