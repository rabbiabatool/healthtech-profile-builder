from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.authentication import AdminSessionAuthentication
from accounts.permissions import IsAdminRole

from .models import HealthProfile, ProfileStatus
from .pagination import AdminPagination
from .queries import admin_profile_queryset
from .serializers import AdminProfileListSerializer, AdminProfileSerializer


class AdminProfileListView(ListAPIView):
    authentication_classes = [AdminSessionAuthentication]
    permission_classes = [IsAdminRole]
    serializer_class = AdminProfileListSerializer
    pagination_class = AdminPagination

    def get_queryset(self):
        status = self.request.query_params.get("status", "").strip().upper()
        if status and status not in ProfileStatus.values:
            raise ValidationError({"status": ["Use ACTIVE or INACTIVE."]})

        search = self.request.query_params.get("search", "").strip()[:100]
        return admin_profile_queryset(status=status or None, search=search)


class AdminProfileDetailView(RetrieveAPIView):
    authentication_classes = [AdminSessionAuthentication]
    permission_classes = [IsAdminRole]
    serializer_class = AdminProfileSerializer
    queryset = HealthProfile.objects.select_related("user")


class AdminProfileStatusView(APIView):
    authentication_classes = [AdminSessionAuthentication]
    permission_classes = [IsAdminRole]
    new_status = None

    def patch(self, request, pk):
        profile = get_object_or_404(HealthProfile.objects.select_related("user"), pk=pk)
        if profile.status != self.new_status:
            profile.status = self.new_status
            profile.save(update_fields=["status", "updated_at"])
        return Response(AdminProfileSerializer(profile).data)