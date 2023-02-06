from django import forms

from ipam.models import Prefix
from netbox.forms import NetBoxModelForm, NetBoxModelFilterSetForm
from utilities.forms.fields import CommentField, DynamicModelChoiceField
from .models import HealthCheck


class HealthCheckForm(NetBoxModelForm):

    class Meta:
        model = HealthCheck
        fields = ('name', 'tags')
