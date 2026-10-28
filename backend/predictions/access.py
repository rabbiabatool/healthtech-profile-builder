"""Who may use the ML endpoints: signed-in members (role USER) and admins (role ADMIN).

This reuses the two permission classes the project already has, so role rules
stay defined in one place (accounts/permissions.py).
"""
from accounts.models import Role
from accounts.permissions import IsAdminRole, IsStandardUser

ADMIN_ROLE = Role.ADMIN
MEMBER_ROLES = (Role.USER,)

IsAdminOrMember = IsAdminRole | IsStandardUser