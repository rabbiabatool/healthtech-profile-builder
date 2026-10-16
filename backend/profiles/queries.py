from django.db.models import Q

from .models import HealthProfile


def admin_profile_queryset(status=None, search=""):
    queryset = HealthProfile.objects.select_related("user")
    if status:
        queryset = queryset.filter(status=status)
    if search:
        queryset = queryset.filter(
            Q(user__full_name__icontains=search) | Q(user__email__icontains=search)
        )
    return queryset.order_by("-created_at", "-id")