from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import ListAPIView

from accounts.authentication import AdminSessionAuthentication
from accounts.permissions import IsAdminRole

from .filters import AuditEventFilter
from .models import AuditEvent
from .pagination import AuditCursorPagination
from .serializers import AuditEventSerializer


class AuditEventListView(ListAPIView):
    authentication_classes = [AdminSessionAuthentication]
    permission_classes = [IsAdminRole]
    serializer_class = AuditEventSerializer
    pagination_class = AuditCursorPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = AuditEventFilter
    queryset = AuditEvent.objects.all()


class ProfileAuditTimelineView(AuditEventListView):
    def get_queryset(self):
        return AuditEvent.objects.filter(profile_id=self.kwargs["profile_id"])
