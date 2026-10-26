from rest_framework.permissions import BasePermission

# Change these two values if your user model stores different role names.
ADMIN_ROLE = "ADMIN"
MEMBER_ROLES = ("USER",)


class IsAdminOrMember(BasePermission):
    """Signed-in admins and members only. Anonymous callers and unknown roles are refused."""

    message = "You must be signed in as an admin or a member to use this feature."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return getattr(user, "role", None) in {ADMIN_ROLE, *MEMBER_ROLES}