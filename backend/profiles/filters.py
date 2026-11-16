import django_filters
from django.db.models import Q

from .models import CompletionStatus, HealthProfile, ProfileStatus

ORDERING_CHOICES = [
    ("created_at", "Oldest first"),
    ("-created_at", "Newest first"),
    ("completion_percent", "Least complete first"),
    ("-completion_percent", "Most complete first"),
]


class AdminProfileFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=ProfileStatus.choices)
    completion_status = django_filters.ChoiceFilter(choices=CompletionStatus.choices)
    created_after = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    created_before = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")
    search = django_filters.CharFilter(method="filter_search", max_length=100)
    ordering = django_filters.ChoiceFilter(choices=ORDERING_CHOICES, method="filter_ordering")

    class Meta:
        model = HealthProfile
        fields = []

    def filter_search(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset
        return queryset.filter(Q(user__full_name__icontains=value) | Q(user__email__icontains=value))

    def filter_ordering(self, queryset, name, value):
        tie_breaker = "-id" if value.startswith("-") else "id"
        return queryset.order_by(value, tie_breaker)
