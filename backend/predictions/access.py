from accounts.permissions import IsStandardUser

# Members only. Admin access to predictions is removed.
ADMIN_ROLE = "ADMIN"
MEMBER_ROLES = ("USER",)


class IsAdminOrMember(IsStandardUser):
    """Refactored access class: enforces standard member access only.

    Admins and anonymous callers are strictly refused.
    """

    message = "Standard user access only. Administrator access to predictions is not allowed."
