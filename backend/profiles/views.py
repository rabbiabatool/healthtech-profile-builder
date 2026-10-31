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


class MyProfileView(APIView):
    """
    GET  /api/profiles/me  – read the authenticated member's own profile.
                             Returns 404 if no profile exists yet.

    POST /api/profiles/me  – create the profile for the authenticated member.
                             Returns 201 on success.
                             Returns 409 if a profile already exists.

    DELETE /api/profiles/me – delete the authenticated member's own profile.
                              Retains the user account.
                              Historical audit records are preserved.
                              The same account may POST a new profile afterwards.
                              Returns 204 on success.
                              Returns 404 if no profile exists.

    PATCH /api/profiles/me – NOT ALLOWED (405).
                             Use the section-level endpoints to edit profile data.
    """

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsStandardUser]
    # NOTE: ProfileIsEditable is deliberately NOT listed here at the class
    # level.  GET and POST work regardless of status (no profile exists for
    # POST; a deactivated profile should still be readable on GET).  DELETE
    # has its own business rule (any active member may delete their profile).
    # Section-level writes continue to use ProfileIsEditable via MemberBaseView.
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get(self, request):
        """Read the authenticated member's profile. 404 if none exists."""
        profile = get_object_or_404(
            HealthProfile.objects.select_related("user", "demographics", "wellness").prefetch_related(
                "emergency_contacts"
            ),
            user=request.user,
        )
        return Response(MyProfileSerializer(profile).data)

    def post(self, request):
        """
        Create the profile for the authenticated member.

        - Owner is always the authenticated user; any owner field in the
          request body is ignored.
        - Returns 201 with the full profile representation on success.
        - Returns 409 if the member already has a profile.
        """
        try:
            profile = services.create_profile(request.user, actor=request.user)
        except Exception as exc:
            # Catch the ValidationError raised by create_profile for duplicates.
            from rest_framework.exceptions import ValidationError
            if isinstance(exc, ValidationError) and getattr(exc, "detail", {}).get("detail") == "A profile already exists for this account.":
                return Response(
                    {"detail": "A profile already exists for this account."},
                    status=status.HTTP_409_CONFLICT,
                )
            raise

        # Reload with related sections so the serializer has full data.
        profile = HealthProfile.objects.select_related("user", "demographics", "wellness").prefetch_related(
            "emergency_contacts"
        ).get(pk=profile.pk)
        return Response(MyProfileSerializer(profile).data, status=status.HTTP_201_CREATED)

    def delete(self, request):
        """
        Delete the authenticated member's own profile.

        - The user account is NOT deleted.
        - Historical audit records survive because AuditEvent.profile_id is a
          plain BigIntegerField (no FK cascade).
        - Returns 204 on success.
        - Returns 404 if no profile exists.
        """
        profile = get_object_or_404(HealthProfile, user=request.user)
        services.delete_profile(profile, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


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
