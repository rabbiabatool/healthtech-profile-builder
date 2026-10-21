from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.authentication import CookieJWTAuthentication
from accounts.permissions import IsStandardUser

from . import services
from .models import Demographics, EmergencyContact, HealthProfile, WellnessPreferences
from .permissions import ProfileIsEditable
from .serializers import (
    DemographicsSerializer,
    EmergencyContactSerializer,
    MyProfileSerializer,
    WellnessSerializer,
)


class MemberBaseView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsStandardUser, ProfileIsEditable]

    def get_profile(self):
        return get_object_or_404(HealthProfile, user=self.request.user)


class MyProfileView(MemberBaseView):
    def get(self, request):
        profile = get_object_or_404(
            HealthProfile.objects.select_related("user", "demographics", "wellness").prefetch_related(
                "emergency_contacts"
            ),
            user=request.user,
        )
        return Response(MyProfileSerializer(profile).data)


class SectionView(MemberBaseView):
    model = None
    serializer_class = None

    def update_section(self, profile, values, actor):
        raise NotImplementedError

    def reset_section(self, profile, actor):
        raise NotImplementedError

    def get(self, request):
        section = get_object_or_404(self.model, profile=self.get_profile())
        return Response(self.serializer_class(section).data)

    def patch(self, request):
        profile = self.get_profile()
        section = get_object_or_404(self.model, profile=profile)
        serializer = self.serializer_class(section, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = self.update_section(profile, serializer.validated_data, actor=request.user)
        return Response(self.serializer_class(updated).data)

    def delete(self, request):
        updated = self.reset_section(self.get_profile(), actor=request.user)
        return Response(self.serializer_class(updated).data)


class DemographicsView(SectionView):
    model = Demographics
    serializer_class = DemographicsSerializer

    def update_section(self, profile, values, actor):
        return services.update_demographics(profile, values, actor=actor)

    def reset_section(self, profile, actor):
        return services.reset_demographics(profile, actor=actor)


class WellnessView(SectionView):
    model = WellnessPreferences
    serializer_class = WellnessSerializer

    def update_section(self, profile, values, actor):
        return services.update_wellness(profile, values, actor=actor)

    def reset_section(self, profile, actor):
        return services.reset_wellness(profile, actor=actor)


class ContactListView(MemberBaseView):
    def get(self, request):
        profile = self.get_profile()
        return Response(EmergencyContactSerializer(profile.emergency_contacts.all(), many=True).data)

    def post(self, request):
        profile = self.get_profile()
        serializer = EmergencyContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contact = services.create_contact(profile, serializer.validated_data, actor=request.user)
        return Response(EmergencyContactSerializer(contact).data, status=status.HTTP_201_CREATED)


class ContactDetailView(MemberBaseView):
    def get_contact(self, pk):
        return get_object_or_404(EmergencyContact, pk=pk, profile=self.get_profile())

    def get(self, request, pk):
        return Response(EmergencyContactSerializer(self.get_contact(pk)).data)

    def patch(self, request, pk):
        profile = self.get_profile()
        contact = get_object_or_404(EmergencyContact, pk=pk, profile=profile)
        serializer = EmergencyContactSerializer(contact, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = services.update_contact(profile, pk, serializer.validated_data, actor=request.user)
        return Response(EmergencyContactSerializer(updated).data)

    def delete(self, request, pk):
        services.delete_contact(self.get_profile(), pk, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)