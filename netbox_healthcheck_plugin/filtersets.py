from netbox.filtersets import NetBoxModelFilterSet
from .models import HealthCheck


# class HealthCheckFilterSet(NetBoxModelFilterSet):
#
#     class Meta:
#         model = HealthCheck
#         fields = ['name', ]
#
#     def search(self, queryset, name, value):
#         return queryset.filter(description__icontains=value)
