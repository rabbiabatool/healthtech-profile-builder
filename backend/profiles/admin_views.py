from django.db import transaction
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.authentication import AdminSessionAuthentication
from accounts.permissions import IsAdminRole
from audit.models import AuditAction
from audit.services import FILTER_NAMES, record_event

from .filters import AdminProfileFilter
from .models import HealthProfile, ProfileStatus
from .pagination import AdminPagination
from .queries import admin_profile_queryset
from .serializers import AdminProfileListSerializer, AdminProfileSerializer


def admin_detail_queryset():
    return HealthProfile.objects.select_related("user", "demographics", "wellness").prefetch_related(
        "emergency_contacts"
    )


class AdminProfileListView(ListAPIView):
    authentication_classes = [AdminSessionAuthentication]
    permission_classes = [IsAdminRole]
    serializer_class = AdminProfileListSerializer
    pagination_class = AdminPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = AdminProfileFilter

    def get_queryset(self):
        return admin_profile_queryset()

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        used = [name for name in FILTER_NAMES if request.query_params.get(name)]
        if used and request.query_params.get("page", "1") == "1":
            record_event(
                request.user,
                AuditAction.ADMIN_SEARCH_PERFORMED,
                metadata={"filters_used": used, "result_count": response.data["count"]},
            )
        return response


class AdminProfileDetailView(RetrieveAPIView):
    authentication_classes = [AdminSessionAuthentication]
    permission_classes = [IsAdminRole]
    serializer_class = AdminProfileSerializer
    queryset = admin_detail_queryset()

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        record_event(request.user, AuditAction.ADMIN_PROFILE_VIEWED, profile_id=self.kwargs["pk"])
        return response


class AdminProfileStatusView(APIView):
    authentication_classes = [AdminSessionAuthentication]
    permission_classes = [IsAdminRole]
    new_status = None
    audit_action = None

    def patch(self, request, pk):
        with transaction.atomic():
            profile = get_object_or_404(HealthProfile.objects.select_for_update(), pk=pk)
            previous = profile.status
            if previous != self.new_status:
                profile.status = self.new_status
                profile.save(update_fields=["status", "updated_at"])
                record_event(
                    request.user,
                    self.audit_action,
                    profile_id=profile.pk,
                    metadata={"from_status": previous, "to_status": self.new_status},
                )

        profile = get_object_or_404(admin_detail_queryset(), pk=pk)
        return Response(AdminProfileSerializer(profile).data)

class DeactivateProfileView(AdminProfileStatusView):
    new_status = ProfileStatus.INACTIVE
    audit_action = AuditAction.ADMIN_PROFILE_DEACTIVATED


class ReactivateProfileView(AdminProfileStatusView):
    new_status = ProfileStatus.ACTIVE
    audit_action = AuditAction.ADMIN_PROFILE_REACTIVATED