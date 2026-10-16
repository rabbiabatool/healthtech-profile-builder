from rest_framework.permissions import BasePermission

from .models import Role


class IsStandardUser(BasePermission):
    message = "Standard user access only."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.role == Role.USER
        )