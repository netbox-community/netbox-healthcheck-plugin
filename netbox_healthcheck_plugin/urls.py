from django.urls import path

from netbox.views.generic import ObjectChangeLogView
from . import models, views


urlpatterns = (

    path('healthchecks/', views.HealthCheckListView.as_view(), name='healthcheck_list'),
    path('healthcheck/', include('health_check.urls'), name='healthcheck_view'),
)
