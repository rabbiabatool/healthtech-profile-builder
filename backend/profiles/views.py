from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.authentication import CookieJWTAuthentication
from accounts.permissions import IsStandardUser

from .models import HealthProfile, ProfileStatus
from .serializers import ProfileSerializer, ProfileUpdateSerializer


class MyProfileView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsStandardUser]

    def get_profile(self, request):
        return get_object_or_404(
            HealthProfile.objects.select_related("user"),
            user=request.user,
        )

    def get(self, request):
        profile = self.get_profile(request)
        return Response(ProfileSerializer(profile).data)

    def patch(self, request):
        profile = self.get_profile(request)
        if profile.status != ProfileStatus.ACTIVE:
            raise PermissionDenied("This profile has been deactivated.")

        serializer = ProfileUpdateSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ProfileSerializer(profile).data)