import django_filters
from django import forms

from .models import AuditAction, AuditEvent, Outcome


class IntegerFilter(django_filters.Filter):
    field_class = forms.IntegerField


class AuditEventFilter(django_filters.FilterSet):
    action = django_filters.ChoiceFilter(choices=AuditAction.choices)
    outcome = django_filters.ChoiceFilter(choices=Outcome.choices)
    actor_id = IntegerFilter(field_name="actor_id", min_value=1)
    profile_id = IntegerFilter(field_name="profile_id", min_value=1)
    created_after = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    created_before = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model = AuditEvent
        fields = []