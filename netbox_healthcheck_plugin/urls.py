from django.conf.urls import include
from django.urls import path

from . import views

urlpatterns = (
    path('healthcheck/', views.HealthCheckListView.as_view(), name='healthcheck_list'),
)
