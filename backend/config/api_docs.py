from functools import wraps

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers

from accounts import admin_views as account_admin_views
from accounts import views as account_views
from accounts.serializers import AdminUserSerializer, LoginSerializer, SignupSerializer, UserSerializer
from audit import views as audit_views
from profiles import admin_views as profile_admin_views
from profiles import views as profile_views
from profiles.serializers import (
    AdminProfileSerializer,
    DemographicsSerializer,
    EmergencyContactSerializer,
    MyProfileSerializer,
    WellnessSerializer,
)

MEMBER_AUTH = "Authentication (members)"
MEMBER_PROFILE = "Member profile"
ADMIN_SESSION = "Admin session"
ADMIN_PROFILES = "Admin profiles"
AUDIT = "Audit log"

CSRF_HEADER = OpenApiParameter(
    name="X-CSRFToken",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.HEADER,
    required=True,
    description="CSRF token from GET /api/auth/csrf (or /api/admin/csrf).",
)

BAD_REQUEST = OpenApiResponse(description="Validation failed. The body maps field names to lists of messages.")
UNAUTHENTICATED = OpenApiResponse(description="Not signed in, or the session or token has expired.")
FORBIDDEN = OpenApiResponse(description="Not allowed: wrong role, deactivated profile or missing CSRF token.")
NOT_FOUND = OpenApiResponse(description="Does not exist, or does not belong to you.")

READ_ERRORS = {401: UNAUTHENTICATED, 403: FORBIDDEN}
WRITE_ERRORS = {400: BAD_REQUEST, 401: UNAUTHENTICATED, 403: FORBIDDEN}

Detail = inline_serializer("Detail", {"detail": serializers.CharField()})


def document(view_class, method, **schema):
    if not hasattr(view_class, method):
        return
    original = getattr(view_class, method)

    @wraps(original)
    def documented(self, *args, **kwargs):
        return original(self, *args, **kwargs)

    documented.kwargs = {}
    setattr(view_class, method, extend_schema(**schema)(documented))


# ---------- Members: sign up, sign in, tokens ----------

document(
    account_views.CsrfView,
    "get",
    summary="Get a CSRF token",
    description="Returns a token and sets the csrftoken cookie. Send the token in the X-CSRFToken header on state-changing requests.",
    tags=[MEMBER_AUTH],
    responses={200: inline_serializer("CsrfToken", {"csrfToken": serializers.CharField()})},
)
document(
    account_views.SignupView,
    "post",
    summary="Register a member",
    description="Creates the account and an empty profile. Members cannot register as administrators.",
    tags=[MEMBER_AUTH],
    request=SignupSerializer,
    responses={201: UserSerializer, 400: BAD_REQUEST},
)
document(
    account_views.UserLoginView,
    "post",
    summary="Member login",
    description="Requires a valid CSRF token and matching origin. On success sets the access_token and refresh_token HttpOnly cookies. No token is returned in the body.",
    tags=[MEMBER_AUTH],
    request=LoginSerializer,
    parameters=[CSRF_HEADER],
    responses={
        200: inline_serializer("MemberLogin", {"user": UserSerializer()}),
        400: BAD_REQUEST,
        401: OpenApiResponse(description="Invalid email or password."),
        403: FORBIDDEN,
    },
)
document(
    account_views.RefreshView,
    "post",
    summary="Refresh the member session",
    description="Rotates the refresh token (the old one is revoked) and issues new cookies.",
    tags=[MEMBER_AUTH],
    request=None,
    parameters=[CSRF_HEADER],
    responses={200: Detail, 401: UNAUTHENTICATED, 403: FORBIDDEN},
)
document(
    account_views.UserLogoutView,
    "post",
    summary="Member logout",
    description="Revokes the refresh token and clears both cookies.",
    tags=[MEMBER_AUTH],
    request=None,
    parameters=[CSRF_HEADER],
    responses={204: None, 403: FORBIDDEN},
)

# ---------- Members: profile sections ----------

document(
    profile_views.MyProfileView,
    "get",
    summary="Get my whole profile",
    description="Status, completion (percent, status and missing items) and all three sections.",
    tags=[MEMBER_PROFILE],
    responses={200: MyProfileSerializer, **READ_ERRORS},
)
document(
    profile_views.MyProfileView,
    "post",
    summary="Create my health profile",
    description="Creates a new root health profile for the authenticated member with initialised empty sections. Returns 409 if a profile already exists.",
    tags=[MEMBER_PROFILE],
    request=None,
    parameters=[CSRF_HEADER],
    responses={
        201: MyProfileSerializer,
        401: UNAUTHENTICATED,
        403: FORBIDDEN,
        409: OpenApiResponse(description="A profile already exists for this account."),
    },
)
document(
    profile_views.MyProfileView,
    "delete",
    summary="Delete my health profile",
    description="Deletes the authenticated member's root profile and related sections while preserving the account and audit history.",
    tags=[MEMBER_PROFILE],
    parameters=[CSRF_HEADER],
    responses={
        204: None,
        401: UNAUTHENTICATED,
        403: FORBIDDEN,
        404: NOT_FOUND,
    },
)

for view, serializer, label in (
    (profile_views.DemographicsView, DemographicsSerializer, "demographics"),
    (profile_views.WellnessView, WellnessSerializer, "wellness preferences"),
):
    document(
        view,
        "get",
        summary=f"Get my {label}",
        tags=[MEMBER_PROFILE],
        responses={200: serializer, **READ_ERRORS},
    )
    document(
        view,
        "patch",
        summary=f"Update my {label}",
        description="Send only the fields to change. Completion is recalculated and the edit is audited (field names only).",
        tags=[MEMBER_PROFILE],
        request=serializer,
        parameters=[CSRF_HEADER],
        responses={200: serializer, **WRITE_ERRORS},
    )
    document(
        view,
        "delete",
        summary=f"Reset my {label}",
        description="Clears every field in this section and returns the empty section.",
        tags=[MEMBER_PROFILE],
        parameters=[CSRF_HEADER],
        responses={200: serializer, **READ_ERRORS},
    )

document(
    profile_views.ContactListView,
    "get",
    summary="List my emergency contacts",
    description="At most three, primary first.",
    tags=[MEMBER_PROFILE],
    responses={200: EmergencyContactSerializer(many=True), **READ_ERRORS},
)
document(
    profile_views.ContactListView,
    "post",
    summary="Add an emergency contact",
    description="The first contact becomes primary automatically. A profile can hold at most three contacts.",
    tags=[MEMBER_PROFILE],
    request=EmergencyContactSerializer,
    parameters=[CSRF_HEADER],
    responses={201: EmergencyContactSerializer, **WRITE_ERRORS},
)
document(
    profile_views.ContactDetailView,
    "get",
    summary="Get one of my emergency contacts",
    tags=[MEMBER_PROFILE],
    responses={200: EmergencyContactSerializer, 404: NOT_FOUND, **READ_ERRORS},
)
document(
    profile_views.ContactDetailView,
    "patch",
    summary="Edit an emergency contact",
    description="Setting is_primary to true demotes the current primary. The primary flag cannot be switched off directly.",
    tags=[MEMBER_PROFILE],
    request=EmergencyContactSerializer,
    parameters=[CSRF_HEADER],
    responses={200: EmergencyContactSerializer, 404: NOT_FOUND, **WRITE_ERRORS},
)
document(
    profile_views.ContactDetailView,
    "delete",
    summary="Delete an emergency contact",
    description="Deleting the primary promotes the oldest remaining contact.",
    tags=[MEMBER_PROFILE],
    parameters=[CSRF_HEADER],
    responses={204: None, 404: NOT_FOUND, **READ_ERRORS},
)

# ---------- Administrators ----------

document(
    account_admin_views.AdminLoginView,
    "post",
    summary="Admin login",
    description="Admins are created from the command line and cannot self-register. Sets the admin_session cookie.",
    tags=[ADMIN_SESSION],
    request=LoginSerializer,
    parameters=[CSRF_HEADER],
    responses={
        200: inline_serializer(
            "AdminLogin", {"user": AdminUserSerializer(), "csrfToken": serializers.CharField()}
        ),
        400: BAD_REQUEST,
        401: OpenApiResponse(description="Invalid email or password (or not an admin account)."),
        403: FORBIDDEN,
    },
)
document(
    account_admin_views.AdminLogoutView,
    "post",
    summary="Admin logout",
    description="Destroys the server-side session.",
    tags=[ADMIN_SESSION],
    request=None,
    parameters=[CSRF_HEADER],
    responses={204: None, **READ_ERRORS},
)
document(
    account_admin_views.AdminMeView,
    "get",
    summary="Who am I (admin)",
    tags=[ADMIN_SESSION],
    responses={200: AdminUserSerializer, **READ_ERRORS},
)
document(
    profile_admin_views.AdminProfileListView,
    "get",
    summary="List and search member profiles",
    description="Filters: status, completion_status, created_after, created_before, search. Ordering: four fixed choices. A search or filter is audited (names only, never the search words).",
    tags=[ADMIN_PROFILES],
)
document(
    profile_admin_views.AdminProfileDetailView,
    "get",
    summary="View one profile with all sections",
    description="Read-only. Every view is recorded in the audit log.",
    tags=[ADMIN_PROFILES],
)
document(
    profile_admin_views.DeactivateProfileView,
    "patch",
    summary="Deactivate a profile",
    description="The member can still read the profile but can no longer edit it. Recorded in the audit log.",
    tags=[ADMIN_PROFILES],
    request=None,
    parameters=[CSRF_HEADER],
    responses={200: AdminProfileSerializer, 404: NOT_FOUND, **READ_ERRORS},
)
document(
    profile_admin_views.ReactivateProfileView,
    "patch",
    summary="Reactivate a profile",
    tags=[ADMIN_PROFILES],
    request=None,
    parameters=[CSRF_HEADER],
    responses={200: AdminProfileSerializer, 404: NOT_FOUND, **READ_ERRORS},
)

# ---------- Audit log (read-only) ----------

document(
    audit_views.ProfileAuditTimelineView,
    "get",
    summary="One profile's audit timeline",
    description="Newest first, cursor pagination. Field names only: values are never stored.",
    tags=[AUDIT],
)
document(
    audit_views.AuditEventListView,
    "get",
    summary="List audit events",
    description="Newest first, cursor pagination. Filters: action, outcome, actor_id, profile_id, created_after, created_before. There is no way to create, change or delete events through the API.",
    tags=[AUDIT],
)