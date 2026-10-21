from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import ProfileStatus


class ProfileIsEditable(BasePermission):
    message = "This profile has been deactivated."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        profile = getattr(request.user, "profile", None)
        return profile is not None and profile.status == ProfileStatus.ACTIVE