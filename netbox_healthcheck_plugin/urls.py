from django.urls import path

from netbox.views.generic import ObjectChangeLogView
from . import models, views


urlpatterns = (

    path('healthchecks/', views.HealthCheckListView.as_view(), name='healthcheck_list'),
    path('healthchecks/add/', views.HealthCheckEditView.as_view(), name='healthcheck_add'),
    path('healthchecks/<int:pk>/', views.HealthCheckView.as_view(), name='healthcheck'),
    path('healthchecks/<int:pk>/edit/', views.HealthCheckEditView.as_view(), name='healthcheck_edit'),
    path('healthchecks/<int:pk>/delete/', views.HealthCheckDeleteView.as_view(), name='healthcheck_delete'),
    path('healthchecks/<int:pk>/changelog/', ObjectChangeLogView.as_view(), name='healthcheck_changelog', kwargs={
        'model': models.HealthCheck
    }),

)
